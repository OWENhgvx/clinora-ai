"""
main.py — Clinora FastAPI backend v4.0
JWT auth + patient record management
Run: uvicorn main:app --reload --port 8000
"""
import os, json, uuid
import re
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import HTTPException, Depends, UploadFile, File, Query
from typing import List
from fastapi.responses import Response
from fastapi.security import OAuth2PasswordRequestForm

load_dotenv()

from sse_starlette.sse import EventSourceResponse

from agents import (
    call_interviewer, call_diagnostician, call_critic,
    call_diagnostician_cot, call_critic_cot,
    rewrite_image_findings_for_rag,
    call_agent_commentary, call_diagnostic_roundtable,
)
from agents_async import (
    call_interviewer_async,
    call_diagnostician_cot_async, call_diagnostician_async,
    call_critic_cot_async, call_critic_async,
    call_agent_commentary_async, call_diagnostic_roundtable_async,
)
from safety import classify_safety
from rag    import get_collection_size, add_documents
from ingest import fetch_pmids, fetch_article_details, DEFAULT_TERMS
from export import generate_pdf
from eval   import run_single_llm, run_multi_agent, run_mistral_judge, run_mistral_diagnosis_review, SAMPLE_QUESTIONS
from core.app_factory import create_app, validation_exception_handler
from db import get_db, severity_to_level, severity_to_score
from services.diagnosis_service import build_diagnosis_context, build_rag_query, extract_key_findings_excerpt
import services.media_service as _media_service
import services.session_service as _services
from schemas.api import (
    ChatMessage,
    DiagnoseRequest,
    EvalRequest,
    IngestRequest,
    MessageInput,
    PatientInput,
    RegisterInput,
    SymptomInput,
    VerdictInput,
    _check_injection,
)
from auth   import (
    user_create, user_get_by_username, verify_password,
    create_token, get_current_user, require_user,
    patient_create, patient_get, patient_update, patient_delete, patients_list
)


def _bind_services_db():
    # Keep legacy tests/consumers that monkeypatch main.get_db working while
    # the implementation lives in services.py.
    _services.get_db = get_db


def _now():
    return _services._now()


def _extract_latest_safety_payload(session_id: str):
    _bind_services_db()
    return _services._extract_latest_safety_payload(session_id)


def _maybe_reuse_recent_session(symptoms, user_id, severity_level):
    _bind_services_db()
    return _services._maybe_reuse_recent_session(symptoms, user_id, severity_level)


def session_get(sid):
    _bind_services_db()
    _services.session_messages_legacy = session_messages_legacy
    return _services.session_get(sid)


def session_message_create(session_id, role, content, agent_type=None, user_id=None):
    _bind_services_db()
    return _services.session_message_create(session_id, role, content, agent_type, user_id)


def session_messages_raw(session_id):
    _bind_services_db()
    return _services.session_messages_raw(session_id)


def session_messages_legacy(session_id):
    raw = session_messages_raw(session_id)
    out = []
    for m in raw:
        if m["role"] == "user":
            out.append({"role": "user", "text": m["content"]})
        elif m["role"] == "agent":
            out.append({"role": "ai", "agent": m.get("agent_type"), "text": m["content"]})
        else:
            out.append({"role": "system", "text": m["content"]})
    return out


def normalize_history_for_interviewer(history):
    return _services.normalize_history_for_interviewer(history)


def session_uploads_list(session_id):
    _bind_services_db()
    return _services.session_uploads_list(session_id)


def session_update(sid, **kwargs):
    _bind_services_db()
    return _services.session_update(sid, **kwargs)


def sessions_list(*args, **kwargs):
    _bind_services_db()
    return _services.sessions_list(*args, **kwargs)


def provider_sessions_list(*args, **kwargs):
    _bind_services_db()
    return _services.provider_sessions_list(*args, **kwargs)


def _is_provider(user):
    return _services._is_provider(user)


UPLOAD_ROOT = _media_service.UPLOAD_ROOT
ALLOWED_UPLOAD_TYPES = _media_service.ALLOWED_UPLOAD_TYPES
IMAGE_MEDIA_TYPES = _media_service.IMAGE_MEDIA_TYPES
MAX_UPLOAD_CONTEXT_CHARS = _media_service.MAX_UPLOAD_CONTEXT_CHARS
_MAX_IMAGE_BYTES = _media_service._MAX_IMAGE_BYTES
_ORIGINAL_COMPRESS_IMAGE_BYTES = _media_service._compress_image_bytes
_ORIGINAL_ANALYZE_MEDICAL_IMAGE_BYTES = _media_service._analyze_medical_image_bytes


def _bind_media_helpers():
    # Keep monkeypatches against main.* effective after moving implementation.
    compress = globals()["_compress_image_bytes"]
    analyze_bytes = globals()["_analyze_medical_image_bytes"]
    _media_service._MAX_IMAGE_BYTES = globals()["_MAX_IMAGE_BYTES"]
    _media_service.IMAGE_MEDIA_TYPES = globals()["IMAGE_MEDIA_TYPES"]
    _media_service._compress_image_bytes = (
        _ORIGINAL_COMPRESS_IMAGE_BYTES
        if compress is _MEDIA_COMPRESS_WRAPPER
        else compress
    )
    _media_service._analyze_medical_image_bytes = (
        _ORIGINAL_ANALYZE_MEDICAL_IMAGE_BYTES
        if analyze_bytes is _MEDIA_ANALYZE_BYTES_WRAPPER
        else analyze_bytes
    )


def _safe_filename(name: str) -> str:
    return _media_service._safe_filename(name)


def _extract_text_from_txt(path: Path) -> str:
    return _media_service._extract_text_from_txt(path)


def _extract_text_from_pdf(path: Path) -> str:
    return _media_service._extract_text_from_pdf(path)


def _compress_image_bytes(raw: bytes, orig_ext: str) -> tuple[bytes, str]:
    return _ORIGINAL_COMPRESS_IMAGE_BYTES(raw, orig_ext)


def _analyze_medical_image_bytes(raw: bytes, media_type: str) -> dict:
    return _ORIGINAL_ANALYZE_MEDICAL_IMAGE_BYTES(raw, media_type)


_MEDIA_COMPRESS_WRAPPER = _compress_image_bytes
_MEDIA_ANALYZE_BYTES_WRAPPER = _analyze_medical_image_bytes


def _analyze_medical_image(path: Path) -> dict:
    _bind_media_helpers()
    return _media_service._analyze_medical_image(path)


def _analyze_dicom(path: Path) -> dict:
    _bind_media_helpers()
    return _media_service._analyze_dicom(path)


def _transcribe_audio(path: Path, language: str = "en-US") -> str:
    return _media_service._transcribe_audio(path, language)


def _analyze_video(path: Path) -> str:
    return _media_service._analyze_video(path)

app = create_app()

# ── Health ────────────────────────────────────────────────
@app.get("/")
def root():
    return {"service":"Clinora API","version":"4.0.0","rag_db_size":get_collection_size(),"status":"ok"}

@app.get("/api/rag/status")
def rag_status():
    size = get_collection_size()
    return {"document_count":size,"status":"ready" if size>0 else "empty"}

@app.post("/api/rag/ingest")
async def rag_ingest(body: IngestRequest, user=Depends(require_user)):
    """
    Fetch fresh PubMed articles and write them into the RAG vector store.
    Provider role only.
    """
    if user.get("role") != "provider":
        raise HTTPException(403, "Only providers can trigger ingestion")
    import time as _time

    terms = body.terms if body.terms else DEFAULT_TERMS
    per_term = min(body.per_term, 50)  # cap per-term to avoid runaway fetches

    initial_size = get_collection_size()
    total_added = 0
    details = []

    for term in terms:
        pmids = fetch_pmids(term, per_term)
        if not pmids:
            details.append({"term": term, "found": 0, "added": 0})
            continue

        articles = fetch_article_details(pmids)
        if not articles:
            details.append({"term": term, "found": len(pmids), "added": 0})
            continue

        added = add_documents(articles)
        total_added += added
        details.append({
            "term": term,
            "found": len(pmids),
            "fetched": len(articles),
            "added": added,
            "skipped_duplicates": len(articles) - added,
        })
        _time.sleep(0.4)  # NCBI rate limit

    final_size = get_collection_size()
    return {
        "total_added": total_added,
        "initial_db_size": initial_size,
        "final_db_size": final_size,
        "terms_processed": len(terms),
        "details": details,
    }

# ── Auth Routes ───────────────────────────────────────────
@app.post("/api/auth/register")
def register(body: RegisterInput):
    """Register a new user account."""
    user = user_create(body.username, body.email, body.password, body.full_name, body.role)
    token = create_token(user["id"], user["username"])
    return {"token": token, "user": user}

@app.post("/api/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 form login."""
    user = user_get_by_username(form.username)
    if not user or not verify_password(form.password, user["password"]):
        raise HTTPException(401, "Incorrect username or password")
    token = create_token(user["id"], user["username"])
    # Remove password from response
    user.pop("password", None)
    return {"access_token": token, "token_type": "bearer", "user": user}

@app.post("/api/auth/login/json")
def login_json(body: dict):
    """JSON body login — returns a JWT token."""
    username = body.get("username","")
    password = body.get("password","")
    user = user_get_by_username(username)
    if not user or not verify_password(password, user["password"]):
        raise HTTPException(401, "Incorrect username or password")
    token = create_token(user["id"], user["username"])
    user.pop("password", None)
    return {"token": token, "user": user}

@app.get("/api/auth/me")
def me(user=Depends(require_user)):
    """Return the currently authenticated user's profile."""
    return user

# ── Patient Routes ────────────────────────────────────────
@app.get("/api/patients")
def list_patients(user=Depends(require_user)):
    """List patients belonging to the current user."""
    return patients_list(user["id"])

@app.post("/api/patients")
def create_patient(body: PatientInput, user=Depends(require_user)):
    """Create a new patient record."""
    return patient_create(user["id"], body.model_dump())

@app.get("/api/patients/{patient_id}")
def get_patient(patient_id: str, user=Depends(require_user)):
    """Fetch a patient record by ID."""
    p = patient_get(patient_id)
    if not p: raise HTTPException(404, "Patient not found")
    if p["user_id"] != user["id"]: raise HTTPException(403, "Forbidden")
    # attach session count
    with get_db() as c:
        count = c.execute("SELECT COUNT(*) FROM sessions WHERE patient_id=?", (patient_id,)).fetchone()[0]
    p["session_count"] = count
    return p

@app.put("/api/patients/{patient_id}")
def update_patient(patient_id: str, body: PatientInput, user=Depends(require_user)):
    """Update a patient record."""
    p = patient_get(patient_id)
    if not p: raise HTTPException(404, "Patient not found")
    if p["user_id"] != user["id"]: raise HTTPException(403, "Forbidden")
    patient_update(patient_id, body.model_dump())
    return patient_get(patient_id)

@app.delete("/api/patients/{patient_id}")
def delete_patient(patient_id: str, user=Depends(require_user)):
    """Delete a patient record."""
    p = patient_get(patient_id)
    if not p: raise HTTPException(404, "Patient not found")
    if p["user_id"] != user["id"]: raise HTTPException(403, "Forbidden")
    patient_delete(patient_id)
    return {"deleted": True}

@app.get("/api/patients/{patient_id}/sessions")
def patient_sessions(patient_id: str, user=Depends(require_user)):
    """List all sessions for a given patient."""
    p = patient_get(patient_id)
    if not p: raise HTTPException(404, "Patient not found")
    if p["user_id"] != user["id"]: raise HTTPException(403, "Forbidden")
    with get_db() as c:
        rows = c.execute(
            "SELECT id,status,created_at,symptoms FROM sessions WHERE patient_id=? ORDER BY created_at DESC",
            (patient_id,)
        ).fetchall()
    return [{"id":d["id"],"status":d["status"],"created_at":d["created_at"],
             "description":json.loads(d["symptoms"]).get("description","")[:60]} for d in map(dict,rows)]

# ── Stateless file analysis (no session required) ─────────
@app.post("/api/analyze/file")
async def analyze_file(
    file: UploadFile = File(...),
    lang: str = Query(default="en-US"),
    user=Depends(get_current_user),
):
    """Analyse a file and return the result without persisting to any session."""
    import tempfile

    original_name = _safe_filename(file.filename or "upload")
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_UPLOAD_TYPES:
        raise HTTPException(
            400,
            "Unsupported file type. Supported: PDF, TXT, DICOM, images, audio, video.",
        )
    file_type = ALLOWED_UPLOAD_TYPES[ext]
    payload = await file.read()

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(payload)
        tmp_path = Path(tmp.name)

    annotations = []
    try:
        if file_type == "txt":
            analysis = _extract_text_from_txt(tmp_path)
        elif file_type == "pdf":
            analysis = _extract_text_from_pdf(tmp_path)
        elif file_type == "image":
            result = _analyze_medical_image(tmp_path)
            analysis = result["analysis"]
            annotations = result["annotations"]
        elif file_type == "dicom":
            result = _analyze_dicom(tmp_path)
            analysis = result["analysis"]
            annotations = result["annotations"]
        elif file_type == "audio":
            analysis = _transcribe_audio(tmp_path, language=lang)
        elif file_type == "video":
            analysis = _analyze_video(tmp_path)
        else:
            analysis = ""
    except Exception as e:
        raise HTTPException(400, f"Failed to process file: {e}")
    finally:
        tmp_path.unlink(missing_ok=True)

    return {
        "ok": True,
        "file_name": original_name,
        "file_type": file_type if file_type != "dicom" else "image",
        "analysis": analysis,
        "analysis_preview": analysis[:400],
        "annotations": annotations,
    }


@app.post("/api/analyze/compare")
async def analyze_compare(
    files: List[UploadFile] = File(...),
    user=Depends(get_current_user),
):
    """Compare 2–6 medical images with Claude Vision."""
    import tempfile, base64
    import anthropic as _anthropic

    if len(files) < 2:
        raise HTTPException(400, "At least 2 images required for comparison.")
    if len(files) > 6:
        raise HTTPException(400, "Maximum 6 images for comparison.")

    content = []
    image_names = []

    for i, upload in enumerate(files):
        original_name = _safe_filename(upload.filename or f"image{i+1}")
        ext = Path(original_name).suffix.lower()
        raw = await upload.read()

        if ext == ".dcm":
            # DICOM → JPEG conversion
            with tempfile.NamedTemporaryFile(suffix=".dcm", delete=False) as tmp:
                tmp.write(raw)
                tmp_path = Path(tmp.name)
            try:
                result = _analyze_dicom(tmp_path)
                # Re-render pixel array to bytes for Vision
                import pydicom, io, numpy as np
                from PIL import Image as _PIL
                ds = pydicom.dcmread(str(tmp_path))
                arr = ds.pixel_array.astype(float)
                pmin, pmax = arr.min(), arr.max()
                if pmax > pmin:
                    arr = ((arr - pmin) / (pmax - pmin) * 255).astype("uint8")
                if arr.ndim == 3:
                    arr = arr[arr.shape[0] // 2]
                buf = io.BytesIO()
                _PIL.fromarray(arr).convert("RGB").save(buf, format="JPEG", quality=85)
                raw = buf.getvalue()
            finally:
                tmp_path.unlink(missing_ok=True)
            media_type = "image/jpeg"
        elif ext in IMAGE_MEDIA_TYPES:
            media_type = IMAGE_MEDIA_TYPES[ext]
        else:
            raise HTTPException(400, f"{original_name} is not a supported image type.")

        if len(raw) > _MAX_IMAGE_BYTES:
            raw, media_type = _compress_image_bytes(raw, ext)

        b64 = base64.standard_b64encode(raw).decode("utf-8")
        image_names.append(original_name)
        content.append({"type": "text", "text": f"**Image {i+1}: {original_name}**"})
        content.append({"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}})

    content.append({
        "type": "text",
        "text": (
            f"You are a medical imaging specialist. Compare these {len(files)} medical images:\n\n"
            "1. **Individual Assessment**: Brief findings for each image (1-2 sentences each)\n"
            "2. **Comparison**: Key similarities and differences\n"
            "3. **Progression/Change**: If same patient over time, describe any change\n"
            "4. **Clinical Interpretation**: Overall significance of the comparison\n\n"
            "Be systematic and objective."
        ),
    })

    _client = _anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = _client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": content}],
    )

    return {
        "ok": True,
        "image_count": len(files),
        "image_names": image_names,
        "analysis": response.content[0].text,
    }


@app.post("/api/analyze/ocr")
async def analyze_ocr(file: UploadFile = File(...), user=Depends(get_current_user)):
    """Extract structured medical information from a handwritten or printed medical record image."""
    import tempfile, base64
    import anthropic as _anthropic

    original_name = _safe_filename(file.filename or "upload")
    ext = Path(original_name).suffix.lower()
    if ext not in IMAGE_MEDIA_TYPES and ext != ".dcm":
        raise HTTPException(400, "OCR requires an image file (JPG, PNG, etc.) or DICOM.")

    payload = await file.read()
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(payload)
        tmp_path = Path(tmp.name)

    try:
        if ext == ".dcm":
            import pydicom, io, numpy as np
            from PIL import Image as _PIL
            ds = pydicom.dcmread(str(tmp_path))
            arr = ds.pixel_array.astype(float)
            pmin, pmax = arr.min(), arr.max()
            if pmax > pmin:
                arr = ((arr - pmin) / (pmax - pmin) * 255).astype("uint8")
            if arr.ndim == 3:
                arr = arr[arr.shape[0] // 2]
            buf = io.BytesIO()
            _PIL.fromarray(arr).convert("RGB").save(buf, format="JPEG", quality=85)
            raw = buf.getvalue()
            media_type = "image/jpeg"
        else:
            raw = payload
            media_type = IMAGE_MEDIA_TYPES.get(ext, "image/jpeg")

        if len(raw) > _MAX_IMAGE_BYTES:
            raw, media_type = _compress_image_bytes(raw, ext)

        b64 = base64.standard_b64encode(raw).decode("utf-8")
        _client = _anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = _client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                    {"type": "text", "text": (
                        "You are a medical scribe specialist. This image contains a medical record, "
                        "clinical note, prescription, or handwritten patient notes.\n\n"
                        "Extract ALL readable text and organize it into structured fields:\n\n"
                        "**Patient Information** (name, DOB, gender, ID if visible)\n"
                        "**Chief Complaint / Presenting Symptoms**\n"
                        "**Medical History** (past illnesses, surgeries, family history)\n"
                        "**Current Medications** (drug name, dose, frequency)\n"
                        "**Allergies**\n"
                        "**Physical Examination Findings** (vitals, examination notes)\n"
                        "**Investigations / Test Results** (lab values, imaging reports)\n"
                        "**Assessment / Diagnosis**\n"
                        "**Treatment Plan / Prescriptions**\n"
                        "**Follow-up Instructions**\n\n"
                        "For any section not visible or not applicable, write 'Not documented'.\n"
                        "Preserve original medical terminology. Flag any illegible text with [illegible].\n"
                        "If this is not a medical document, describe what you see."
                    )},
                ],
            }],
        )
        text = response.content[0].text
    except Exception as e:
        raise HTTPException(400, f"OCR failed: {e}")
    finally:
        tmp_path.unlink(missing_ok=True)

    return {
        "ok": True,
        "file_name": original_name,
        "ocr_text": text,
        "ocr_preview": text[:400],
    }


# ── Session Routes ────────────────────────────────────────
@app.post("/api/session/start")
def start_session(symptoms: SymptomInput, user=Depends(get_current_user)):
    uid = user["id"] if user else None
    severity_level = severity_to_level(symptoms.severity)
    severity_score = severity_to_score(severity_level)

    existing_sid = _maybe_reuse_recent_session(symptoms, uid, severity_level)
    if existing_sid:
        existing = session_get(existing_sid)
        existing_reply = ""
        for m in (existing.get("messages") or []):
            if m.get("role") == "ai" and m.get("agent") == "interviewer":
                existing_reply = m.get("text") or ""
                break
        return {
            "session_id": existing_sid,
            "reply": existing_reply,
            "status": "interviewing",
            "safety": _extract_latest_safety_payload(existing_sid),
        }

    sid = str(uuid.uuid4())
    payload = symptoms.model_dump()
    payload["severity"] = severity_score
    payload["severity_level"] = severity_level
    pre_ctx_block = ""
    if symptoms.pre_context:
        ctx_items = [c.strip() for c in symptoms.pre_context if c.strip()]
        if ctx_items:
            pre_ctx_block = (
                "\n\n<uploaded_documents>\n"
                + "\n---\n".join(f"<document>{c}</document>" for c in ctx_items)
                + "\n</uploaded_documents>"
            )
    case = (
        f"Patient presents with:\n- Chief complaint: {symptoms.description}\n"
        f"- Body area: {symptoms.bodyPart}\n- Duration: {symptoms.duration}\n"
        f"- Severity: {severity_level}\n- History: {symptoms.notes or 'None'}"
        f"{pre_ctx_block}\n\nBegin empathetic interview."
    )
    history = [{"role":"user","content":case}]
    reply = call_interviewer(history)
    reply, _qr_start = _extract_quick_replies(reply)
    history.append({"role":"assistant","content":reply})
    messages = [{"role":"ai","agent":"interviewer","text":reply}]
    now = _now()
    with get_db() as c:
        c.execute("""INSERT INTO sessions(id,user_id,patient_id,symptoms,messages,history,turns,status,severity_level,consent_to_provider_review,created_at,updated_at)
            VALUES(?,?,?,?,?,?,0,'interviewing',?,?,?,?)""",
            (sid, uid, symptoms.patient_id,
             json.dumps(payload), json.dumps(messages), json.dumps(history), severity_level,
             1 if symptoms.consent_to_provider_review else 0, now, now))
        c.commit()

    safety = classify_safety(symptoms.description)
    safety_content = json.dumps(
        {
            "final_risk": safety.get("final_risk", safety.get("risk_level", "low")),
            "rule_risk": safety.get("rule_risk", "low"),
            "llm_risk": safety.get("llm_risk", "low"),
            "message": safety.get("message", ""),
            "warning": safety.get("warning", ""),
        },
        ensure_ascii=False,
    )

    session_message_create(sid, role="agent", content=safety_content, agent_type="safety", user_id=uid)
    session_message_create(sid, role="agent", content=reply, agent_type="interviewer", user_id=uid)
    return {
        "session_id":sid,
        "reply":reply,
        "quick_replies": _qr_start,
        "status":"interviewing",
        "safety": {
            "final_risk": safety.get("final_risk", safety.get("risk_level", "low")),
            "message": safety.get("message", ""),
            "warning": safety.get("warning", ""),
            "rule_risk": safety.get("rule_risk", "low"),
            "llm_risk": safety.get("llm_risk", "low"),
        },
    }


@app.post("/api/sessions")
def create_session(symptoms: SymptomInput, user=Depends(get_current_user)):
    return start_session(symptoms, user)

@app.post("/api/session/chat")
def chat(body: ChatMessage, user=Depends(get_current_user)):
    sess = session_get(body.session_id)
    if not sess: raise HTTPException(404,"Session not found")
    if sess["status"]!="interviewing": raise HTTPException(400,f"Status: {sess['status']}")
    if sess.get("user_id") and (not user or sess["user_id"] != user["id"]):
        raise HTTPException(403, "Forbidden")
    history=sess["history"]; messages=sess["messages"]; turns=sess["turns"]+1

    for att in (body.attachments or []):
        att_text = (att or "").strip()
        if not att_text:
            continue
        history.append({"role":"user","content":f"[ATTACHMENT] {att_text}"})
        messages.append({"role":"user","text":f"📎 {att_text}"})
        session_message_create(body.session_id, role="user", content=f"📎 {att_text}", user_id=user["id"] if user else None)

    history.append({"role":"user","content":body.user_message})
    messages.append({"role":"user","text":body.user_message})
    session_message_create(body.session_id, role="user", content=body.user_message, user_id=user["id"] if user else None)

    safety = classify_safety(body.user_message)
    safety_content = json.dumps(
        {
            "final_risk": safety.get("final_risk", safety.get("risk_level", "low")),
            "rule_risk": safety.get("rule_risk", "low"),
            "llm_risk": safety.get("llm_risk", "low"),
            "message": safety.get("message", ""),
            "warning": safety.get("warning", ""),
        },
        ensure_ascii=False,
    )
    session_message_create(
        body.session_id,
        role="agent",
        content=safety_content,
        agent_type="safety",
        user_id=user["id"] if user else None,
    )

    # Hard-stop the interview so a reluctant model cannot keep asking questions
    # indefinitely; the diagnosis phase should receive the best available case.
    MAX_TURNS = 12
    reply = call_interviewer(normalize_history_for_interviewer(history))
    ready = "[READY_FOR_DIAGNOSIS]" in reply
    clean = reply.replace("[READY_FOR_DIAGNOSIS]","").strip()

    clean, quick_replies = _extract_quick_replies(clean)

    # When the cap is reached, close the intake politely even if the model did
    # not emit READY_FOR_DIAGNOSIS. This keeps the UX deterministic.
    force_trigger = turns >= MAX_TURNS
    if force_trigger and not ready:
        clean = clean + "\n\nThank you for sharing all of that. I now have enough information to proceed with a thorough analysis."

    history.append({"role":"assistant","content":clean})
    messages.append({"role":"ai","agent":"interviewer","text":clean})
    session_message_create(body.session_id, role="agent", content=clean, agent_type="interviewer", user_id=user["id"] if user else None)
    trigger = ready or force_trigger
    session_update(body.session_id,history=history,messages=messages,
        turns=turns,status="analyzing" if trigger else "interviewing")

    symptoms_ctx = ""
    try:
        s_payload = sess.get("symptoms") or {}
        symptoms_ctx = s_payload.get("description", "") if isinstance(s_payload, dict) else ""
    except Exception:
        pass
    agent_commentary = {}
    if not trigger:
        try:
            agent_commentary = call_agent_commentary(
                user_message=body.user_message,
                interviewer_reply=clean,
                symptoms_context=symptoms_ctx,
            )
        except Exception:
            agent_commentary = {}

    return {
        "reply":clean,
        "quick_replies": quick_replies,
        "status":"analyzing" if trigger else "interviewing",
        "trigger_diagnose":trigger,
        "agent_commentary": agent_commentary,
        "safety": {
            "final_risk": safety.get("final_risk", safety.get("risk_level", "low")),
            "message": safety.get("message", ""),
            "warning": safety.get("warning", ""),
            "rule_risk": safety.get("rule_risk", "low"),
            "llm_risk": safety.get("llm_risk", "low"),
        },
    }

@app.post("/api/session/diagnose")
def diagnose(body: DiagnoseRequest, user=Depends(get_current_user)):
    sess = session_get(body.session_id)
    if not sess: raise HTTPException(404,"Session not found")
    if sess.get("user_id") and (not user or sess["user_id"] != user["id"]):
        raise HTTPException(403, "Forbidden")
    s = sess["symptoms"]
    diagnosis_context = build_diagnosis_context(sess)
    case_text = diagnosis_context["case_text"]
    image_analyses = diagnosis_context["image_analyses"]

    # Visual findings often use descriptive language; rewriting them into medical
    # terms improves retrieval without letting uploaded text control instructions.
    image_medical_terms = rewrite_image_findings_for_rag(image_analyses) if image_analyses else ""
    rag_query = build_rag_query(s, image_medical_terms)

    # Extended thinking improves difficult differentials, but it is provider/model
    # dependent. The standard path preserves diagnosis availability if CoT fails.
    try:
        diagnosis, diag_cot, refs = call_diagnostician_cot(case_text, rag_query)
        review, critic_cot = call_critic_cot(case_text, diagnosis)
        cot = {"diagnostician": diag_cot, "critic": critic_cot}
    except Exception:
        diagnosis, refs = call_diagnostician(case_text, rag_query)
        review = call_critic(case_text, diagnosis)
        cot = None

    session_message_create(body.session_id, role="agent", content=diagnosis, agent_type="diagnostician", user_id=user["id"] if user else None)
    session_message_create(body.session_id, role="agent", content=review, agent_type="critic", user_id=user["id"] if user else None)

    # Roundtable logs are explanatory UI evidence only; diagnosis persistence
    # should not fail if this secondary commentary cannot be generated.
    agent_logs = []
    try:
        agent_logs = call_diagnostic_roundtable(case_text, diagnosis, review)
    except Exception:
        agent_logs = []

    session_update(body.session_id, diagnosis=diagnosis, review=review, refs=refs, status="done",
                   cot=json.dumps(cot) if cot else None)
    return {"status": "done", "diagnosis": diagnosis, "review": review, "refs": refs, "cot": cot, "agent_logs": agent_logs}

# ── SSE helpers ───────────────────────────────────────────
def _sse(type_: str, **kwargs) -> dict:
    """Format a single SSE data frame."""
    return {"data": json.dumps({"type": type_, **kwargs}, ensure_ascii=False)}


_QR_RE = re.compile(r"QUICK_REPLIES\s*:\s*(.+?)(?:\n|$)", re.IGNORECASE)

def _extract_quick_replies(text: str) -> tuple[str, list[str]]:
    """Strip QUICK_REPLIES: ... from reply text and return (clean_text, chips)."""
    m = _QR_RE.search(text)
    if not m:
        return text.strip(), []
    chips = [c.strip() for c in m.group(1).split("|") if c.strip()]
    clean = _QR_RE.sub("", text).strip()
    return clean, chips


# ── /api/session/chat/stream ──────────────────────────────
async def _chat_stream_gen(body: "ChatMessage", user):
    """
    SSE generator for the chat endpoint.
    Events emitted (in order):
      safety_result → interviewer_reply → agent_message × 2 → done
    If trigger_diagnose the frontend should call /api/session/diagnose/stream next.
    """
    try:
        sess = await asyncio.to_thread(session_get, body.session_id)
        if not sess:
            yield _sse("error", message="Session not found"); return
        if sess["status"] != "interviewing":
            yield _sse("error", message=f"Status: {sess['status']}"); return
        if sess.get("user_id") and (not user or sess["user_id"] != user["id"]):
            yield _sse("error", message="Forbidden"); return

        uid = user["id"] if user else None
        history = sess["history"]
        messages = sess["messages"]
        turns = sess["turns"] + 1

        # Attachments
        for att in (body.attachments or []):
            att_text = (att or "").strip()
            if not att_text: continue
            history.append({"role": "user", "content": f"[ATTACHMENT] {att_text}"})
            messages.append({"role": "user", "text": f"📎 {att_text}"})
            await asyncio.to_thread(
                session_message_create, body.session_id, "user", f"📎 {att_text}", None, uid
            )

        history.append({"role": "user", "content": body.user_message})
        messages.append({"role": "user", "text": body.user_message})
        await asyncio.to_thread(
            session_message_create, body.session_id, "user", body.user_message, None, uid
        )

        # Safety check
        safety = await asyncio.to_thread(classify_safety, body.user_message)
        safety_content = json.dumps({
            "final_risk": safety.get("final_risk", safety.get("risk_level", "low")),
            "rule_risk": safety.get("rule_risk", "low"),
            "llm_risk": safety.get("llm_risk", "low"),
            "message": safety.get("message", ""),
            "warning": safety.get("warning", ""),
        }, ensure_ascii=False)
        await asyncio.to_thread(
            session_message_create, body.session_id, "agent", safety_content, "safety", uid
        )
        yield _sse("safety_result",
                   final_risk=safety.get("final_risk", safety.get("risk_level", "low")),
                   message=safety.get("message", ""),
                   warning=safety.get("warning", ""),
                   rule_risk=safety.get("rule_risk", "low"),
                   llm_risk=safety.get("llm_risk", "low"))

        # Interviewer
        MAX_TURNS = 12
        reply = await call_interviewer_async(normalize_history_for_interviewer(history))
        ready = "[READY_FOR_DIAGNOSIS]" in reply
        clean = reply.replace("[READY_FOR_DIAGNOSIS]", "").strip()

        clean, quick_replies = _extract_quick_replies(clean)
        force_trigger = turns >= MAX_TURNS
        if force_trigger and not ready:
            clean = clean + "\n\nThank you for sharing all of that. I now have enough information to proceed with a thorough analysis."
        trigger = ready or force_trigger

        history.append({"role": "assistant", "content": clean})
        messages.append({"role": "ai", "agent": "interviewer", "text": clean})
        await asyncio.to_thread(
            session_message_create, body.session_id, "agent", clean, "interviewer", uid
        )
        await asyncio.to_thread(
            session_update, body.session_id,
            history=history, messages=messages,
            turns=turns, status="analyzing" if trigger else "interviewing"
        )

        yield _sse("interviewer_reply", text=clean, trigger=trigger, quick_replies=quick_replies)

        # Inter-agent commentary (only when NOT triggering diagnosis)
        if not trigger:
            symptoms_ctx = ""
            try:
                s_pay = sess.get("symptoms") or {}
                symptoms_ctx = s_pay.get("description", "") if isinstance(s_pay, dict) else ""
            except Exception:
                pass

            commentary = await call_agent_commentary_async(body.user_message, clean, symptoms_ctx)

            if commentary.get("safety_to_interviewer"):
                await asyncio.sleep(0.2)
                yield _sse("agent_message",
                           from_agent="safety", to_agent="interviewer",
                           text=commentary["safety_to_interviewer"], phase="intake")

            if commentary.get("interviewer_to_safety"):
                await asyncio.sleep(0.35)
                yield _sse("agent_message",
                           from_agent="interviewer", to_agent="safety",
                           text=commentary["interviewer_to_safety"], phase="intake")

        yield _sse("done")

    except Exception as exc:
        yield _sse("error", message=str(exc))


@app.post("/api/session/chat/stream")
async def chat_stream(body: ChatMessage, user=Depends(get_current_user)):
    """SSE streaming version of /api/session/chat"""
    return EventSourceResponse(_chat_stream_gen(body, user))


# ── /api/session/diagnose/stream ──────────────────────────
async def _diagnose_stream_gen(body: "DiagnoseRequest", user):
    """
    SSE generator for the diagnose endpoint.
    Events: phase_sep → agent_message (diagnostician) → agent_message (critic)
            → agent_message × 3 (roundtable) → diagnosis_ready → done
    """
    try:
        sess = await asyncio.to_thread(session_get, body.session_id)
        if not sess:
            yield _sse("error", message="Session not found"); return
        if sess.get("user_id") and (not user or sess["user_id"] != user["id"]):
            yield _sse("error", message="Forbidden"); return

        uid = user["id"] if user else None
        s = sess["symptoms"]

        diagnosis_context = build_diagnosis_context(sess)
        case_text = diagnosis_context["case_text"]
        image_analyses = diagnosis_context["image_analyses"]

        from agents import rewrite_image_findings_for_rag as _rw
        image_medical_terms = await asyncio.to_thread(_rw, image_analyses) if image_analyses else ""
        rag_query = build_rag_query(s, image_medical_terms)

        # ── IMAGING ANALYSIS phase — only runs when the session has uploaded images ──
        if image_analyses:
            yield _sse("phase_sep", label="IMAGING ANALYSIS")
            await asyncio.sleep(0.15)
            yield _sse("agent_message",
                       from_agent="imaging", to_agent=None,
                       text=f"Reviewing {len(image_analyses)} uploaded medical image(s). Extracting clinical findings…",
                       phase="imaging")
            for idx, analysis in enumerate(image_analyses, 1):
                excerpt = extract_key_findings_excerpt(analysis)
                if len(image_analyses) > 1:
                    label = f"Image {idx} — {excerpt}"
                else:
                    label = excerpt
                await asyncio.sleep(0.2)
                yield _sse("agent_message",
                           from_agent="imaging", to_agent=None,
                           text=label + ("…" if len(excerpt) >= 200 else ""),
                           phase="imaging")
            await asyncio.sleep(0.25)
            yield _sse("agent_message",
                       from_agent="imaging", to_agent="diagnostician",
                       text=f"Imaging analysis complete. Key medical terms forwarded for RAG retrieval: {image_medical_terms or 'N/A'}",
                       phase="imaging")

        # ── DIAGNOSTIC ANALYSIS phase ──
        yield _sse("phase_sep", label="DIAGNOSTIC ANALYSIS")
        await asyncio.sleep(0.15)
        yield _sse("agent_message",
                   from_agent="diagnostician", to_agent=None,
                   text="Case received. Querying medical knowledge base (MedQuAD + PubMed, hybrid dense + BM25 search)…",
                   phase="diagnosis")

        try:
            diagnosis, diag_thinking, refs = await call_diagnostician_cot_async(case_text, rag_query)
            review, critic_thinking = await call_critic_cot_async(case_text, diagnosis)
            cot = {"diagnostician": diag_thinking, "critic": critic_thinking}
        except Exception:
            diagnosis, refs = await call_diagnostician_async(case_text, rag_query)
            review = await call_critic_async(case_text, diagnosis)
            cot = None

        if refs:
            await asyncio.sleep(0.25)
            yield _sse("agent_message",
                       from_agent="diagnostician", to_agent=None,
                       text=f"Retrieved {len(refs)} supporting references from knowledge base.",
                       phase="diagnosis")

        await asyncio.sleep(0.3)
        yield _sse("agent_message",
                   from_agent="diagnostician", to_agent="critic",
                   text=diagnosis, phase="diagnosis")

        # ── PEER REVIEW phase ──
        await asyncio.sleep(0.4)
        yield _sse("phase_sep", label="PEER REVIEW")
        await asyncio.sleep(0.2)
        yield _sse("agent_message",
                   from_agent="critic", to_agent=None,
                   text="Peer review initiated. Evaluating differential for clinical soundness and completeness…",
                   phase="review")

        await asyncio.sleep(0.35)
        yield _sse("agent_message",
                   from_agent="critic", to_agent="diagnostician",
                   text=review, phase="review")

        # Roundtable debate
        roundtable = await call_diagnostic_roundtable_async(case_text, diagnosis, review)
        for entry in roundtable:
            await asyncio.sleep(0.35)
            yield _sse("agent_message",
                       from_agent=entry["from_agent"],
                       to_agent=entry["to_agent"],
                       text=entry["text"], phase="review")

        # Final safety clearance
        await asyncio.sleep(0.25)
        yield _sse("agent_message",
                   from_agent="safety", to_agent=None,
                   text="Final safety sweep complete. No escalation pathway required at this stage.",
                   phase="review")

        # Persist to DB
        await asyncio.to_thread(
            session_message_create, body.session_id, "agent", diagnosis, "diagnostician", uid
        )
        await asyncio.to_thread(
            session_message_create, body.session_id, "agent", review, "critic", uid
        )
        await asyncio.to_thread(
            session_update, body.session_id,
            diagnosis=diagnosis, review=review, refs=refs, status="done",
            cot=json.dumps(cot) if cot else None
        )

        yield _sse("diagnosis_ready",
                   diagnosis=diagnosis, review=review,
                   refs=refs, cot=cot)
        yield _sse("done")

    except Exception as exc:
        yield _sse("error", message=str(exc))


@app.post("/api/session/diagnose/stream")
async def diagnose_stream(body: DiagnoseRequest, user=Depends(get_current_user)):
    """SSE streaming version of /api/session/diagnose"""
    return EventSourceResponse(_diagnose_stream_gen(body, user))


# ── (existing non-stream endpoints continue below) ────────

@app.get("/api/session/{session_id}")
def get_session(session_id: str, user=Depends(get_current_user)):
    sess = session_get(session_id)
    if not sess: raise HTTPException(404,"Session not found")
    if sess.get("user_id") and (not user or (not _is_provider(user) and sess["user_id"] != user["id"])):
        raise HTTPException(403, "Forbidden")
    return sess

@app.delete("/api/sessions/{session_id}", status_code=204)
def delete_session(session_id: str, user=Depends(get_current_user)):
    """
    Delete a session and all associated data (messages, uploads).
    Users may only delete their own sessions; providers may delete any.
    """
    sess = session_get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    uid = user["id"] if user else None
    if not _is_provider(user) and sess.get("user_id") and sess["user_id"] != uid:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Delete physical upload files from disk
    with get_db() as c:
        rows = c.execute(
            "SELECT file_path FROM uploads WHERE session_id=?", (session_id,)
        ).fetchall()
    for row in rows:
        try:
            Path(row["file_path"]).unlink(missing_ok=True)
        except Exception:
            pass

    # Delete session row — messages and uploads cascade via FK
    with get_db() as c:
        c.execute("PRAGMA foreign_keys = ON")
        c.execute("DELETE FROM sessions WHERE id=?", (session_id,))
        c.commit()


@app.patch("/api/sessions/{session_id}/verdict", status_code=200)
def set_session_verdict(session_id: str, body: VerdictInput, user=Depends(require_user)):
    """Provider submits approve/flag verdict with optional revision note."""
    if body.verdict not in ("approved", "flagged"):
        raise HTTPException(status_code=400, detail="verdict must be 'approved' or 'flagged'")
    if not _is_provider(user):
        raise HTTPException(status_code=403, detail="Provider role required")
    sess = session_get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    with get_db() as c:
        c.execute(
            "UPDATE sessions SET provider_verdict=?, provider_note=?, updated_at=? WHERE id=?",
            (body.verdict, body.note.strip(), _now(), session_id),
        )
        c.commit()
    return {"session_id": session_id, "verdict": body.verdict, "note": body.note.strip()}


@app.get("/api/sessions")
def list_sessions(
    status: Optional[str] = Query(default=None),
    severity_level: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    from_date: Optional[str] = Query(default=None, alias="from"),
    to: Optional[str] = Query(default=None),
    limit: int = Query(default=50),
    offset: int = Query(default=0),
    user=Depends(require_user),
):
    if _is_provider(user):
        return sessions_list(
            status=status,
            severity_level=severity_level,
            q=q,
            date_from=from_date,
            date_to=to,
            limit=limit,
            offset=offset,
        )
    return sessions_list(
        user["id"],
        status=status,
        severity_level=severity_level,
        q=q,
        date_from=from_date,
        date_to=to,
        limit=limit,
        offset=offset,
    )


@app.get("/api/provider/sessions")
def provider_sessions(
    status: Optional[str] = Query(default=None),
    severity_level: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    from_date: Optional[str] = Query(default=None, alias="from"),
    to: Optional[str] = Query(default=None),
    limit: int = Query(default=50),
    offset: int = Query(default=0),
    user=Depends(require_user),
):
    if not _is_provider(user):
        raise HTTPException(403, "Provider access required")
    return provider_sessions_list(
        status=status,
        severity_level=severity_level,
        q=q,
        date_from=from_date,
        date_to=to,
        limit=limit,
        offset=offset,
    )


@app.post("/api/sessions/{session_id}/messages")
def store_session_message(session_id: str, body: MessageInput, user=Depends(require_user)):
    sess = session_get(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    if sess.get("user_id") and (not _is_provider(user) and sess["user_id"] != user["id"]):
        raise HTTPException(403, "Forbidden")

    session_message_create(
        session_id=session_id,
        role=body.role,
        content=body.content,
        agent_type=body.agent_type,
        user_id=user["id"]
    )

    legacy_messages = sess["messages"]
    if body.role == "user":
        legacy_messages.append({"role": "user", "text": body.content})
    elif body.role == "agent":
        legacy_messages.append({"role": "ai", "agent": body.agent_type, "text": body.content})
    else:
        legacy_messages.append({"role": "system", "text": body.content})
    session_update(session_id, messages=legacy_messages)

    return {"ok": True}


@app.get("/api/sessions/{session_id}/messages")
def get_session_messages(session_id: str, user=Depends(require_user)):
    sess = session_get(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    if sess.get("user_id") and (not _is_provider(user) and sess["user_id"] != user["id"]):
        raise HTTPException(403, "Forbidden")
    return session_messages_raw(session_id)


@app.get("/api/sessions/{session_id}/uploads")
def get_session_uploads(session_id: str, user=Depends(get_current_user)):
    sess = session_get(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    if sess.get("user_id") and (not user or (not _is_provider(user) and sess["user_id"] != user["id"])):
        raise HTTPException(403, "Forbidden")
    return session_uploads_list(session_id)


@app.post("/api/sessions/{session_id}/upload")
async def upload_session_file(session_id: str, file: UploadFile = File(...), user=Depends(get_current_user)):
    sess = session_get(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    if sess.get("user_id") and (not user or sess["user_id"] != user["id"]):
        raise HTTPException(403, "Forbidden")

    original_name = _safe_filename(file.filename or "upload")
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_UPLOAD_TYPES:
        raise HTTPException(400, "Only .pdf, .txt, and image files (.jpg, .jpeg, .png, .gif, .bmp, .webp) are supported")

    file_type = ALLOWED_UPLOAD_TYPES[ext]
    upload_id = str(uuid.uuid4())
    session_dir = UPLOAD_ROOT / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{upload_id}{ext}"
    stored_path = session_dir / stored_name

    payload = await file.read()
    stored_path.write_bytes(payload)

    try:
        if file_type == "txt":
            extracted_text = _extract_text_from_txt(stored_path)
        elif file_type == "image":
            result = _analyze_medical_image(stored_path)
            extracted_text = result["analysis"]
        else:
            extracted_text = _extract_text_from_pdf(stored_path)
    except Exception as e:
        raise HTTPException(400, f"Failed to process file: {e}")

    uploaded_at = _now()
    with get_db() as c:
        c.execute(
            """INSERT INTO uploads(id,session_id,file_name,file_type,file_path,extracted_text,uploaded_at)
               VALUES(?,?,?,?,?,?,?)""",
            (
                upload_id,
                session_id,
                original_name,
                file_type,
                str(stored_path),
                extracted_text,
                uploaded_at,
            ),
        )
        c.commit()

    # Push extracted content into session history so next chat turn can use it.
    context_text = extracted_text.strip()
    if len(context_text) > MAX_UPLOAD_CONTEXT_CHARS:
        context_text = context_text[:MAX_UPLOAD_CONTEXT_CHARS] + "\n...[truncated]"

    if file_type == "image":
        context_label = f"Uploaded medical image: {original_name}. AI analysis of this image:\n\n"
    else:
        context_label = f"Uploaded {file_type.upper()} file: {original_name}. Use the following extracted text as additional clinical context:\n\n"

    history = sess.get("history", [])
    history.append({
        "role": "system",
        "content": context_label + context_text,
    })

    legacy_messages = sess.get("messages", [])
    legacy_messages.append({
        "role": "system",
        "text": f"Uploaded file context added: {original_name} ({file_type})",
    })
    session_update(session_id, history=history, messages=legacy_messages)

    session_message_create(
        session_id=session_id,
        role="system",
        content=(
            f"Uploaded file: {original_name} ({file_type}), analysis length {len(extracted_text)} chars.\n\n"
            f"{context_text}"
        ),
        user_id=user["id"] if user else None,
    )

    return {
        "ok": True,
        "upload": {
            "id": upload_id,
            "session_id": session_id,
            "file_name": original_name,
            "file_type": file_type,
            "file_path": str(stored_path),
            "uploaded_at": uploaded_at,
            "extracted_text_length": len(extracted_text),
            "extracted_text_preview": extracted_text[:500],
        },
    }

# ── Export ────────────────────────────────────────────────
@app.get("/api/session/{session_id}/export/pdf")
def export_pdf(session_id: str):
    sess = session_get(session_id)
    if not sess: raise HTTPException(404,"Session not found")
    if sess["status"]!="done": raise HTTPException(400,"Not complete")
    pdf_bytes = generate_pdf(sess)
    fname = f"Clinora_{session_id[:8]}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return Response(content=pdf_bytes,media_type="application/pdf",
        headers={"Content-Disposition":f'attachment; filename="{fname}"'})

@app.get("/api/session/{session_id}/export/json")
def export_json(session_id: str):
    sess = session_get(session_id)
    if not sess: raise HTTPException(404,"Session not found")
    data = {k:v for k,v in sess.items() if k!="history"}
    data["exported_at"] = _now()
    fname = f"Clinora_{session_id[:8]}_{datetime.now().strftime('%Y%m%d')}.json"
    return Response(content=json.dumps(data,indent=2,ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition":f'attachment; filename="{fname}"'})

# ── Mistral Peer Review ────────────────────────────────────
@app.get("/api/session/{session_id}/peer-review")
def session_peer_review(session_id: str, user=Depends(get_current_user)):
    """
    Get an independent second opinion from Mistral on the Claude diagnosis.
    Result is cached in sessions.mistral_peer_review so we don't charge twice.
    """
    sess = session_get(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    # Only enforce ownership when both session and requester have a user_id
    if user and sess.get("user_id") and sess["user_id"] != user["id"]:
        raise HTTPException(403, "Forbidden")
    if not sess.get("diagnosis"):
        raise HTTPException(400, "No diagnosis available for this session yet")

    # Return cached result if already evaluated
    if sess.get("mistral_peer_review"):
        try:
            return json.loads(sess["mistral_peer_review"])
        except Exception:
            pass

    # Build symptoms summary — sess["symptoms"] is already a parsed dict
    sym = sess.get("symptoms") or {}
    if isinstance(sym, str):
        try: sym = json.loads(sym)
        except Exception: sym = {}
    symptoms_parts = []
    if sym.get("description"):    symptoms_parts.append(f"Chief complaint: {sym['description']}")
    if sym.get("body_part"):      symptoms_parts.append(f"Location: {sym['body_part']}")
    if sym.get("duration"):       symptoms_parts.append(f"Duration: {sym['duration']}")
    if sess.get("severity_level"):symptoms_parts.append(f"Severity: {sess['severity_level']}")
    symptoms_text = "\n".join(symptoms_parts) or "No symptom details available"

    review_result = run_mistral_diagnosis_review(
        symptoms_text=symptoms_text,
        diagnosis_text=sess["diagnosis"],
        review_text=sess.get("review") or "",
    )

    # Cache in DB
    with get_db() as c:
        c.execute("UPDATE sessions SET mistral_peer_review=? WHERE id=?",
                  (json.dumps(review_result), session_id))
        c.commit()

    return review_result

# ── MedQA Eval ────────────────────────────────────────────
@app.get("/api/eval/questions")
def get_questions():
    return {"questions":[{"id":q["id"],"question":q["question"],"options":q["options"],"category":q["category"]} for q in SAMPLE_QUESTIONS]}

@app.post("/api/eval/run")
def run_eval(body: EvalRequest):
    q = next((x for x in SAMPLE_QUESTIONS if x["id"]==body.question_id), None)
    if not q: raise HTTPException(404,"Question not found")
    result = {"question_id":body.question_id,"correct":q["correct"],"category":q["category"]}
    if body.mode in ("single","both"):
        s = run_single_llm(q["question"], q["options"])
        result["single"] = s; result["single_correct"] = s["answer"]==q["correct"]
    if body.mode in ("multi","both"):
        m = run_multi_agent(q["question"], q["options"])
        result["multi"] = m; result["multi_correct"] = m["answer"]==q["correct"]
        # Mistral acts as an independent reviewer for the Claude multi-agent output
        mj = run_mistral_judge(
            question=q["question"],
            options=q["options"],
            claude_answer=m["answer"],
            claude_reasoning=m["reasoning"],
            correct_answer=q["correct"],
        )
        result["mistral_judge"] = mj
    eid = str(uuid.uuid4())
    mj = result.get("mistral_judge", {})
    with get_db() as c:
        c.execute("""INSERT INTO eval_runs(id,question_id,single_answer,single_reasoning,
            multi_answer,multi_reasoning,multi_pipeline,correct_answer,category,
            single_correct,multi_correct,mistral_verdict,mistral_reasoning,mistral_correct,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (eid, body.question_id,
             result.get("single",{}).get("answer",""), result.get("single",{}).get("reasoning",""),
             result.get("multi",{}).get("answer",""),  result.get("multi",{}).get("reasoning",""),
             json.dumps(result.get("multi",{}).get("pipeline",{})),
             q["correct"], q["category"],
             1 if result.get("single_correct") else 0,
             1 if result.get("multi_correct")  else 0,
             mj.get("verdict",""), mj.get("assessment",""),
             1 if mj.get("correct") else 0,
             _now()))
        c.commit()
    return result

@app.get("/api/eval/history")
def eval_history():
    with get_db() as c:
        rows = c.execute("""SELECT question_id,single_answer,multi_answer,correct_answer,
            category,single_correct,multi_correct,mistral_verdict,mistral_reasoning,mistral_correct,created_at
            FROM eval_runs ORDER BY created_at DESC LIMIT 50""").fetchall()
    records = [dict(r) for r in rows]
    if records:
        total=len(records); s_total=sum(1 for r in records if r["single_answer"]); m_total=sum(1 for r in records if r["multi_answer"])
        s_correct=sum(r["single_correct"] or 0 for r in records); m_correct=sum(r["multi_correct"] or 0 for r in records)
        mj_total=sum(1 for r in records if r.get("mistral_verdict") and r["mistral_verdict"] not in ("","UNAVAILABLE","ERROR"))
        mj_agree=sum(1 for r in records if r.get("mistral_correct"))
        cats={}
        for r in records:
            cat=r["category"]
            if cat not in cats: cats[cat]={"single":0,"single_c":0,"multi":0,"multi_c":0}
            if r["single_answer"]: cats[cat]["single"]+=1; cats[cat]["single_c"]+=r["single_correct"] or 0
            if r["multi_answer"]:  cats[cat]["multi"]+=1;  cats[cat]["multi_c"]+=r["multi_correct"] or 0
        stats={"total":total,"single_accuracy":round(s_correct/s_total*100,1) if s_total else 0,
               "multi_accuracy":round(m_correct/m_total*100,1) if m_total else 0,
               "mistral_agreement":round(mj_agree/mj_total*100,1) if mj_total else None,
               "improvement":round((m_correct-s_correct)/s_total*100,1) if s_total else 0,"by_category":cats}
    else:
        stats={"total":0,"single_accuracy":0,"multi_accuracy":0,"improvement":0,"by_category":{}}
    return {"records":records,"stats":stats}
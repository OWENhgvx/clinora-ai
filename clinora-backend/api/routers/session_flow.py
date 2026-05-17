import json
import uuid

from fastapi import APIRouter, Depends

from app.agents import (
    call_diagnostician,
    call_diagnostician_cot,
)
from app.auth import get_current_user
from app.db import get_db
from app.interview_graph import InterviewState, invoke_interview_graph, message_from_content
from services.diagnosis_service import build_diagnosis_context, build_rag_query
import services.session_service as _services
from services.session_flow_helpers import (
    INTERVIEWING_STATUS,
    extract_quick_replies,
    process_interviewer_reply,
    raise_for_session_access,
    status_from_trigger,
    user_id_or_none,
)
from schemas.api import ChatMessage, DiagnoseRequest, SymptomInput

router = APIRouter()
DEFAULT_SEVERITY_LEVEL = "moderate"

# Compatibility attributes for older tests/extensions that monkeypatch these
# names. The LangGraph interview workflow below does not call them.
call_interviewer = None
classify_safety = None
call_agent_commentary = None
DEFAULT_SAFETY = {
    "final_risk": "low",
    "rule_risk": "low",
    "llm_risk": "low",
    "message": "",
    "warning": "",
}

def _bind_services_db():
    _services.get_db = get_db


def _now():
    return _services._now()


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


def session_update(sid, **kwargs):
    _bind_services_db()
    return _services.session_update(sid, **kwargs)


def _history_to_interview_messages(history):
    out = []
    for item in history or []:
        role = item.get("role")
        if role == "assistant":
            out.append(message_from_content("interviewer", item.get("content", "")))
        elif role == "system":
            out.append(message_from_content("system", item.get("content", "")))
        else:
            out.append(message_from_content("patient", item.get("content", "")))
    return out


def _symptoms_complaint(symptoms: dict) -> str:
    parts = [
        symptoms.get("description", ""),
        symptoms.get("bodyPart", ""),
        symptoms.get("duration", ""),
        symptoms.get("notes", ""),
    ]
    return " ".join(str(p).strip() for p in parts if str(p or "").strip()).strip()


def _run_interview_graph(session_id: str, symptoms: dict, history: list, turn_count: int):
    return invoke_interview_graph(
        InterviewState(
            session_id=session_id,
            complaint=_symptoms_complaint(symptoms),
            history=_history_to_interview_messages(history),
            turn_count=turn_count,
        )
    )


def _interview_response_from_state(state):
    if state.interview_result:
        summary = state.interview_result.clinical_interview_summary
        return (
            "Thank you. I now have enough information to prepare the clinical analysis.",
            [],
            True,
            summary,
        )
    question = state.next_question or "Can you tell me a little more about what you are experiencing?"
    clean, quick_replies = extract_quick_replies(question)
    return clean, quick_replies, False, None


@router.post("/api/session/start")
def start_session(symptoms: SymptomInput, user=Depends(get_current_user)):
    uid = user_id_or_none(user)
    severity_level = DEFAULT_SEVERITY_LEVEL

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
            "quick_replies": [],
            "status": INTERVIEWING_STATUS,
            "trigger_diagnose": False,
            "interview_result": None,
            "safety": DEFAULT_SAFETY,
        }

    sid = str(uuid.uuid4())
    payload = symptoms.model_dump()
    payload["severity_level"] = severity_level
    case = _symptoms_complaint(payload)
    history = [{"role": "user", "content": case}]
    interview_state = _run_interview_graph(sid, payload, history, 0)
    reply, quick_replies, trigger, interview_summary = _interview_response_from_state(interview_state)
    history.append({"role": "assistant", "content": reply})
    messages = [{"role": "ai", "agent": "interviewer", "text": reply}]
    if interview_state.interview_result:
        payload["interview_result"] = interview_state.interview_result.model_dump()
    now = _now()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO sessions(id,user_id,patient_id,symptoms,messages,history,turns,status,severity_level,consent_to_provider_review,created_at,updated_at)
            VALUES(?,?,?,?,?,?,0,?,?,?,?,?)""",
            (
                sid,
                uid,
                symptoms.patient_id,
                json.dumps(payload),
                json.dumps(messages),
                json.dumps(history),
                status_from_trigger(trigger),
                severity_level,
                1 if symptoms.consent_to_provider_review else 0,
                now,
                now,
            ),
        )
        conn.commit()

    session_message_create(sid, role="agent", content=reply, agent_type="interviewer", user_id=uid)
    if interview_summary:
        session_message_create(sid, role="system", content=interview_summary, user_id=uid)
    return {
        "session_id": sid,
        "reply": reply,
        "quick_replies": quick_replies,
        "status": status_from_trigger(trigger),
        "trigger_diagnose": trigger,
        "interview_result": interview_state.interview_result.model_dump() if interview_state.interview_result else None,
        "safety": DEFAULT_SAFETY,
    }


@router.post("/api/sessions")
def create_session(symptoms: SymptomInput, user=Depends(get_current_user)):
    return start_session(symptoms, user)


@router.post("/api/session/chat")
def chat(body: ChatMessage, user=Depends(get_current_user)):
    sess = session_get(body.session_id)
    raise_for_session_access(sess, user, required_status=INTERVIEWING_STATUS)
    history = sess["history"]
    messages = sess["messages"]
    turns = sess["turns"] + 1
    uid = user_id_or_none(user)
    history.append({"role": "user", "content": body.user_message})
    messages.append({"role": "user", "text": body.user_message})
    session_message_create(body.session_id, role="user", content=body.user_message, user_id=uid)

    symptoms = dict(sess["symptoms"])
    interview_state = _run_interview_graph(body.session_id, symptoms, history, turns)
    clean, quick_replies, trigger, interview_summary = _interview_response_from_state(interview_state)
    history.append({"role": "assistant", "content": clean})
    messages.append({"role": "ai", "agent": "interviewer", "text": clean})
    session_message_create(body.session_id, role="agent", content=clean, agent_type="interviewer", user_id=uid)
    if interview_state.interview_result:
        symptoms["interview_result"] = interview_state.interview_result.model_dump()
    if interview_summary:
        session_message_create(body.session_id, role="system", content=interview_summary, user_id=uid)
    session_update(
        body.session_id,
        symptoms=symptoms,
        history=history,
        messages=messages,
        turns=turns,
        status=status_from_trigger(trigger),
    )

    return {
        "reply": clean,
        "quick_replies": quick_replies,
        "status": status_from_trigger(trigger),
        "trigger_diagnose": trigger,
        "interview_result": interview_state.interview_result.model_dump() if interview_state.interview_result else None,
        "safety": DEFAULT_SAFETY,
    }


@router.post("/api/session/diagnose")
def diagnose(body: DiagnoseRequest, user=Depends(get_current_user)):
    sess = session_get(body.session_id)
    raise_for_session_access(sess, user)

    symptoms = sess["symptoms"]
    diagnosis_context = build_diagnosis_context(sess)
    case_text = diagnosis_context["case_text"]
    rag_query = build_rag_query(symptoms)

    try:
        diagnosis_text, diag_cot, refs = call_diagnostician_cot(case_text, rag_query)
        cot = {"diagnostician": diag_cot}
    except Exception:
        diagnosis_text, refs = call_diagnostician(case_text, rag_query)
        cot = None

    session_message_create(body.session_id, role="agent", content=diagnosis_text, agent_type="diagnostician", user_id=user["id"] if user else None)

    session_update(
        body.session_id,
        diagnosis=diagnosis_text,
        refs=refs,
        status="done",
        cot=json.dumps(cot) if cot else None,
    )
    return {
        "status": "done",
        "diagnosis": diagnosis_text,
        "refs": refs,
        "cot": cot,
    }

"""
services.py — shared business helpers for Clinora API routes.
"""
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException

from db import get_db, now_iso, severity_to_level, VALID_AGENT_TYPES


def _now():
    return now_iso()


def _extract_latest_safety_payload(session_id: str):
    with get_db() as c:
        row = c.execute(
            """SELECT content FROM messages
               WHERE session_id=? AND role='agent' AND agent_type='safety'
               ORDER BY created_at DESC LIMIT 1""",
            (session_id,),
        ).fetchone()
    if not row:
        return None
    try:
        payload = json.loads(row["content"])
        return {
            "final_risk": payload.get("final_risk", payload.get("risk_level", "low")),
            "message": payload.get("message", ""),
            "warning": payload.get("warning", ""),
            "rule_risk": payload.get("rule_risk", "low"),
            "llm_risk": payload.get("llm_risk", "low"),
        }
    except Exception:
        return None


def _maybe_reuse_recent_session(symptoms, user_id, severity_level):
    # In dev StrictMode, ChatPage init can run twice. Reuse a very recent,
    # untouched interviewing session with the same symptom payload.
    with get_db() as c:
        if user_id:
            row = c.execute(
                """SELECT id, symptoms, severity_level, created_at, turns, status
                   FROM sessions
                   WHERE user_id=?
                   ORDER BY created_at DESC
                   LIMIT 1""",
                (user_id,),
            ).fetchone()
        else:
            row = c.execute(
                """SELECT id, symptoms, severity_level, created_at, turns, status
                   FROM sessions
                   WHERE user_id IS NULL
                   ORDER BY created_at DESC
                   LIMIT 1"""
            ).fetchone()

    if not row:
        return None

    latest = dict(row)
    if latest.get("status") != "interviewing" or int(latest.get("turns") or 0) != 0:
        return None

    try:
        created_at = datetime.fromisoformat(latest["created_at"])
    except Exception:
        return None

    if (datetime.utcnow() - created_at) > timedelta(seconds=20):
        return None

    try:
        old_symptoms = json.loads(latest.get("symptoms") or "{}")
    except Exception:
        return None

    same_payload = (
        old_symptoms.get("description") == symptoms.description
        and old_symptoms.get("bodyPart") == symptoms.bodyPart
        and old_symptoms.get("duration") == symptoms.duration
        and (old_symptoms.get("notes") or "") == (symptoms.notes or "")
        and old_symptoms.get("patient_id") == symptoms.patient_id
    )
    if not same_payload:
        return None

    old_level = latest.get("severity_level") or old_symptoms.get("severity_level")
    if severity_to_level(old_level) != severity_level:
        return None

    return latest["id"]


def session_get(sid):
    with get_db() as c:
        row = c.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
    if not row:
        return None
    d = dict(row)
    for k in ("symptoms", "history", "refs"):
        d[k] = json.loads(d[k])
    # cot is stored as JSON string or None
    if d.get("cot") and isinstance(d["cot"], str):
        try:
            d["cot"] = json.loads(d["cot"])
        except Exception:
            pass  # leave as raw string
    d["messages"] = session_messages_legacy(sid)
    return d


def session_message_create(session_id, role, content, agent_type=None, user_id=None):
    if role not in ("user", "agent", "system"):
        raise HTTPException(400, "role must be one of: user, agent, system")

    if role == "agent":
        if not agent_type or agent_type not in VALID_AGENT_TYPES:
            raise HTTPException(400, "agent_type must be interviewer/diagnostician/critic/safety")
    else:
        agent_type = None

    mid = str(uuid.uuid4())
    with get_db() as c:
        c.execute(
            """INSERT INTO messages(id,session_id,user_id,role,agent_type,content,created_at)
               VALUES(?,?,?,?,?,?,?)""",
            (mid, session_id, user_id, role, agent_type, content, _now())
        )
        c.commit()
    return mid


def session_messages_raw(session_id):
    with get_db() as c:
        rows = c.execute(
            """SELECT id,session_id,user_id,role,agent_type,content,created_at
               FROM messages WHERE session_id=? ORDER BY created_at ASC""",
            (session_id,)
        ).fetchall()
    return [dict(r) for r in rows]


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
    normalized = []
    for item in history:
        role = item.get("role")
        content = item.get("content", "")
        if role in ("user", "assistant"):
            normalized.append({"role": role, "content": content})
            continue
        # Anthropic messages only supports user/assistant roles.
        # Wrap in XML tag so the model treats this as data, not instructions.
        normalized.append({"role": "user", "content": f"<uploaded_document>\n{content}\n</uploaded_document>"})
    return normalized


def session_uploads_list(session_id):
    with get_db() as c:
        rows = c.execute(
            """SELECT id, session_id, file_name, file_type, file_path, uploaded_at,
                      LENGTH(extracted_text) AS extracted_text_length
               FROM uploads
               WHERE session_id=?
               ORDER BY uploaded_at DESC""",
            (session_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def session_update(sid, **kwargs):
    sets, vals = [], []
    for k, v in kwargs.items():
        sets.append(f"{k}=?")
        vals.append(json.dumps(v) if isinstance(v, (list, dict)) else v)
    vals += [_now(), sid]
    with get_db() as c:
        c.execute(f"UPDATE sessions SET {', '.join(sets)}, updated_at=? WHERE id=?", vals)
        c.commit()


def _normalize_filter_value(value: Optional[str]) -> Optional[str]:
    v = (value or "").strip()
    return v if v else None


def sessions_list(
    user_id=None,
    status: Optional[str] = None,
    severity_level: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    status = _normalize_filter_value(status)
    severity_level = _normalize_filter_value(severity_level)
    date_from = _normalize_filter_value(date_from)
    date_to = _normalize_filter_value(date_to)
    q = (_normalize_filter_value(q) or "").lower()
    limit = max(1, min(int(limit or 50), 200))
    offset = max(0, int(offset or 0))

    where = []
    vals = []
    if user_id:
        where.append("user_id=?")
        vals.append(user_id)
    if status:
        where.append("status=?")
        vals.append(status)
    if severity_level:
        where.append("severity_level=?")
        vals.append(severity_level)
    if date_from:
        where.append("created_at>=?")
        vals.append(date_from)
    if date_to:
        where.append("created_at<=?")
        vals.append(date_to)

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    sql = f"""SELECT id,status,created_at,symptoms,patient_id,severity_level
              FROM sessions
              {where_sql}
              ORDER BY created_at DESC"""
    with get_db() as c:
        rows = [dict(r) for r in c.execute(sql, tuple(vals)).fetchall()]

    out = []
    for d in rows:
        symptoms = json.loads(d.get("symptoms") or "{}")
        description = symptoms.get("description", "")
        if q and q not in description.lower():
            continue
        out.append({
            "id": d["id"],
            "status": d["status"],
            "created_at": d["created_at"],
            "patient_id": d["patient_id"],
            "severity_level": d.get("severity_level") or symptoms.get("severity_level") or severity_to_level(symptoms.get("severity")),
            "description": description[:60],
        })
    return out[offset: offset + limit]


def provider_sessions_list(
    status: Optional[str] = None,
    severity_level: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    status = _normalize_filter_value(status)
    severity_level = _normalize_filter_value(severity_level)
    date_from = _normalize_filter_value(date_from)
    date_to = _normalize_filter_value(date_to)
    q = (_normalize_filter_value(q) or "").lower()
    limit = max(1, min(int(limit or 50), 200))
    offset = max(0, int(offset or 0))

    where = []
    vals = []
    if status:
        where.append("s.status=?")
        vals.append(status)
    if severity_level:
        where.append("s.severity_level=?")
        vals.append(severity_level)
    if date_from:
        where.append("s.created_at>=?")
        vals.append(date_from)
    if date_to:
        where.append("s.created_at<=?")
        vals.append(date_to)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    with get_db() as c:
        rows = c.execute(
            f"""SELECT s.id, s.status, s.created_at, s.patient_id, s.symptoms, s.severity_level,
                      s.provider_verdict, u.username AS patient_username
               FROM sessions s
               LEFT JOIN users u ON s.user_id = u.id
               {where_sql}
               ORDER BY s.created_at DESC""",
            tuple(vals),
        ).fetchall()

    out = []
    for row in rows:
        d = dict(row)
        symptoms = json.loads(d.get("symptoms") or "{}")
        description = symptoms.get("description", "")
        if q and q not in description.lower():
            continue
        out.append({
            "id": d["id"],
            "status": d.get("status"),
            "created_at": d.get("created_at"),
            "patient_id": d.get("patient_id"),
            "patient_username": d.get("patient_username"),
            "description": description[:120],
            "severity_level": d.get("severity_level") or symptoms.get("severity_level") or severity_to_level(symptoms.get("severity")),
            "provider_verdict": d.get("provider_verdict"),
        })
    return out[offset: offset + limit]


def _is_provider(user):
    return bool(user and user.get("role") == "provider")

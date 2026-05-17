import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user, require_user
from app.db import get_db
import services.session_service as _services
from schemas.api import MessageInput

router = APIRouter()


def _bind_services_db():
    _services.get_db = get_db


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


def session_update(sid, **kwargs):
    _bind_services_db()
    return _services.session_update(sid, **kwargs)


def sessions_list(*args, **kwargs):
    _bind_services_db()
    return _services.sessions_list(*args, **kwargs)


def _is_provider(user):
    return _services._is_provider(user)


@router.get("/api/session/{session_id}")
def get_session(session_id: str, user=Depends(get_current_user)):
    sess = session_get(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    if sess.get("user_id") and (not user or (not _is_provider(user) and sess["user_id"] != user["id"])):
        raise HTTPException(403, "Forbidden")
    return sess


@router.delete("/api/sessions/{session_id}", status_code=204)
def delete_session(session_id: str, user=Depends(get_current_user)):
    sess = session_get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    uid = user["id"] if user else None
    if not _is_provider(user) and sess.get("user_id") and sess["user_id"] != uid:
        raise HTTPException(status_code=403, detail="Forbidden")

    with get_db() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))
        conn.commit()


@router.get("/api/sessions")
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


@router.post("/api/sessions/{session_id}/messages")
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
        user_id=user["id"],
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


@router.get("/api/sessions/{session_id}/messages")
def get_session_messages(session_id: str, user=Depends(require_user)):
    sess = session_get(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    if sess.get("user_id") and (not _is_provider(user) and sess["user_id"] != user["id"]):
        raise HTTPException(403, "Forbidden")
    return session_messages_raw(session_id)



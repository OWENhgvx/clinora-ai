import re
from collections.abc import Callable
from typing import Any, Optional, Tuple
from fastapi import HTTPException

READY_FOR_DIAGNOSIS_MARKER = "[READY_FOR_DIAGNOSIS]"
INTERVIEWING_STATUS = "interviewing"
ANALYZING_STATUS = "analyzing"
FORCE_TRIGGER_APPENDIX = (
    "Thank you for sharing all of that. I now have enough information to proceed with a thorough analysis."
)

_QR_RE = re.compile(r"QUICK_REPLIES\s*:\s*(.+?)(?:\n|$)", re.IGNORECASE)


def extract_quick_replies(text: str) -> tuple[str, list[str]]:
    m = _QR_RE.search(text)
    if not m:
        return text.strip(), []
    chips = [c.strip() for c in m.group(1).split("|") if c.strip()]
    clean = _QR_RE.sub("", text).strip()
    return clean, chips


def process_interviewer_reply(reply: str, turns: int, max_turns: int = 12) -> tuple[str, list[str], bool]:
    ready = READY_FOR_DIAGNOSIS_MARKER in reply
    clean = reply.replace(READY_FOR_DIAGNOSIS_MARKER, "").strip()
    clean, quick_replies = extract_quick_replies(clean)

    force_trigger = turns >= max_turns
    if force_trigger and not ready:
        clean = clean + "\n\n" + FORCE_TRIGGER_APPENDIX

    return clean, quick_replies, (ready or force_trigger)


def status_from_trigger(trigger: bool) -> str:
    return ANALYZING_STATUS if trigger else INTERVIEWING_STATUS


def session_access_error(
    sess: Optional[dict[str, Any]],
    user: Optional[dict[str, Any]],
    *,
    required_status: Optional[str] = None,
) -> Optional[Tuple[int, str]]:
    if not sess:
        return 404, "Session not found"
    if required_status and sess.get("status") != required_status:
        return 400, f"Status: {sess.get('status')}"
    if sess.get("user_id") and (not user or sess.get("user_id") != user.get("id")):
        return 403, "Forbidden"
    return None


def raise_for_session_access(
    sess: Optional[dict[str, Any]],
    user: Optional[dict[str, Any]],
    *,
    required_status: Optional[str] = None,
) -> None:
    access_error = session_access_error(sess, user, required_status=required_status)
    if access_error:
        status_code, message = access_error
        raise HTTPException(status_code, message)


def user_id_or_none(user: Optional[dict[str, Any]]) -> Optional[str]:
    return user["id"] if user else None


def append_user_inputs_sync(
    *,
    session_id: str,
    history: list[dict[str, Any]],
    messages: list[dict[str, Any]],
    user_message: str,
    user_id: Optional[str],
    persist_message: Callable[..., Any],
) -> None:
    history.append({"role": "user", "content": user_message})
    messages.append({"role": "user", "text": user_message})
    persist_message(session_id, role="user", content=user_message, user_id=user_id)

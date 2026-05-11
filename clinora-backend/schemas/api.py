"""
schemas.py — request models and input validators for Clinora API.
"""
import re
from typing import Optional, Union

from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator


_INJECTION_PATTERNS = re.compile(
    r"(ignore\s+(previous|prior|all)\s+instructions?|"
    r"you\s+are\s+now|forget\s+(everything|all)|"
    r"act\s+as\s+if|pretend\s+(you\s+are|to\s+be)|"
    r"disregard\s+(your|all)|system\s+prompt|"
    r"jailbreak|do\s+anything\s+now|dan\s+mode|"
    r"<\s*script|javascript:|on\w+\s*=)",
    re.IGNORECASE,
)


def _check_injection(text: str, field: str = "input") -> None:
    """Raise 400 if text contains prompt-injection or XSS patterns."""
    if _INJECTION_PATTERNS.search(text):
        raise HTTPException(400, f"Invalid content detected in {field}.")


_ALLOWED_ROLES = {"patient", "provider"}
_ALLOWED_GENDERS = {"male", "female", "other", "prefer not to say", ""}
_ALLOWED_BLOOD_TYPES = {"a+", "a-", "b+", "b-", "ab+", "ab-", "o+", "o-", "unknown", ""}
_ALLOWED_MSG_ROLES = {"user", "agent", "system"}
_ALLOWED_AGENT_TYPES = {"interviewer", "diagnostician", "critic", "safety", None}
_ALLOWED_EVAL_MODES = {"rag", "base", "both"}


class RegisterInput(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=6, max_length=128)
    full_name: str = Field(default="", max_length=100)
    role: str = "patient"

    @field_validator("username")
    @classmethod
    def val_username(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[A-Za-z0-9_\-]+$", v):
            raise ValueError("Username may only contain letters, digits, _ and -")
        return v

    @field_validator("email")
    @classmethod
    def val_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Invalid email address")
        return v

    @field_validator("role")
    @classmethod
    def val_role(cls, v: str) -> str:
        if v not in _ALLOWED_ROLES:
            raise ValueError(f"role must be one of: {', '.join(_ALLOWED_ROLES)}")
        return v

    @field_validator("full_name")
    @classmethod
    def val_full_name(cls, v: str) -> str:
        _check_injection(v, "full_name")
        return v.strip()


class SymptomInput(BaseModel):
    description: str = Field(min_length=2, max_length=2000)
    bodyPart: str = Field(default="General", max_length=100)
    duration: str = Field(default="1-3 days", max_length=50)
    severity: Union[int, str] = "moderate"
    notes: str = Field(default="", max_length=500)
    patient_id: Optional[str] = None
    pre_context: list[str] = Field(default=[], max_length=20)
    consent_to_provider_review: bool = False

    @field_validator("description")
    @classmethod
    def val_description(cls, v: str) -> str:
        v = v.strip()
        _check_injection(v, "description")
        return v

    @field_validator("severity")
    @classmethod
    def val_severity(cls, v: Union[int, str]) -> Union[int, str]:
        if isinstance(v, int) and not (1 <= v <= 10):
            raise ValueError("severity must be between 1 and 10")
        return v

    @field_validator("notes")
    @classmethod
    def val_notes(cls, v: str) -> str:
        _check_injection(v, "notes")
        return v.strip()


class ChatMessage(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    user_message: str = Field(min_length=1, max_length=2000)
    attachments: list[str] = Field(default=[], max_length=10)

    @field_validator("user_message")
    @classmethod
    def val_user_message(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        _check_injection(v, "user_message")
        return v


class DiagnoseRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)


class MessageInput(BaseModel):
    role: str
    content: str = Field(min_length=1, max_length=5000)
    agent_type: Optional[str] = None

    @field_validator("role")
    @classmethod
    def val_role(cls, v: str) -> str:
        if v not in _ALLOWED_MSG_ROLES:
            raise ValueError(f"role must be one of: {', '.join(_ALLOWED_MSG_ROLES)}")
        return v

    @field_validator("agent_type")
    @classmethod
    def val_agent_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _ALLOWED_AGENT_TYPES:
            raise ValueError("agent_type must be interviewer/diagnostician/critic/safety")
        return v

    @field_validator("content")
    @classmethod
    def val_content(cls, v: str) -> str:
        _check_injection(v, "content")
        return v


class PatientInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    dob: str = Field(default="", max_length=20)
    gender: str = Field(default="", max_length=30)
    blood_type: str = Field(default="", max_length=10)
    allergies: str = Field(default="", max_length=500)
    medications: str = Field(default="", max_length=500)
    conditions: str = Field(default="", max_length=500)
    notes: str = Field(default="", max_length=1000)

    @field_validator("name")
    @classmethod
    def val_name(cls, v: str) -> str:
        v = v.strip()
        _check_injection(v, "name")
        return v

    @field_validator("gender")
    @classmethod
    def val_gender(cls, v: str) -> str:
        if v.lower() not in _ALLOWED_GENDERS:
            raise ValueError(f"gender must be one of: {', '.join(g for g in _ALLOWED_GENDERS if g)}")
        return v

    @field_validator("blood_type")
    @classmethod
    def val_blood_type(cls, v: str) -> str:
        if v.lower() not in _ALLOWED_BLOOD_TYPES:
            raise ValueError(f"Invalid blood type: {v}")
        return v

    @field_validator("allergies", "medications", "conditions", "notes")
    @classmethod
    def val_free_text(cls, v: str) -> str:
        _check_injection(v, "patient field")
        return v.strip()


class EvalRequest(BaseModel):
    question_id: str = Field(min_length=1, max_length=50)
    mode: str = "both"

    @field_validator("mode")
    @classmethod
    def val_mode(cls, v: str) -> str:
        if v not in _ALLOWED_EVAL_MODES:
            raise ValueError(f"mode must be one of: {', '.join(_ALLOWED_EVAL_MODES)}")
        return v


class IngestRequest(BaseModel):
    terms: list[str] = Field(default=[], max_length=50)
    per_term: int = Field(default=15, ge=1, le=100)

    @field_validator("terms")
    @classmethod
    def val_terms(cls, v: list[str]) -> list[str]:
        cleaned = []
        for t in v:
            t = t.strip()
            if len(t) > 200:
                raise ValueError("Each search term must be under 200 characters")
            _check_injection(t, "terms")
            cleaned.append(t)
        return cleaned


class VerdictInput(BaseModel):
    verdict: str  # 'approved' | 'flagged'
    note: str = ""

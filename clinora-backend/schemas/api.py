"""
schemas.py — request models and input validators for Clinora API.
"""
import re
from datetime import date
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator


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
_ALLOWED_VERIFICATION_STATUSES = {"active", "pending_review"}
_ALLOWED_MSG_ROLES = {"user", "agent", "system"}
_ALLOWED_AGENT_TYPES = {"interviewer", "diagnostician", None}
_ALLOWED_EVAL_MODES = {"rag", "base", "both"}


class RegisterInput(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=6, max_length=128)
    full_name: str = Field(default="", max_length=100)
    role: str = "patient"
    birth_date: str = Field(min_length=10, max_length=10)
    sex: str = Field(min_length=1, max_length=30)
    height_cm: Optional[float] = Field(default=None, gt=0, le=260)
    weight_kg: Optional[float] = Field(default=None, gt=0, le=650)
    allergies: str = Field(default="", max_length=500)
    chronic_conditions: list[str] = Field(default_factory=list, max_length=20)
    phone: str = Field(default="", max_length=40)
    data_authorization_accepted: bool = False
    license_number: str = Field(default="", max_length=80)
    hospital: str = Field(default="", max_length=160)
    department: str = Field(default="", max_length=120)
    specialty: str = Field(default="", max_length=120)
    years_experience: Optional[int] = Field(default=None, ge=0, le=80)
    title: str = Field(default="", max_length=120)
    qualification_proof: str = Field(default="", max_length=500)

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

    @field_validator("sex")
    @classmethod
    def val_sex(cls, v: str) -> str:
        v = v.strip()
        if v.lower() not in _ALLOWED_GENDERS - {""}:
            raise ValueError(f"sex must be one of: {', '.join(g for g in _ALLOWED_GENDERS if g)}")
        return v

    @field_validator(
        "allergies",
        "license_number",
        "hospital",
        "department",
        "specialty",
        "title",
        "qualification_proof",
    )
    @classmethod
    def val_register_text(cls, v: str) -> str:
        _check_injection(v, "registration field")
        return v.strip()

    @field_validator("birth_date")
    @classmethod
    def val_birth_date(cls, v: str) -> str:
        v = v.strip()
        _check_injection(v, "birth_date")
        try:
            parsed = date.fromisoformat(v)
        except ValueError as exc:
            raise ValueError("birth_date must be YYYY-MM-DD") from exc
        if parsed > date.today():
            raise ValueError("birth_date cannot be in the future")
        return v

    @field_validator("phone")
    @classmethod
    def val_phone(cls, v: str) -> str:
        v = v.strip()
        if v and not re.match(r"^[0-9+()\-\s]{6,40}$", v):
            raise ValueError("Invalid phone number")
        return v

    @field_validator("chronic_conditions")
    @classmethod
    def val_chronic_conditions(cls, v: list[str]) -> list[str]:
        cleaned = []
        for item in v:
            item = str(item).strip()
            if not item:
                continue
            _check_injection(item, "chronic_conditions")
            if len(item) > 80:
                raise ValueError("Chronic condition is too long")
            cleaned.append(item)
        return cleaned

    @model_validator(mode="after")
    def val_registration_requirements(self):
        if self.role == "patient":
            if self.height_cm is None:
                raise ValueError("height_cm is required for patients")
            if self.weight_kg is None:
                raise ValueError("weight_kg is required for patients")
            if not self.chronic_conditions:
                raise ValueError("chronic_conditions is required for patients")
            if not self.data_authorization_accepted:
                raise ValueError("Patient data authorization must be accepted")
        if self.role == "provider":
            missing = [
                field
                for field in (
                    "full_name",
                    "license_number",
                    "hospital",
                    "department",
                    "specialty",
                    "title",
                    "qualification_proof",
                )
                if not getattr(self, field)
            ]
            if self.years_experience is None:
                missing.append("years_experience")
            if missing:
                raise ValueError(f"Missing provider credential fields: {', '.join(missing)}")
        return self

    @property
    def bmi(self) -> Optional[float]:
        if self.height_cm is None or self.weight_kg is None:
            return None
        meters = self.height_cm / 100
        return round(self.weight_kg / (meters * meters), 1)

    @property
    def age(self) -> int:
        born = date.fromisoformat(self.birth_date)
        today = date.today()
        years = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        return max(0, years)

    @property
    def verification_status(self) -> str:
        status = "pending_review" if self.role == "provider" else "active"
        if status not in _ALLOWED_VERIFICATION_STATUSES:
            return "active"
        return status

    def profile_data(self) -> dict:
        return {
            "birth_date": self.birth_date,
            "age": self.age,
            "sex": self.sex,
            "height_cm": self.height_cm,
            "weight_kg": self.weight_kg,
            "bmi": self.bmi,
            "allergies": self.allergies if self.role == "patient" else None,
            "chronic_conditions": (
                ", ".join(self.chronic_conditions) if self.role == "patient" else None
            ),
            "phone": self.phone,
            "data_authorization_accepted": 1 if self.data_authorization_accepted else 0,
            "license_number": self.license_number,
            "hospital": self.hospital,
            "department": self.department,
            "specialty": self.specialty,
            "years_experience": self.years_experience,
            "title": self.title,
            "qualification_proof": self.qualification_proof,
            "verification_status": self.verification_status,
        }


class SymptomInput(BaseModel):
    description: str = Field(min_length=2, max_length=2000)
    bodyPart: str = Field(default="General", max_length=100)
    duration: str = Field(default="1-3 days", max_length=50)
    notes: str = Field(default="", max_length=500)
    patient_id: Optional[str] = None
    consent_to_provider_review: bool = False

    @field_validator("description")
    @classmethod
    def val_description(cls, v: str) -> str:
        v = v.strip()
        _check_injection(v, "description")
        return v

    @field_validator("notes")
    @classmethod
    def val_notes(cls, v: str) -> str:
        _check_injection(v, "notes")
        return v.strip()


class ChatMessage(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    user_message: str = Field(min_length=1, max_length=2000)

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
            raise ValueError("agent_type must be interviewer/diagnostician")
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


class VerdictInput(BaseModel):
    verdict: str  # 'approved' | 'flagged'
    note: str = ""

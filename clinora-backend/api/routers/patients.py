import json

from fastapi import APIRouter, Depends, HTTPException

from app.auth import patient_create, patient_delete, patient_get, patient_update, patients_list, require_user
from app.db import get_db
from schemas.api import PatientInput

router = APIRouter()


@router.get("/api/patients")
def list_patients(user=Depends(require_user)):
    """List patients belonging to the current user."""
    return patients_list(user["id"])


@router.post("/api/patients")
def create_patient(body: PatientInput, user=Depends(require_user)):
    """Create a new patient record."""
    return patient_create(user["id"], body.model_dump())


@router.get("/api/patients/{patient_id}")
def get_patient(patient_id: str, user=Depends(require_user)):
    """Fetch a patient record by ID."""
    patient = patient_get(patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")
    if patient["user_id"] != user["id"]:
        raise HTTPException(403, "Forbidden")
    with get_db() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM sessions WHERE patient_id=?",
            (patient_id,),
        ).fetchone()[0]
    patient["session_count"] = count
    return patient


@router.put("/api/patients/{patient_id}")
def update_patient(patient_id: str, body: PatientInput, user=Depends(require_user)):
    """Update a patient record."""
    patient = patient_get(patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")
    if patient["user_id"] != user["id"]:
        raise HTTPException(403, "Forbidden")
    patient_update(patient_id, body.model_dump())
    return patient_get(patient_id)


@router.delete("/api/patients/{patient_id}")
def delete_patient(patient_id: str, user=Depends(require_user)):
    """Delete a patient record."""
    patient = patient_get(patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")
    if patient["user_id"] != user["id"]:
        raise HTTPException(403, "Forbidden")
    patient_delete(patient_id)
    return {"deleted": True}


@router.get("/api/patients/{patient_id}/sessions")
def patient_sessions(patient_id: str, user=Depends(require_user)):
    """List all sessions for a given patient."""
    patient = patient_get(patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")
    if patient["user_id"] != user["id"]:
        raise HTTPException(403, "Forbidden")
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id,status,created_at,symptoms FROM sessions WHERE patient_id=? ORDER BY created_at DESC",
            (patient_id,),
        ).fetchall()
    return [
        {
            "id": item["id"],
            "status": item["status"],
            "created_at": item["created_at"],
            "description": json.loads(item["symptoms"]).get("description", "")[:60],
        }
        for item in map(dict, rows)
    ]

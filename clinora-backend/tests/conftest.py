import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")


def registration_payload(username, email, role="patient", **overrides):
    payload = {
        "username": username,
        "email": email,
        "password": "securepass123",
        "full_name": username,
        "role": role,
        "birth_date": "1990-01-01",
        "sex": "female",
        "height_cm": 170,
        "weight_kg": 65,
        "allergies": "None",
        "chronic_conditions": ["None"],
        "phone": "+61400000000",
        "data_authorization_accepted": role == "patient",
    }
    if role == "provider":
        for key in ("height_cm", "weight_kg", "allergies", "chronic_conditions"):
            payload.pop(key, None)
        payload.update(
            {
                "full_name": f"Dr. {username}",
                "license_number": f"LIC-{username}",
                "hospital": "Clinora General Hospital",
                "department": "Internal Medicine",
                "specialty": "Cardiology",
                "years_experience": 8,
                "title": "Attending Physician",
                "qualification_proof": "provider-credential.pdf",
            }
        )
    payload.update(overrides)
    return payload


@pytest.fixture()
def client(tmp_path, monkeypatch):
    os.environ.setdefault("SECRET_KEY", "test-secret-key")

    import app.db as db

    test_db = tmp_path / "test_clinora.db"
    monkeypatch.setattr(db, "DB_FILE", Path(test_db))
    db.init_db()

    import main

    upload_root = tmp_path / "uploads"
    monkeypatch.setattr(main, "UPLOAD_ROOT", upload_root, raising=False)
    upload_root.mkdir(parents=True, exist_ok=True)

    with TestClient(main.app) as c:
        yield c

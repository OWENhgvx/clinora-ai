from io import BytesIO
from pathlib import Path


def _register_and_token(client, username, email, role="patient"):
    resp = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "securepass123",
            "full_name": username,
            "role": role,
        },
    )
    assert resp.status_code == 200
    return resp.json()["token"]


def _start_session(client, token, monkeypatch):
    import main

    monkeypatch.setattr(main, "call_interviewer", lambda history: "Thanks. More detail please?")
    monkeypatch.setattr(
        main,
        "classify_safety",
        lambda text: {
            "final_risk": "low",
            "rule_risk": "low",
            "llm_risk": "low",
            "message": "",
            "warning": "",
        },
    )
    resp = client.post(
        "/api/session/start",
        json={
            "description": "Headache for one day",
            "bodyPart": "Head",
            "duration": "1 day",
            "severity": "mild",
            "notes": "",
            "pre_context": [],
            "consent_to_provider_review": False,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    return resp.json()["session_id"]


def test_delete_session_not_found(client):
    token = _register_and_token(client, "delete_missing", "delete_missing@example.com")
    resp = client.delete(
        "/api/sessions/non-existent",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_delete_session_forbidden_for_other_patient(client, monkeypatch):
    owner_token = _register_and_token(client, "delete_owner", "delete_owner@example.com")
    intruder_token = _register_and_token(client, "delete_intruder", "delete_intruder@example.com")
    session_id = _start_session(client, owner_token, monkeypatch)

    resp = client.delete(
        f"/api/sessions/{session_id}",
        headers={"Authorization": f"Bearer {intruder_token}"},
    )
    assert resp.status_code == 403


def test_delete_session_owner_removes_session_and_upload_file(client, monkeypatch):
    token = _register_and_token(client, "delete_owner_file", "delete_owner_file@example.com")
    session_id = _start_session(client, token, monkeypatch)

    upload = client.post(
        f"/api/sessions/{session_id}/upload",
        files={"file": ("note.txt", BytesIO(b"delete me"), "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert upload.status_code == 200
    stored_path = Path(upload.json()["upload"]["file_path"])
    assert stored_path.exists()

    delete = client.delete(
        f"/api/sessions/{session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete.status_code == 204
    assert not stored_path.exists()

    get_after_delete = client.get(
        f"/api/session/{session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_after_delete.status_code == 404


def test_delete_session_provider_can_delete_patient_session(client, monkeypatch):
    patient_token = _register_and_token(client, "delete_patient", "delete_patient@example.com")
    provider_token = _register_and_token(
        client, "delete_provider", "delete_provider@example.com", role="provider"
    )
    session_id = _start_session(client, patient_token, monkeypatch)

    resp = client.delete(
        f"/api/sessions/{session_id}",
        headers={"Authorization": f"Bearer {provider_token}"},
    )
    assert resp.status_code == 204

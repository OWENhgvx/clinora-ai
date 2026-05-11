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
            "description": "Abdominal pain for one day",
            "bodyPart": "Abdomen",
            "duration": "1 day",
            "severity": "mild",
            "notes": "",
            "pre_context": [],
            "consent_to_provider_review": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    return resp.json()["session_id"]


def test_patient_crud_and_ownership(client):
    token_owner = _register_and_token(client, "patient_owner", "patient_owner@example.com")
    token_other = _register_and_token(client, "patient_other", "patient_other@example.com")

    create = client.post(
        "/api/patients",
        json={
            "name": "Alice Patient",
            "dob": "1990-01-01",
            "gender": "female",
            "blood_type": "o+",
            "allergies": "None",
            "medications": "None",
            "conditions": "None",
            "notes": "Initial note",
        },
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert create.status_code == 200
    patient_id = create.json()["id"]

    list_resp = client.get("/api/patients", headers={"Authorization": f"Bearer {token_owner}"})
    assert list_resp.status_code == 200
    assert any(p["id"] == patient_id for p in list_resp.json())

    get_resp = client.get(
        f"/api/patients/{patient_id}",
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Alice Patient"

    forbidden = client.get(
        f"/api/patients/{patient_id}",
        headers={"Authorization": f"Bearer {token_other}"},
    )
    assert forbidden.status_code == 403

    update = client.put(
        f"/api/patients/{patient_id}",
        json={
            "name": "Alice Updated",
            "dob": "1990-01-01",
            "gender": "female",
            "blood_type": "o+",
            "allergies": "None",
            "medications": "None",
            "conditions": "None",
            "notes": "Updated note",
        },
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert update.status_code == 200
    assert update.json()["name"] == "Alice Updated"

    delete = client.delete(
        f"/api/patients/{patient_id}",
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert delete.status_code == 200
    assert delete.json()["deleted"] is True

    missing = client.get(
        f"/api/patients/{patient_id}",
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert missing.status_code == 404


def test_patients_requires_auth(client):
    resp = client.get("/api/patients")
    assert resp.status_code == 401


def test_patient_sessions_route_lists_owned_patient_sessions(client, monkeypatch):
    import main

    token = _register_and_token(client, "patient_sessions_user", "patient_sessions@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/api/patients",
        json={
            "name": "Session Patient",
            "dob": "1990-01-01",
            "gender": "female",
            "blood_type": "o+",
            "allergies": "",
            "medications": "",
            "conditions": "",
            "notes": "",
        },
        headers=headers,
    )
    assert created.status_code == 200
    patient_id = created.json()["id"]

    monkeypatch.setattr(main, "call_interviewer", lambda history: "Initial reply")
    monkeypatch.setattr(
        main,
        "classify_safety",
        lambda text: {
            "final_risk": "low",
            "rule_risk": "low",
            "llm_risk": "low",
            "message": "No urgent red flags.",
            "warning": "",
        },
    )

    start = client.post(
        "/api/session/start",
        json={
            "description": "Follow up cough",
            "bodyPart": "Chest",
            "duration": "2 days",
            "severity": "mild",
            "notes": "",
            "patient_id": patient_id,
            "pre_context": [],
            "consent_to_provider_review": False,
        },
        headers=headers,
    )
    assert start.status_code == 200

    listed = client.get(f"/api/patients/{patient_id}/sessions", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["description"] == "Follow up cough"


def test_patient_sessions_route_rejects_missing_and_forbidden_patient(client):
    owner_token = _register_and_token(client, "patient_sessions_owner", "sessions_owner@example.com")
    other_token = _register_and_token(client, "patient_sessions_other", "sessions_other@example.com")

    missing = client.get(
        "/api/patients/missing-patient/sessions",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert missing.status_code == 404

    created = client.post(
        "/api/patients",
        json={
            "name": "Owner Patient",
            "dob": "",
            "gender": "",
            "blood_type": "",
            "allergies": "",
            "medications": "",
            "conditions": "",
            "notes": "",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert created.status_code == 200

    forbidden = client.get(
        f"/api/patients/{created.json()['id']}/sessions",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert forbidden.status_code == 403


def test_provider_session_verdict_authorization_and_success(client, monkeypatch):
    patient_token = _register_and_token(client, "verdict_patient", "verdict_patient@example.com")
    provider_token = _register_and_token(
        client, "verdict_provider", "verdict_provider@example.com", role="provider"
    )
    session_id = _start_session(client, patient_token, monkeypatch)

    patient_attempt = client.patch(
        f"/api/sessions/{session_id}/verdict",
        json={"verdict": "approved", "note": "Looks fine"},
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert patient_attempt.status_code == 403

    invalid = client.patch(
        f"/api/sessions/{session_id}/verdict",
        json={"verdict": "unknown", "note": ""},
        headers={"Authorization": f"Bearer {provider_token}"},
    )
    assert invalid.status_code == 400

    success = client.patch(
        f"/api/sessions/{session_id}/verdict",
        json={"verdict": "flagged", "note": "Needs clinician review"},
        headers={"Authorization": f"Bearer {provider_token}"},
    )
    assert success.status_code == 200
    assert success.json()["verdict"] == "flagged"
    assert success.json()["note"] == "Needs clinician review"

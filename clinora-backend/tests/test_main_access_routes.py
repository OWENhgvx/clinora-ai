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

    monkeypatch.setattr(
        main,
        "call_interviewer",
        lambda history: "Thanks. More detail please?",
    )
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
    start = client.post(
        "/api/session/start",
        json={
            "description": "Headache for two days",
            "bodyPart": "Head",
            "duration": "2 days",
            "severity": "mild",
            "notes": "",
            "pre_context": [],
            "consent_to_provider_review": False,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert start.status_code == 200
    return start.json()["session_id"]


def test_get_session_owner_ok_intruder_403(client, monkeypatch):
    token_owner = _register_and_token(
        client, "access_owner", "access_owner@example.com", "patient"
    )
    token_intruder = _register_and_token(
        client, "access_intruder", "access_intruder@example.com", "patient"
    )
    session_id = _start_session(client, token_owner, monkeypatch)

    r403 = client.get(
        f"/api/session/{session_id}",
        headers={"Authorization": f"Bearer {token_intruder}"},
    )
    assert r403.status_code == 403
    assert "forbidden" in r403.json()["detail"].lower()

    r200 = client.get(
        f"/api/session/{session_id}",
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert r200.status_code == 200
    assert r200.json()["id"] == session_id


def test_get_session_unauthenticated_403_when_session_bound_to_user(client, monkeypatch):
    token = _register_and_token(client, "access_u1", "access_u1@example.com")
    session_id = _start_session(client, token, monkeypatch)
    r = client.get(f"/api/session/{session_id}")
    assert r.status_code == 403


def test_get_session_as_provider_can_read_patient_session(client, monkeypatch):
    token_patient = _register_and_token(
        client, "access_pt", "access_pt@example.com", "patient"
    )
    token_provider = _register_and_token(
        client, "access_pr", "access_pr@example.com", "provider"
    )
    session_id = _start_session(client, token_patient, monkeypatch)
    r = client.get(
        f"/api/session/{session_id}",
        headers={"Authorization": f"Bearer {token_provider}"},
    )
    assert r.status_code == 200
    assert r.json()["id"] == session_id


def test_get_session_messages_owner_ok_intruder_403(client, monkeypatch):
    token_owner = _register_and_token(
        client, "msg_owner2", "msg_owner2@example.com", "patient"
    )
    token_intruder = _register_and_token(
        client, "msg_b2", "msg_b2@example.com", "patient"
    )
    session_id = _start_session(client, token_owner, monkeypatch)

    r403 = client.get(
        f"/api/sessions/{session_id}/messages",
        headers={"Authorization": f"Bearer {token_intruder}"},
    )
    assert r403.status_code == 403

    r200 = client.get(
        f"/api/sessions/{session_id}/messages",
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert r200.status_code == 200
    assert isinstance(r200.json(), list)


def test_list_sessions_requires_auth_and_returns_user_sessions(client, monkeypatch):
    token = _register_and_token(client, "list_sessions_user", "list_sessions@example.com")
    session_id = _start_session(client, token, monkeypatch)

    unauth = client.get("/api/sessions")
    assert unauth.status_code == 401

    resp = client.get(
        "/api/sessions?status=interviewing&q=headache&limit=5&offset=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert any(item["id"] == session_id for item in resp.json())


def test_provider_sessions_route_requires_provider(client, monkeypatch):
    patient_token = _register_and_token(client, "provider_list_patient", "provider_list_patient@example.com")
    provider_token = _register_and_token(
        client, "provider_list_provider", "provider_list_provider@example.com", "provider"
    )
    session_id = _start_session(client, patient_token, monkeypatch)

    forbidden = client.get(
        "/api/provider/sessions",
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert forbidden.status_code == 403

    ok = client.get(
        "/api/provider/sessions?status=interviewing&q=headache",
        headers={"Authorization": f"Bearer {provider_token}"},
    )
    assert ok.status_code == 200
    assert any(item["id"] == session_id for item in ok.json())


def test_list_sessions_provider_branch(client, monkeypatch):
    patient_token = _register_and_token(client, "all_sessions_patient", "all_sessions_patient@example.com")
    provider_token = _register_and_token(
        client, "all_sessions_provider", "all_sessions_provider@example.com", "provider"
    )
    session_id = _start_session(client, patient_token, monkeypatch)

    resp = client.get(
        "/api/sessions?status=interviewing&q=headache",
        headers={"Authorization": f"Bearer {provider_token}"},
    )
    assert resp.status_code == 200
    assert any(item["id"] == session_id for item in resp.json())

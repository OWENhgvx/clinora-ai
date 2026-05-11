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
        lambda history: "Thanks for sharing. Any fever or nausea?",
    )
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

    payload = {
        "description": "I have persistent headaches for three days.",
        "bodyPart": "Head",
        "duration": "3 days",
        "severity": "moderate",
        "notes": "Worse at night",
        "pre_context": [],
        "consent_to_provider_review": False,
    }
    start = client.post(
        "/api/session/start",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert start.status_code == 200
    return start.json()["session_id"]


def test_session_chat_success(client, monkeypatch):
    import main

    token = _register_and_token(client, "chat_user_1", "chat_user_1@example.com")
    session_id = _start_session(client, token, monkeypatch)

    monkeypatch.setattr(
        main,
        "call_interviewer",
        lambda history: "Thanks, that helps. Is pain worse in the morning?",
    )
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
    monkeypatch.setattr(
        main,
        "call_agent_commentary",
        lambda user_message, interviewer_reply, symptoms_context: {
            "safety_to_interviewer": "Monitor symptom progression.",
            "interviewer_to_safety": "No immediate risk signs.",
        },
    )

    chat = client.post(
        "/api/session/chat",
        json={
            "session_id": session_id,
            "user_message": "The pain gets worse after waking up.",
            "attachments": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert chat.status_code == 200
    body = chat.json()
    assert body["status"] in ("interviewing", "analyzing")
    assert "reply" in body and body["reply"]
    assert "safety" in body and body["safety"]["final_risk"] == "low"


def test_session_chat_invalid_session_id_fails(client):
    token = _register_and_token(client, "chat_user_2", "chat_user_2@example.com")
    chat = client.post(
        "/api/session/chat",
        json={
            "session_id": "non-existent-session-id",
            "user_message": "hello",
            "attachments": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert chat.status_code == 404
    assert "not found" in chat.json()["detail"].lower()


def test_session_chat_unauthorized_access_fails(client, monkeypatch):
    owner_token = _register_and_token(client, "chat_owner", "chat_owner@example.com")
    intruder_token = _register_and_token(client, "chat_intruder", "chat_intruder@example.com")
    session_id = _start_session(client, owner_token, monkeypatch)

    chat = client.post(
        "/api/session/chat",
        json={
            "session_id": session_id,
            "user_message": "I should not access this session.",
            "attachments": [],
        },
        headers={"Authorization": f"Bearer {intruder_token}"},
    )
    assert chat.status_code == 403
    assert "forbidden" in chat.json()["detail"].lower()


def test_session_chat_rejects_non_interviewing_status(client, monkeypatch):
    import main

    token = _register_and_token(client, "chat_status_user", "chat_status_user@example.com")
    session_id = _start_session(client, token, monkeypatch)
    main.session_update(session_id, status="done")

    chat = client.post(
        "/api/session/chat",
        json={
            "session_id": session_id,
            "user_message": "Can I keep chatting?",
            "attachments": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert chat.status_code == 400
    assert "status" in chat.json()["detail"].lower()


def test_session_chat_force_triggers_at_turn_limit_with_attachments(client, monkeypatch):
    import main

    token = _register_and_token(client, "chat_limit_user", "chat_limit_user@example.com")
    session_id = _start_session(client, token, monkeypatch)
    main.session_update(session_id, turns=11)

    monkeypatch.setattr(
        main,
        "call_interviewer",
        lambda history: "One last follow-up without ready marker.",
    )
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

    chat = client.post(
        "/api/session/chat",
        json={
            "session_id": session_id,
            "user_message": "Here is the final detail.",
            "attachments": ["uploaded lab text", "   "],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert chat.status_code == 200
    body = chat.json()
    assert body["status"] == "analyzing"
    assert body["trigger_diagnose"] is True
    assert "enough information" in body["reply"]

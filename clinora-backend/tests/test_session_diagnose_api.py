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


def _start_session_ready_for_diagnose(client, token, monkeypatch):
    import main

    monkeypatch.setattr(
        main,
        "call_interviewer",
        lambda history: "Thanks for sharing. [READY_FOR_DIAGNOSIS]",
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
        "description": "Persistent headache with nausea.",
        "bodyPart": "Head",
        "duration": "2 days",
        "severity": "moderate",
        "notes": "No known chronic conditions",
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


def test_session_diagnose_success(client, monkeypatch):
    import main

    token = _register_and_token(client, "diag_user_1", "diag_user_1@example.com")
    session_id = _start_session_ready_for_diagnose(client, token, monkeypatch)

    monkeypatch.setattr(main, "rewrite_image_findings_for_rag", lambda analyses: "")
    monkeypatch.setattr(
        main,
        "call_diagnostician_cot",
        lambda case_text, rag_query: (
            "Likely migraine; consider tension headache.",
            "CoT diagnostician",
            [{"title": "Ref A", "pmid": "12345"}],
        ),
    )
    monkeypatch.setattr(
        main,
        "call_critic_cot",
        lambda case_text, diagnosis: ("No immediate red flags; monitor progression.", "CoT critic"),
    )
    monkeypatch.setattr(
        main,
        "call_diagnostic_roundtable",
        lambda case_text, diagnosis, review: [
            {"from_agent": "diagnostician", "to_agent": "critic", "text": "Differential discussed."}
        ],
    )

    resp = client.post(
        "/api/session/diagnose",
        json={"session_id": session_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "done"
    assert "Likely migraine" in body["diagnosis"]
    assert isinstance(body["refs"], list)
    assert isinstance(body["agent_logs"], list)


def test_session_diagnose_fallback_when_cot_fails(client, monkeypatch):
    import main

    token = _register_and_token(client, "diag_user_2", "diag_user_2@example.com")
    session_id = _start_session_ready_for_diagnose(client, token, monkeypatch)

    monkeypatch.setattr(main, "rewrite_image_findings_for_rag", lambda analyses: "")

    def raise_cot_error(case_text, rag_query):
        raise RuntimeError("cot model unavailable")

    monkeypatch.setattr(main, "call_diagnostician_cot", raise_cot_error)
    monkeypatch.setattr(
        main,
        "call_diagnostician",
        lambda case_text, rag_query: ("Fallback diagnosis output", []),
    )
    monkeypatch.setattr(
        main,
        "call_critic",
        lambda case_text, diagnosis: "Fallback critic review",
    )
    monkeypatch.setattr(main, "call_diagnostic_roundtable", lambda case_text, diagnosis, review: [])

    resp = client.post(
        "/api/session/diagnose",
        json={"session_id": session_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "done"
    assert body["diagnosis"] == "Fallback diagnosis output"
    assert body["review"] == "Fallback critic review"
    assert body["cot"] is None


def test_session_diagnose_invalid_session_fails(client):
    token = _register_and_token(client, "diag_user_3", "diag_user_3@example.com")
    resp = client.post(
        "/api/session/diagnose",
        json={"session_id": "non-existent-session-id"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()

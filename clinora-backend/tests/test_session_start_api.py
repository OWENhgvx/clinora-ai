def test_session_start_success(client, monkeypatch):
    import main

    monkeypatch.setattr(
        main,
        "call_interviewer",
        lambda history: "Thanks for sharing. Can you describe when this started?",
    )
    monkeypatch.setattr(
        main,
        "classify_safety",
        lambda text: {
            "final_risk": "low",
            "rule_risk": "low",
            "llm_risk": "low",
            "message": "No urgent red flags detected.",
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
    resp = client.post("/api/session/start", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"]
    assert body["status"] == "interviewing"
    assert "reply" in body and body["reply"]
    assert body["safety"]["final_risk"] == "low"


def test_session_start_missing_description_fails(client):
    payload = {
        "bodyPart": "Head",
        "duration": "3 days",
        "severity": "moderate",
        "notes": "Worse at night",
    }
    resp = client.post("/api/session/start", json=payload)
    assert resp.status_code == 422
    assert "description" in resp.json()["detail"].lower()


def test_session_start_reuses_recent_untouched_session(client, monkeypatch):
    import main

    monkeypatch.setattr(
        main,
        "call_interviewer",
        lambda history: "Initial interviewer reply.",
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
        "description": "I have mild nausea.",
        "bodyPart": "Abdomen",
        "duration": "1 day",
        "severity": "mild",
        "notes": "",
        "pre_context": [],
        "consent_to_provider_review": False,
    }

    first = client.post("/api/session/start", json=payload)
    assert first.status_code == 200

    second = client.post("/api/session/start", json=payload)
    assert second.status_code == 200
    assert second.json()["session_id"] == first.json()["session_id"]
    assert second.json()["reply"] == "Initial interviewer reply."
    assert second.json()["safety"]["final_risk"] == "low"

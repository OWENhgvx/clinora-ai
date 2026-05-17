import api.routers.session_flow as session_flow
from conftest import registration_payload


def _register_and_token(client, username, email, role="patient"):
    resp = client.post(
        "/api/auth/register",
        json=registration_payload(username, email, role),
    )
    assert resp.status_code == 200
    return resp.json()["token"]


def _start_session_ready_for_diagnose(client, token, monkeypatch):
    monkeypatch.setattr(
        session_flow,
        "call_interviewer",
        lambda history: "Thanks for sharing. [READY_FOR_DIAGNOSIS]",
    )

    payload = {
        "description": "Persistent headache with nausea.",
        "bodyPart": "Head",
        "duration": "2 days",
        "notes": "No known chronic conditions",
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
    token = _register_and_token(client, "diag_user_1", "diag_user_1@example.com")
    session_id = _start_session_ready_for_diagnose(client, token, monkeypatch)

    monkeypatch.setattr(
        session_flow,
        "call_diagnostician_cot",
        lambda case_text, rag_query: (
            "Likely migraine; consider tension headache.",
            "CoT diagnostician",
            [{"title": "Ref A", "pmid": "12345"}],
        ),
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
    assert body["cot"] == {"diagnostician": "CoT diagnostician"}


def test_session_diagnose_fallback_when_cot_fails(client, monkeypatch):
    token = _register_and_token(client, "diag_user_2", "diag_user_2@example.com")
    session_id = _start_session_ready_for_diagnose(client, token, monkeypatch)

    def raise_cot_error(case_text, rag_query):
        raise RuntimeError("cot model unavailable")

    monkeypatch.setattr(session_flow, "call_diagnostician_cot", raise_cot_error)
    monkeypatch.setattr(
        session_flow,
        "call_diagnostician",
        lambda case_text, rag_query: ("Fallback diagnosis output", []),
    )

    resp = client.post(
        "/api/session/diagnose",
        json={"session_id": session_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "done"
    assert body["diagnosis"] == "Fallback diagnosis output"
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

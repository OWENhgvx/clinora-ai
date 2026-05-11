from io import BytesIO


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
        lambda history: "Thanks for sharing. Can you provide more detail?",
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
        "description": "Mild abdominal pain for one day.",
        "bodyPart": "Abdomen",
        "duration": "1 day",
        "severity": "mild",
        "notes": "No vomiting",
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


def test_store_and_get_session_messages_success(client, monkeypatch):
    token = _register_and_token(client, "msg_user_1", "msg_user_1@example.com")
    session_id = _start_session(client, token, monkeypatch)

    store = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"role": "user", "content": "Additional symptom details."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert store.status_code == 200
    assert store.json()["ok"] is True

    get_resp = client.get(
        f"/api/sessions/{session_id}/messages",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_resp.status_code == 200
    messages = get_resp.json()
    assert any(m["role"] == "user" and "Additional symptom details." in m["content"] for m in messages)


def test_store_session_message_forbidden_for_other_user(client, monkeypatch):
    owner_token = _register_and_token(client, "msg_owner", "msg_owner@example.com")
    intruder_token = _register_and_token(client, "msg_intruder", "msg_intruder@example.com")
    session_id = _start_session(client, owner_token, monkeypatch)

    store = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"role": "user", "content": "I should not write here."},
        headers={"Authorization": f"Bearer {intruder_token}"},
    )
    assert store.status_code == 403


def test_upload_and_list_session_uploads_success(client, monkeypatch):
    token = _register_and_token(client, "upload_user_1", "upload_user_1@example.com")
    session_id = _start_session(client, token, monkeypatch)

    files = {"file": ("note.txt", BytesIO(b"patient notes for testing"), "text/plain")}
    upload = client.post(
        f"/api/sessions/{session_id}/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert upload.status_code == 200
    body = upload.json()
    assert body["ok"] is True
    assert body["upload"]["file_type"] == "txt"

    get_uploads = client.get(
        f"/api/sessions/{session_id}/uploads",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_uploads.status_code == 200
    uploads = get_uploads.json()
    assert len(uploads) >= 1
    assert any(item["file_type"] == "txt" for item in uploads)


def test_get_session_uploads_forbidden_for_other_user(client, monkeypatch):
    owner_token = _register_and_token(client, "upload_owner", "upload_owner@example.com")
    intruder_token = _register_and_token(client, "upload_intruder", "upload_intruder@example.com")
    session_id = _start_session(client, owner_token, monkeypatch)

    get_uploads = client.get(
        f"/api/sessions/{session_id}/uploads",
        headers={"Authorization": f"Bearer {intruder_token}"},
    )
    assert get_uploads.status_code == 403


def test_session_uploads_missing_session_returns_404(client):
    token = _register_and_token(client, "upload_missing_user", "upload_missing@example.com")

    get_uploads = client.get(
        "/api/sessions/missing-session/uploads",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_uploads.status_code == 404

    upload = client.post(
        "/api/sessions/missing-session/upload",
        files={"file": ("note.txt", BytesIO(b"text"), "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert upload.status_code == 404


def test_upload_session_file_rejects_unsupported_type(client, monkeypatch):
    token = _register_and_token(client, "upload_type_user", "upload_type@example.com")
    session_id = _start_session(client, token, monkeypatch)

    upload = client.post(
        f"/api/sessions/{session_id}/upload",
        files={"file": ("malware.exe", BytesIO(b"bad"), "application/octet-stream")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert upload.status_code == 400
    assert "supported" in upload.json()["detail"].lower()


def test_upload_session_file_forbidden_for_other_user(client, monkeypatch):
    owner_token = _register_and_token(client, "upload_owner2", "upload_owner2@example.com")
    intruder_token = _register_and_token(client, "upload_intruder2", "upload_intruder2@example.com")
    session_id = _start_session(client, owner_token, monkeypatch)

    upload = client.post(
        f"/api/sessions/{session_id}/upload",
        files={"file": ("note.txt", BytesIO(b"text"), "text/plain")},
        headers={"Authorization": f"Bearer {intruder_token}"},
    )
    assert upload.status_code == 403


def test_upload_session_file_processing_error_returns_400(client, monkeypatch):
    import main

    token = _register_and_token(client, "upload_error_user", "upload_error@example.com")
    session_id = _start_session(client, token, monkeypatch)
    monkeypatch.setattr(
        main,
        "_extract_text_from_txt",
        lambda path: (_ for _ in ()).throw(RuntimeError("extract failed")),
    )

    upload = client.post(
        f"/api/sessions/{session_id}/upload",
        files={"file": ("note.txt", BytesIO(b"text"), "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert upload.status_code == 400
    assert "failed to process file" in upload.json()["detail"].lower()

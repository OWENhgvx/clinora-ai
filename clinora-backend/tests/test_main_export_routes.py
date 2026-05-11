def test_export_pdf_session_not_found(client, monkeypatch):
    import main

    monkeypatch.setattr(main, "session_get", lambda session_id: None)
    resp = client.get("/api/session/non-existent/export/pdf")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_export_pdf_not_complete(client, monkeypatch):
    import main

    monkeypatch.setattr(
        main,
        "session_get",
        lambda session_id: {"id": session_id, "status": "interviewing"},
    )
    resp = client.get("/api/session/s1/export/pdf")
    assert resp.status_code == 400
    assert "not complete" in resp.json()["detail"].lower()


def test_export_pdf_success(client, monkeypatch):
    import main

    fake_session = {"id": "session-123", "status": "done"}
    monkeypatch.setattr(main, "session_get", lambda session_id: fake_session)
    monkeypatch.setattr(main, "generate_pdf", lambda sess: b"%PDF-1.4 test pdf bytes")

    resp = client.get("/api/session/session-123/export/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")
    assert resp.content.startswith(b"%PDF")


def test_export_json_session_not_found(client, monkeypatch):
    import main

    monkeypatch.setattr(main, "session_get", lambda session_id: None)
    resp = client.get("/api/session/non-existent/export/json")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_export_json_success(client, monkeypatch):
    import json
    import main

    fake_session = {
        "id": "session-json-1",
        "status": "done",
        "diagnosis": "example diagnosis",
        "history": [{"role": "user", "content": "hidden in export"}],
    }
    monkeypatch.setattr(main, "session_get", lambda session_id: fake_session)

    resp = client.get("/api/session/session-json-1/export/json")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    data = json.loads(resp.text)
    assert data["id"] == "session-json-1"
    assert "history" not in data
    assert "exported_at" in data

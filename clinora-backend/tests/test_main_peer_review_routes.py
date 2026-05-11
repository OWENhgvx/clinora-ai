def test_peer_review_session_not_found(client, monkeypatch):
    import main

    monkeypatch.setattr(main, "session_get", lambda session_id: None)
    resp = client.get("/api/session/missing/peer-review")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_peer_review_requires_existing_diagnosis(client, monkeypatch):
    import main

    monkeypatch.setattr(
        main,
        "session_get",
        lambda session_id: {
            "id": session_id,
            "user_id": None,
            "symptoms": {"description": "headache"},
            "diagnosis": "",
            "review": "",
        },
    )
    resp = client.get("/api/session/s1/peer-review")
    assert resp.status_code == 400
    assert "no diagnosis" in resp.json()["detail"].lower()


def test_peer_review_returns_cached_result(client, monkeypatch):
    import main

    cached = '{"verdict":"AGREE","assessment":"Cached review","correct":true}'
    monkeypatch.setattr(
        main,
        "session_get",
        lambda session_id: {
            "id": session_id,
            "user_id": None,
            "symptoms": {"description": "headache"},
            "diagnosis": "diagnosis text",
            "review": "critic text",
            "mistral_peer_review": cached,
        },
    )

    resp = client.get("/api/session/s1/peer-review")
    assert resp.status_code == 200
    assert resp.json()["assessment"] == "Cached review"


def test_peer_review_generates_and_caches_result(client, monkeypatch):
    import main

    writes = []

    monkeypatch.setattr(
        main,
        "session_get",
        lambda session_id: {
            "id": session_id,
            "user_id": None,
            "symptoms": {
                "description": "headache",
                "body_part": "Head",
                "duration": "2 days",
            },
            "severity_level": "moderate",
            "diagnosis": "Likely migraine",
            "review": "No immediate red flags",
            "mistral_peer_review": None,
        },
    )
    monkeypatch.setattr(
        main,
        "run_mistral_diagnosis_review",
        lambda **kwargs: {
            "verdict": "AGREE",
            "assessment": "Independent review agrees.",
            "correct": True,
        },
    )

    class FakeConn:
        def execute(self, sql, vals):
            writes.append((sql, vals))

        def commit(self):
            writes.append(("commit", None))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(main, "get_db", lambda: FakeConn())

    resp = client.get("/api/session/s1/peer-review")
    assert resp.status_code == 200
    body = resp.json()
    assert body["verdict"] == "AGREE"
    assert body["correct"] is True
    assert any("UPDATE sessions SET mistral_peer_review" in item[0] for item in writes if item[1])

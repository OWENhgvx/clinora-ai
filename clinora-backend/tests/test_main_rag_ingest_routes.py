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


def test_rag_ingest_requires_auth(client):
    resp = client.post("/api/rag/ingest", json={"terms": ["headache"], "per_term": 2})
    assert resp.status_code == 401


def test_rag_ingest_rejects_patient_role(client):
    token = _register_and_token(client, "rag_patient", "rag_patient@example.com", role="patient")
    resp = client.post(
        "/api/rag/ingest",
        json={"terms": ["headache"], "per_term": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert "provider" in resp.json()["detail"].lower()


def test_rag_ingest_provider_handles_no_pmids(client, monkeypatch):
    import main

    token = _register_and_token(client, "rag_provider_empty", "rag_provider_empty@example.com", role="provider")
    monkeypatch.setattr(main, "get_collection_size", lambda: 10)
    monkeypatch.setattr(main, "fetch_pmids", lambda term, per_term: [])

    resp = client.post(
        "/api/rag/ingest",
        json={"terms": ["rare condition"], "per_term": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_added"] == 0
    assert body["initial_db_size"] == 10
    assert body["final_db_size"] == 10
    assert body["details"][0]["found"] == 0


def test_rag_ingest_provider_success(client, monkeypatch):
    import main

    token = _register_and_token(client, "rag_provider_ok", "rag_provider_ok@example.com", role="provider")
    sizes = iter([5, 7])
    monkeypatch.setattr(main, "get_collection_size", lambda: next(sizes))
    monkeypatch.setattr(main, "fetch_pmids", lambda term, per_term: ["1", "2"])
    monkeypatch.setattr(
        main,
        "fetch_article_details",
        lambda pmids: [
            {"id": "1", "text": "article one"},
            {"id": "2", "text": "article two"},
        ],
    )
    monkeypatch.setattr(main, "add_documents", lambda articles: 2)

    resp = client.post(
        "/api/rag/ingest",
        json={"terms": ["migraine"], "per_term": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_added"] == 2
    assert body["initial_db_size"] == 5
    assert body["final_db_size"] == 7
    assert body["terms_processed"] == 1
    assert body["details"][0]["added"] == 2

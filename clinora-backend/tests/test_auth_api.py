def test_register_success(client):
    payload = {
        "username": "alice01",
        "email": "alice@example.com",
        "password": "securepass123",
        "full_name": "Alice",
        "role": "patient",
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["token"]
    assert body["user"]["username"] == "alice01"
    assert "password" not in body["user"]


def test_register_duplicate_username_fails(client):
    payload = {
        "username": "dup_user",
        "email": "dup1@example.com",
        "password": "securepass123",
        "full_name": "Dup",
        "role": "patient",
    }
    first = client.post("/api/auth/register", json=payload)
    assert first.status_code == 200

    second_payload = {**payload, "email": "dup2@example.com"}
    second = client.post("/api/auth/register", json=second_payload)
    assert second.status_code == 400
    assert "taken" in second.json()["detail"].lower()


def test_login_json_success_and_wrong_password(client):
    register_payload = {
        "username": "bob01",
        "email": "bob@example.com",
        "password": "securepass123",
        "full_name": "Bob",
        "role": "patient",
    }
    reg = client.post("/api/auth/register", json=register_payload)
    assert reg.status_code == 200

    ok = client.post(
        "/api/auth/login/json",
        json={"username": "bob01", "password": "securepass123"},
    )
    assert ok.status_code == 200
    assert ok.json()["token"]

    bad = client.post(
        "/api/auth/login/json",
        json={"username": "bob01", "password": "wrong-pass"},
    )
    assert bad.status_code == 401
    assert "incorrect" in bad.json()["detail"].lower()


def test_login_oauth_form_success_and_wrong_password(client):
    register_payload = {
        "username": "formuser01",
        "email": "formuser@example.com",
        "password": "securepass123",
        "full_name": "Form User",
        "role": "patient",
    }
    reg = client.post("/api/auth/register", json=register_payload)
    assert reg.status_code == 200

    ok = client.post(
        "/api/auth/login",
        data={"username": "formuser01", "password": "securepass123"},
    )
    assert ok.status_code == 200
    assert ok.json()["access_token"]
    assert ok.json()["token_type"] == "bearer"
    assert "password" not in ok.json()["user"]

    bad = client.post(
        "/api/auth/login",
        data={"username": "formuser01", "password": "wrong-pass"},
    )
    assert bad.status_code == 401
    assert "incorrect" in bad.json()["detail"].lower()


def test_auth_me_requires_valid_token(client):
    no_token = client.get("/api/auth/me")
    assert no_token.status_code == 401

    register_payload = {
        "username": "charlie01",
        "email": "charlie@example.com",
        "password": "securepass123",
        "full_name": "Charlie",
        "role": "provider",
    }
    reg = client.post("/api/auth/register", json=register_payload)
    token = reg.json()["token"]

    with_token = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert with_token.status_code == 200
    assert with_token.json()["username"] == "charlie01"


def test_register_missing_required_field_fails(client):
    payload = {
        "username": "missing_email_user",
        "password": "securepass123",
        "full_name": "No Email",
        "role": "patient",
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 422
    assert "email" in resp.json()["detail"].lower()


def test_login_json_nonexistent_user_fails(client):
    resp = client.post(
        "/api/auth/login/json",
        json={"username": "does_not_exist", "password": "irrelevant"},
    )
    assert resp.status_code == 401
    assert "incorrect" in resp.json()["detail"].lower()

from conftest import registration_payload


def test_register_success(client):
    payload = registration_payload("alice01", "alice@example.com", full_name="Alice")
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["token"]
    assert body["user"]["username"] == "alice01"
    assert body["user"]["bmi"] == 22.5
    assert body["user"]["verification_status"] == "active"
    assert "password" not in body["user"]


def test_register_duplicate_username_fails(client):
    payload = registration_payload("dup_user", "dup1@example.com", full_name="Dup")
    first = client.post("/api/auth/register", json=payload)
    assert first.status_code == 200

    second_payload = {**payload, "email": "dup2@example.com"}
    second = client.post("/api/auth/register", json=second_payload)
    assert second.status_code == 400
    assert "taken" in second.json()["detail"].lower()


def test_login_json_success_and_wrong_password(client):
    register_payload = registration_payload("bob01", "bob@example.com", full_name="Bob")
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
    register_payload = registration_payload(
        "formuser01", "formuser@example.com", full_name="Form User"
    )
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

    register_payload = registration_payload(
        "charlie01", "charlie@example.com", "provider", full_name="Dr. Charlie"
    )
    reg = client.post("/api/auth/register", json=register_payload)
    token = reg.json()["token"]

    with_token = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert with_token.status_code == 200
    assert with_token.json()["username"] == "charlie01"
    assert with_token.json()["verification_status"] == "pending_review"


def test_register_missing_required_field_fails(client):
    payload = registration_payload("missing_email_user", "missing@example.com")
    payload.pop("email")
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


def test_patient_registration_requires_data_authorization(client):
    payload = registration_payload(
        "no_consent_user",
        "no_consent@example.com",
        data_authorization_accepted=False,
    )
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 422
    assert "authorization" in resp.text.lower()


def test_provider_registration_requires_credentials(client):
    payload = registration_payload(
        "provider_missing",
        "provider_missing@example.com",
        "provider",
        license_number="",
    )
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 422
    assert "license_number" in resp.text


def test_provider_registration_does_not_require_patient_health_fields(client):
    payload = registration_payload(
        "provider_no_health",
        "provider_no_health@example.com",
        "provider",
    )
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 200
    user = resp.json()["user"]
    assert user["role"] == "provider"
    assert user["height_cm"] is None
    assert user["weight_kg"] is None
    assert user["allergies"] is None
    assert user["chronic_conditions"] is None

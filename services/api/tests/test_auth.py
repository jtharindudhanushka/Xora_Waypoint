from fastapi.testclient import TestClient

from tests.conftest import PASSWORD, auth_header


def test_login_returns_token_and_user_scope(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login", json={"email": "Driver@test.local", "password": PASSWORD}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == "driver"


def test_wrong_password_is_rejected_without_revealing_the_account(client: TestClient) -> None:
    wrong = client.post(
        "/api/v1/auth/login", json={"email": "driver@test.local", "password": "nope"}
    )
    unknown = client.post(
        "/api/v1/auth/login", json={"email": "ghost@test.local", "password": "nope"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["code"] == unknown.json()["code"] == "INVALID_CREDENTIALS"


def test_me_requires_a_valid_token(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401
    bad = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert bad.status_code == 401
    ok = client.get("/api/v1/auth/me", headers=auth_header(client, "loader"))
    assert ok.status_code == 200
    assert ok.json()["role"] == "loader"

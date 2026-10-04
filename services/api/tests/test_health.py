from fastapi.testclient import TestClient

from app.main import create_app


def test_health_ok_and_request_id_echoed() -> None:
    client = TestClient(create_app())
    response = client.get("/api/v1/health", headers={"X-Request-ID": "abc123"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"] == "abc123"


def test_unknown_route_returns_problem_json() -> None:
    client = TestClient(create_app())
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["status"] == 404

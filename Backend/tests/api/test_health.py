from fastapi.testclient import TestClient

from tallerclaro.main import create_app


def test_health_is_available_without_external_services():
    with TestClient(create_app()) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

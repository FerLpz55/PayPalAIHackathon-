from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from tallerclaro.infrastructure.db.connection import Database


def test_health_is_available_without_external_services():
    from tallerclaro.main import create_app

    with TestClient(create_app(database=MagicMock(spec=Database))) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

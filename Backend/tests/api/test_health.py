from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from tallerclaro.infrastructure.db.connection import Database


def test_health_is_available_without_external_services():
    from tallerclaro.main import create_app
    from tallerclaro.bootstrap.settings import Settings
    import bcrypt

    settings = Settings(workshop_password_hash=bcrypt.hashpw(b"test-password", bcrypt.gensalt(rounds=4)).decode())
    with TestClient(create_app(settings=settings, database=MagicMock(spec=Database))) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

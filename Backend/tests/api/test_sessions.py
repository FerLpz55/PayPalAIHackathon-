"""Sesiones del taller: cookies, CSRF, rotación, revocación y aislamiento."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import bcrypt
import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from tallerclaro.bootstrap.settings import Settings
from tallerclaro.domain.entities import Carpenter, CarpenterId
from tallerclaro.infrastructure.security.session_service import (
    WorkshopSessionService,
    credential_fingerprint,
)
from tallerclaro.presentation.http.dependencies import get_unit_of_work
from tallerclaro.presentation.http.session_cookies import (
    CSRF_COOKIE_NAME,
    SESSION_COOKIE_NAME,
)
from tests.fakes import FakeAIService, FakePaymentProcessor, FakeUnitOfWork

PASSWORD = "demo-password"
ORIGIN = "http://localhost:5173"


def _settings(**overrides) -> Settings:
    values = {
        "workshop_username": "taller",
        "workshop_password_hash": bcrypt.hashpw(
            PASSWORD.encode(), bcrypt.gensalt(rounds=4)
        ).decode(),
        "workshop_carpenter_id": 1,
        "cors_origins": [ORIGIN],
    }
    values.update(overrides)
    return Settings(**values)


def _build_app(settings: Settings, uow: FakeUnitOfWork):
    from tallerclaro.main import create_app

    with uow:
        uow.carpenters.seed(
            Carpenter(
                id=CarpenterId(1),
                name="José Carpintero",
                workshop_name="Taller José",
                email="jose@tallerclaro.com",
                phone=None,
            )
        )
        uow.commit()

    app = create_app(
        settings=settings,
        ai_service=FakeAIService(),
        payment_processor=FakePaymentProcessor(success=True),
    )

    def override_uow(request: Request):
        return uow

    app.dependency_overrides[get_unit_of_work] = override_uow
    return app, TestClient(app, base_url="https://testserver")


@pytest.fixture
def session_app():
    uow = FakeUnitOfWork()
    settings = _settings()
    app, client = _build_app(settings, uow)
    return client, uow, settings


def _login(client: TestClient, username: str = "taller", password: str = PASSWORD):
    return client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )


def _cookie_values(response) -> str:
    return "; ".join(response.headers.get_list("set-cookie"))


def test_login_sets_host_prefixed_secure_httponly_cookies(session_app):
    client, uow, _ = session_app
    resp = _login(client)

    assert resp.status_code == 200
    cookies = _cookie_values(resp)
    assert f"{SESSION_COOKIE_NAME}=" in cookies
    assert f"{CSRF_COOKIE_NAME}=" in cookies
    assert "HttpOnly" in cookies
    assert "Secure" in cookies
    assert "SameSite=lax" in cookies
    assert "Path=/" in cookies
    assert "Domain=" not in cookies
    assert resp.headers["cache-control"] == "no-store"

    body = resp.json()
    assert body["authenticated"] is True
    assert body["carpenter_id"] == 1
    assert body["csrf_token"] == client.cookies.get(CSRF_COOKIE_NAME)
    serialized = json.dumps(body).lower()
    assert "password" not in serialized
    assert "session_token" not in serialized


def test_session_store_never_contains_plaintext_token(session_app):
    client, uow, _ = session_app
    _login(client)
    token = client.cookies.get(SESSION_COOKIE_NAME)

    assert token
    with uow:
        assert token not in uow.sessions.stored_hashes
        assert len(uow.sessions.stored_hashes) == 1


def test_session_endpoint_returns_current_workshop(session_app):
    client, _, _ = session_app
    assert client.get("/api/auth/session").status_code == 401

    _login(client)
    resp = client.get("/api/auth/session")
    assert resp.status_code == 200
    assert resp.json()["carpenter_id"] == 1
    assert resp.json()["idle_timeout_seconds"] == 30 * 60
    assert resp.json()["absolute_timeout_seconds"] == 8 * 3600


def test_workshop_routes_accept_session_cookie(session_app):
    client, _, _ = session_app
    _login(client)
    assert client.get("/api/orders").status_code == 200


def test_unsafe_cookie_requests_require_csrf(session_app):
    client, _, _ = session_app
    _login(client)

    missing = client.patch("/api/orders/1", json={"status": "in_progress"})
    assert missing.status_code == 403
    assert missing.json()["code"] == "FORBIDDEN"

    csrf = client.cookies.get(CSRF_COOKIE_NAME)
    wrong = client.patch(
        "/api/orders/1",
        json={"status": "in_progress"},
        headers={"X-CSRF-Token": "not-the-cookie"},
    )
    assert wrong.status_code == 403

    accepted = client.patch(
        "/api/orders/1",
        json={"status": "in_progress"},
        headers={"X-CSRF-Token": csrf},
    )
    # La autenticación pasa; el pedido inexistente produce 404, no 401/403.
    assert accepted.status_code == 404


def test_disallowed_origin_is_rejected_on_login(session_app):
    client, _, _ = session_app
    resp = client.post(
        "/api/auth/login",
        json={"username": "taller", "password": PASSWORD},
        headers={"Origin": "https://evil.example"},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"


def test_allowed_origin_is_accepted_on_login(session_app):
    client, _, _ = session_app
    resp = client.post(
        "/api/auth/login",
        json={"username": "taller", "password": PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert resp.status_code == 200


def test_wrong_credentials_do_not_create_session(session_app):
    client, uow, _ = session_app
    resp = _login(client, password="wrong-password")
    assert resp.status_code == 401
    with uow:
        assert uow.sessions.stored_hashes == []
    assert SESSION_COOKIE_NAME not in resp.headers.get("set-cookie", "")


def test_logout_revokes_session_and_clears_cookies(session_app):
    client, uow, _ = session_app
    _login(client)
    csrf = client.cookies.get(CSRF_COOKIE_NAME)

    logout = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
    assert logout.status_code == 204
    cookies = _cookie_values(logout)
    assert f"{SESSION_COOKIE_NAME}=" in cookies
    assert "Max-Age=0" in cookies or "expires" in cookies.lower()

    assert client.get("/api/auth/session").status_code == 401
    assert client.get("/api/orders").status_code == 401


def test_logout_without_csrf_is_rejected(session_app):
    client, uow, _ = session_app
    _login(client)
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 403
    assert client.get("/api/auth/session").status_code == 200


def test_login_rotates_previous_session(session_app):
    client, uow, _ = session_app
    _login(client)
    first_token = client.cookies.get(SESSION_COOKIE_NAME)

    _login(client)
    second_token = client.cookies.get(SESSION_COOKIE_NAME)

    assert first_token != second_token
    with uow:
        assert uow.sessions.verify(first_token) is None
        assert uow.sessions.verify(second_token) == CarpenterId(1)


def test_basic_auth_is_disabled_by_default(session_app):
    client, _, settings = session_app
    assert settings.enable_workshop_basic_auth is False
    resp = client.get("/api/orders", auth=("taller", PASSWORD))
    assert resp.status_code == 401


def test_basic_auth_only_works_when_explicitly_enabled():
    uow = FakeUnitOfWork()
    settings = _settings(enable_workshop_basic_auth=True)
    _, client = _build_app(settings, uow)
    resp = client.get("/api/orders", auth=("taller", PASSWORD))
    assert resp.status_code == 200


def test_customer_token_is_not_accepted_as_workshop_session(session_app):
    client, uow, _ = session_app
    with uow:
        token = uow.tokens.create(
            __import__("tallerclaro.domain.entities", fromlist=["CustomerId"]).CustomerId(1),
            __import__("tallerclaro.domain.entities", fromlist=["QuoteId"]).QuoteId(1),
        )
        uow.commit()
    resp = client.get("/api/orders", headers={"X-Customer-Token": token})
    assert resp.status_code == 401


# --- Semántica del repositorio de sesiones ---


def _service(clock) -> WorkshopSessionService:
    conn = MagicMock()
    return WorkshopSessionService(
        conn,
        credential_fingerprint=credential_fingerprint("hash"),
        idle_minutes=30,
        absolute_hours=8,
        clock=clock,
    )


def test_postgres_session_service_stores_only_hash():
    now = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
    service = _service(lambda: now)
    token = service.create(CarpenterId(7))

    params = service._conn.execute.call_args.args[1]
    assert params[0] == 7
    assert params[1] != token
    assert len(params[1]) == 64  # sha256 hex
    assert params[2] == credential_fingerprint("hash")
    assert params[4] == now
    assert params[5] == now + timedelta(hours=8)


def test_postgres_session_service_verifies_with_idle_and_absolute_limits():
    now = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
    service = _service(lambda: now)
    service._conn.execute.return_value.fetchone.return_value = (7,)

    assert service.verify("token") == CarpenterId(7)

    sql, params = service._conn.execute.call_args.args
    assert "ultimo_uso > %s" in sql
    assert "credencial_huella = %s" in sql
    assert params[3] == now
    assert params[4] == now - timedelta(minutes=30)


def test_postgres_session_service_rejects_unknown_or_revoked():
    now = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
    service = _service(lambda: now)
    service._conn.execute.return_value.fetchone.return_value = None
    assert service.verify("unknown") is None


def test_fake_session_repository_enforces_idle_expiry():
    now = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
    from tests.fakes import FakeWorkshopSessionRepository

    clock = {"now": now}
    repository = FakeWorkshopSessionRepository(clock=lambda: clock["now"])
    token = repository.create(CarpenterId(1))

    clock["now"] = now + timedelta(minutes=29)
    assert repository.verify(token) == CarpenterId(1)

    clock["now"] = now + timedelta(minutes=29 + 31)
    assert repository.verify(token) is None


def test_fake_session_repository_enforces_absolute_expiry_despite_activity():
    now = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
    from tests.fakes import FakeWorkshopSessionRepository

    clock = {"now": now}
    repository = FakeWorkshopSessionRepository(clock=lambda: clock["now"])
    token = repository.create(CarpenterId(1))

    for _ in range(8):
        clock["now"] += timedelta(minutes=20)
        repository.verify(token)

    clock["now"] = now + timedelta(hours=8, minutes=1)
    assert repository.verify(token) is None


def test_fake_session_repository_rejects_changed_credentials():
    now = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
    from tests.fakes import FakeWorkshopSessionRepository

    clock = {"now": now}
    repository = FakeWorkshopSessionRepository(
        clock=lambda: clock["now"], credential_fingerprint="old-hash"
    )
    token = repository.create(CarpenterId(1))
    assert repository.verify(token) == CarpenterId(1)

    repository._credential_fingerprint = "new-hash"
    assert repository.verify(token) is None


def test_revoke_all_invalidates_every_session_of_the_workshop():
    now = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
    from tests.fakes import FakeWorkshopSessionRepository

    repository = FakeWorkshopSessionRepository(clock=lambda: now)
    first = repository.create(CarpenterId(1))
    second = repository.create(CarpenterId(1))

    assert repository.revoke_all(CarpenterId(1)) == 2
    assert repository.verify(first) is None
    assert repository.verify(second) is None

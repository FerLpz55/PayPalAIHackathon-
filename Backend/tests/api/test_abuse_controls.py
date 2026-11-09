"""Controles de abuso, recuperación de cliente y límites de Fase C."""

from __future__ import annotations

from datetime import datetime, timezone

import bcrypt
import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from tallerclaro.application.exceptions import RateLimitedError
from tallerclaro.bootstrap.settings import Settings
from tallerclaro.domain.entities import Carpenter, CarpenterId
from tallerclaro.presentation.http.dependencies import get_unit_of_work
from tallerclaro.presentation.http.rate_limits import (
    GENERATION_WORKSHOP_BUDGET,
    enforce_quote_generation,
)
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


def _build_app(settings: Settings | None = None, uow: FakeUnitOfWork | None = None):
    from tallerclaro.main import create_app

    settings = settings or _settings()
    uow = uow or FakeUnitOfWork()
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
    return app, uow, TestClient(app, base_url="https://testserver")


def _create_quote(client: TestClient, request: str = "Mesa de centro"):
    return client.post(
        "/api/quotes",
        json={
            "customer": {"name": "Carlos", "email": "carlos@example.com"},
            "carpenter_id": 1,
            "request": request,
        },
    )


def _csrf(client: TestClient) -> str:
    return client.cookies.get(CSRF_COOKIE_NAME)


# --- Límites de creación y generación ---


def test_quote_creation_is_limited_per_ip_with_retry_after():
    _, _, client = _build_app()

    for _ in range(5):
        assert _create_quote(client).status_code == 201

    blocked = _create_quote(client)
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "RATE_LIMITED"
    assert int(blocked.headers["retry-after"]) >= 1


def test_quote_generation_is_limited_per_quote():
    _, _, client = _build_app()
    created = _create_quote(client).json()
    token = created["customer_token"]

    for _ in range(5):
        response = client.post(
            f"/api/quotes/{created['id']}/generate",
            headers={"X-Customer-Token": token},
        )
        assert response.status_code == 200

    blocked = client.post(
        f"/api/quotes/{created['id']}/generate",
        headers={"X-Customer-Token": token},
    )
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "RATE_LIMITED"
    assert int(blocked.headers["retry-after"]) >= 1


def test_workshop_generation_budget_is_enforced_across_quotes():
    uow = FakeUnitOfWork()
    moment = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)

    for quote_id in range(1, GENERATION_WORKSHOP_BUDGET + 1):
        enforce_quote_generation(uow, quote_id, workshop_id=1, now=moment)

    with pytest.raises(RateLimitedError) as error:
        enforce_quote_generation(
            uow, GENERATION_WORKSHOP_BUDGET + 1, workshop_id=1, now=moment
        )
    assert error.value.retry_after >= 1


def test_generation_limit_is_checked_before_the_ai_call(monkeypatch):
    class ExplodingAI:
        def generate_quote_proposal(self, request: str):
            raise AssertionError("AI must not be called when the limit is exhausted")

    uow = FakeUnitOfWork()
    settings = _settings()
    app, _, client = _build_app(settings=settings, uow=uow)
    created = _create_quote(client).json()
    token = created["customer_token"]

    moment = datetime.now(timezone.utc)
    monkeypatch.setattr(
        "tallerclaro.presentation.http.rate_limits.utcnow", lambda: moment
    )
    for _ in range(5):
        enforce_quote_generation(uow, int(created["id"]), workshop_id=1, now=moment)
    app.state.ai_service = ExplodingAI()

    response = client.post(
        f"/api/quotes/{created['id']}/generate",
        headers={"X-Customer-Token": token},
    )
    assert response.status_code == 429


# --- Cuerpo máximo y proxies ---


def test_request_body_larger_than_limit_is_rejected_before_validation():
    _, _, client = _build_app()

    response = client.post(
        "/api/quotes",
        json={
            "customer": {"name": "Carlos", "email": "carlos@example.com"},
            "carpenter_id": 1,
            "request": "x" * (65 * 1024),
        },
    )

    assert response.status_code == 413
    assert response.json()["code"] == "PAYLOAD_TOO_LARGE"


def test_forwarded_ip_is_ignored_unless_proxy_is_trusted():
    _, _, client = _build_app()

    for index in range(5):
        assert (
            client.post(
                "/api/quotes",
                json={
                    "customer": {"name": f"C{index}", "email": f"c{index}@example.com"},
                    "carpenter_id": 1,
                    "request": "Mesa",
                },
                headers={"X-Forwarded-For": f"203.0.113.{index}"},
            ).status_code
            == 201
        )

    blocked = client.post(
        "/api/quotes",
        json={
            "customer": {"name": "C6", "email": "c6@example.com"},
            "carpenter_id": 1,
            "request": "Mesa",
        },
        headers={"X-Forwarded-For": "203.0.113.6"},
    )
    assert blocked.status_code == 429


def test_forwarded_ip_is_used_when_proxy_headers_are_explicitly_trusted():
    _, _, client = _build_app(settings=_settings(trust_proxy_headers=True))

    for index in range(6):
        response = client.post(
            "/api/quotes",
            json={
                "customer": {"name": f"C{index}", "email": f"c{index}@example.com"},
                "carpenter_id": 1,
                "request": "Mesa",
            },
            headers={"X-Forwarded-For": f"203.0.113.{index}"},
        )
        assert response.status_code == 201


# --- Login ---


def test_login_failures_are_throttled_by_user_and_ip():
    _, uow, client = _build_app()

    for _ in range(5):
        response = client.post(
            "/api/auth/login",
            json={"username": "taller", "password": "wrong"},
        )
        assert response.status_code == 401

    blocked = client.post(
        "/api/auth/login", json={"username": "taller", "password": "wrong"}
    )
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) >= 1

    # Aun con la contraseña correcta, el bloqueo persiste en la ventana.
    still_blocked = client.post(
        "/api/auth/login", json={"username": "taller", "password": PASSWORD}
    )
    assert still_blocked.status_code == 429
    with uow:
        assert uow.sessions.stored_hashes == []


def test_successful_login_resets_failure_counter():
    _, _, client = _build_app()

    for _ in range(3):
        assert (
            client.post(
                "/api/auth/login", json={"username": "taller", "password": "wrong"}
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/api/auth/login", json={"username": "taller", "password": PASSWORD}
        ).status_code
        == 200
    )

    for _ in range(5):
        assert (
            client.post(
                "/api/auth/login", json={"username": "taller", "password": "wrong"}
            ).status_code
            == 401
        )


# --- Contexto del cliente y reemisión ---


def test_customer_context_returns_only_own_quote_order_and_payments():
    _, _, client = _build_app()
    created = _create_quote(client).json()
    token = created["customer_token"]

    generated = client.post(
        f"/api/quotes/{created['id']}/generate",
        headers={"X-Customer-Token": token},
    )
    assert generated.status_code == 200
    approved = client.post(
        f"/api/quotes/{created['id']}/approve",
        headers={"X-Customer-Token": token},
    )
    assert approved.status_code == 200

    context = client.get("/api/customer/context", headers={"X-Customer-Token": token})
    assert context.status_code == 200
    body = context.json()
    assert body["quote"]["id"] == created["id"]
    assert body["order"]["quote_id"] == created["id"]
    assert body["payments"] == []


def test_customer_context_rejects_missing_or_invalid_token():
    _, _, client = _build_app()

    assert client.get("/api/customer/context").status_code == 401
    invalid = client.get(
        "/api/customer/context", headers={"X-Customer-Token": "not-a-token"}
    )
    assert invalid.status_code == 401


def test_customer_context_does_not_accept_a_workshop_session():
    _, _, client = _build_app()
    assert (
        client.post(
            "/api/auth/login", json={"username": "taller", "password": PASSWORD}
        ).status_code
        == 200
    )

    response = client.get("/api/customer/context")
    assert response.status_code == 401
    # La cookie de taller no concede acceso a los recursos de un cliente.
    assert SESSION_COOKIE_NAME in client.cookies


def test_reissue_access_requires_workshop_and_revokes_previous_token():
    _, uow, client = _build_app()
    created = _create_quote(client).json()
    old_token = created["customer_token"]

    anonymous = client.post(f"/api/quotes/{created['id']}/customer-access")
    assert anonymous.status_code == 401

    assert (
        client.post(
            "/api/auth/login", json={"username": "taller", "password": PASSWORD}
        ).status_code
        == 200
    )
    reissued = client.post(
        f"/api/quotes/{created['id']}/customer-access",
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert reissued.status_code == 200
    new_token = reissued.json()["customer_token"]
    assert new_token != old_token

    assert (
        client.get(
            "/api/customer/context", headers={"X-Customer-Token": old_token}
        ).status_code
        == 401
    )
    assert (
        client.get(
            "/api/customer/context", headers={"X-Customer-Token": new_token}
        ).status_code
        == 200
    )


def test_reissue_access_is_forbidden_for_a_customer_token():
    _, _, client = _build_app()
    created = _create_quote(client).json()

    response = client.post(
        f"/api/quotes/{created['id']}/customer-access",
        headers={"X-Customer-Token": created["customer_token"]},
    )
    assert response.status_code == 401


def test_reissue_access_rejects_unknown_quote():
    _, _, client = _build_app()
    client.post("/api/auth/login", json={"username": "taller", "password": PASSWORD})

    response = client.post(
        "/api/quotes/999/customer-access",
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert response.status_code == 404

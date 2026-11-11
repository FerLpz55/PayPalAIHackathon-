"""Fixtures compartidas para pruebas HTTP."""

import pytest

from fastapi import Request
from fastapi.testclient import TestClient

from tallerclaro.application.dtos import AccessPrincipal
from tallerclaro.bootstrap.settings import Settings
from tallerclaro.domain.entities import CarpenterId, CustomerId, QuoteId
from tallerclaro.presentation.http.dependencies import (
    get_unit_of_work,
    require_customer_token,
    require_quote_or_workshop_principal,
    require_workshop_credentials,
)
from tests.fakes import FakeAIService, FakePaymentProcessor, FakeUnitOfWork, FakeDependenciesContainer


@pytest.fixture
def deps():
    return FakeDependenciesContainer()


@pytest.fixture
def client(deps: FakeDependenciesContainer) -> TestClient:
    from tallerclaro.main import create_app

    settings = Settings()
    app = create_app(
        settings=settings,
        ai_service=deps.ai,
        payment_processor=deps.payment,
        accounting_assistant=deps.accounting,
    )

    def override_uow(request: Request):
        return deps.uow

    def override_workshop_credentials():
        return AccessPrincipal(kind="workshop", carpenter_id=CarpenterId(1))

    def override_customer_token():
        return AccessPrincipal(kind="customer", customer_id=CustomerId(1), quote_id=QuoteId(1))

    def override_principal():
        return AccessPrincipal(kind="workshop", carpenter_id=CarpenterId(1))

    app.state.webhook_verifier = deps.webhook
    app.dependency_overrides[get_unit_of_work] = override_uow
    app.dependency_overrides[require_workshop_credentials] = override_workshop_credentials
    app.dependency_overrides[require_customer_token] = override_customer_token
    app.dependency_overrides[require_quote_or_workshop_principal] = override_principal
    return TestClient(app)

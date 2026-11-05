"""Comprobaciones de firmas; comportamiento en test_*_contract y test_repository_contracts.

Las firmas son evidencia complementaria, no una demostración de sustitución.
"""

from __future__ import annotations

import inspect

import pytest

from tallerclaro.application.interfaces import (
    AIService,
    CaptureReservationRepository,
    CarpenterRepository,
    CustomerRepository,
    CustomerTokenRepository,
    OrderRepository,
    PaymentProcessor,
    PaymentRepository,
    QuoteRepository,
)
from tallerclaro.infrastructure.db.repositories import (
    PostgresCaptureReservationRepository,
    PostgresCarpenterRepository,
    PostgresCustomerRepository,
    PostgresOrderRepository,
    PostgresPaymentRepository,
    PostgresQuoteRepository,
)
from tallerclaro.infrastructure.security.token_service import CustomerTokenService
from tallerclaro.infrastructure.ai.service import OpenAIAIService, UnconfiguredAIService
from tallerclaro.infrastructure.payment.paypal_processor import PayPalPaymentProcessor, UnconfiguredPaymentProcessor
from tests.fakes import (
    FakeAIService,
    FakeCaptureReservationRepository,
    FakeCarpenterRepository,
    FakeCustomerRepository,
    FakeCustomerTokenRepository,
    FakeOrderRepository,
    FakePaymentProcessor,
    FakePaymentRepository,
    FakeQuoteRepository,
)


def _protocol_methods(protocol: type) -> list[str]:
    return [
        name
        for name, value in vars(protocol).items()
        if callable(value) and not name.startswith("_")
    ]


def _parameters(target: object, method: str) -> list[str]:
    return list(inspect.signature(getattr(target, method)).parameters)[1:]


@pytest.mark.parametrize(
    ("protocol", "implementation"),
    [
        (CustomerRepository, FakeCustomerRepository),
        (CustomerRepository, PostgresCustomerRepository),
        (CarpenterRepository, FakeCarpenterRepository),
        (CarpenterRepository, PostgresCarpenterRepository),
        (QuoteRepository, FakeQuoteRepository),
        (QuoteRepository, PostgresQuoteRepository),
        (OrderRepository, FakeOrderRepository),
        (OrderRepository, PostgresOrderRepository),
        (PaymentRepository, FakePaymentRepository),
        (PaymentRepository, PostgresPaymentRepository),
        (CustomerTokenRepository, FakeCustomerTokenRepository),
        (CustomerTokenRepository, CustomerTokenService),
        (CaptureReservationRepository, FakeCaptureReservationRepository),
        (CaptureReservationRepository, PostgresCaptureReservationRepository),
        (AIService, FakeAIService),
        (AIService, OpenAIAIService),
        (AIService, UnconfiguredAIService),
        (PaymentProcessor, FakePaymentProcessor),
        (PaymentProcessor, PayPalPaymentProcessor),
        (PaymentProcessor, UnconfiguredPaymentProcessor),
    ],
)
def test_implementation_matches_protocol_method_signatures(protocol, implementation):
    for method in _protocol_methods(protocol):
        assert hasattr(implementation, method), f"{implementation} lacks {method}"
        assert _parameters(implementation, method) == _parameters(protocol, method), (
            f"{implementation.__name__}.{method} signature differs from {protocol.__name__}"
        )


def test_unconfigured_implementations_never_simulate_success():
    from tallerclaro.domain.exceptions import DomainError
    from tallerclaro.infrastructure.ai.service import UnconfiguredAIService
    from tallerclaro.infrastructure.payment.paypal_processor import (
        UnconfiguredPaymentProcessor,
    )

    with pytest.raises(DomainError) as ai_error:
        UnconfiguredAIService().generate_quote_proposal("Mesa")
    assert ai_error.value.code == "SERVICE_UNAVAILABLE"

    with pytest.raises(DomainError) as payment_error:
        UnconfiguredPaymentProcessor().create_order("10.00", "USD")
    assert payment_error.value.code == "SERVICE_UNAVAILABLE"

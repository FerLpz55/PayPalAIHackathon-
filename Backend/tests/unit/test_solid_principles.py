"""Pruebas unitarias de verificación de los principios S.O.L.I.D. en Backend."""

from decimal import Decimal
from unittest.mock import MagicMock
import pytest

from tallerclaro.application.dtos import AccessPrincipal
from tallerclaro.application.exceptions import ForbiddenError
from tallerclaro.application.interfaces import (
    AIService,
    PaymentProcessor,
    QuoteRepository,
    UnitOfWork,
)
from tallerclaro.application.use_cases.authorization import authorize_workshop_or_customer
from tallerclaro.bootstrap.settings import Settings
from tallerclaro.domain.entities import (
    ORDER_STATUS_TRANSITIONS,
    QUOTE_EDITABLE_STATUSES,
    CarpenterId,
    CustomerId,
    Money,
    Quote,
    QuoteId,
)
from tallerclaro.domain.exceptions import DomainError
from tallerclaro.infrastructure.ai.price_lookup import (
    Channel3ResponseParser,
    UnconfiguredPriceLookupService,
    HttpxChannel3PriceLookupService,
    build_price_lookup_service,
)
from tallerclaro.infrastructure.ai.service import (
    AIProposalParser,
    OpenAIAIService,
    UnconfiguredAIService,
    build_ai_service,
)
from tallerclaro.infrastructure.payment.paypal_processor import (
    PayPalPaymentProcessor,
    UnconfiguredPaymentProcessor,
    build_payment_processor,
)
from tallerclaro.presentation.http.dependencies import (
    _extract_customer_token,
    _parse_basic_auth_header,
    _verify_workshop_credentials,
    get_ai_service,
    get_payment_processor,
)


# ==============================================================================
# S: Single Responsibility Principle (SRP)
# ==============================================================================

def test_srp_ai_proposal_parser_isolated_from_http_client():
    """AIProposalParser parses JSON payloads in isolation without network dependencies."""
    json_payload = (
        '{"needs_information": false, "description": "Mesa de roble", '
        '"items": [{"type": "material", "description": "Roble", "unit": "u", "quantity": 1, "unit_price": 200}], '
        '"assumptions": ["Barniz mate"]}'
    )
    result = AIProposalParser.parse(json_payload)
    assert result.needs_information is False
    assert result.description == "Mesa de roble"
    assert len(result.line_items) == 1
    assert result.line_items[0].description == "Roble"
    assert result.line_items[0].unit_price == Decimal("200")
    assert result.assumptions == ["Barniz mate"]


def test_srp_channel3_response_parser_isolated_from_network():
    """Channel3ResponseParser extracts MarketPriceReference DTOs safely without I/O."""
    payload = {
        "products": [
            {
                "title": "Minwax Polyurethane Varnish",
                "offers": [
                    {
                        "domain": "acehardware.com",
                        "url": "https://buy.trychannel3.com/item123",
                        "price": {"price": "14.99", "currency": "USD"},
                    }
                ],
            }
        ]
    }
    refs = Channel3ResponseParser.parse(payload)
    assert len(refs) == 1
    assert refs[0].title == "Minwax Polyurethane Varnish"
    assert refs[0].price_usd == Decimal("14.99")
    assert refs[0].source == "acehardware.com"
    assert refs[0].url == "https://buy.trychannel3.com/item123"


def test_srp_auth_extraction_and_verification_helpers():
    """Authentication parsing and comparison logic is partitioned into cohesive functions."""
    settings = Settings(workshop_username="taller", workshop_password_hash=__import__("bcrypt").hashpw(b"secret-password", __import__("bcrypt").gensalt(rounds=4)).decode())

    # Credential verification
    assert _verify_workshop_credentials("taller", "secret-password", settings) is True
    assert _verify_workshop_credentials("taller", "wrong", settings) is False
    assert _verify_workshop_credentials("other", "secret-password", settings) is False

    # Header parsing
    assert _parse_basic_auth_header("Basic dGFsbGVyOnNlY3JldC1wYXNzd29yZA==") == ("taller", "secret-password")
    assert _parse_basic_auth_header("Bearer token123") is None
    assert _parse_basic_auth_header("Basic not_base_64!!!") is None


def test_srp_resource_authorization_helper_validates_workshop_and_customer():
    """authorize_workshop_or_customer centralizes ownership checks for quotes and orders."""
    workshop_owner = AccessPrincipal(kind="workshop", carpenter_id=CarpenterId(1))
    other_workshop = AccessPrincipal(kind="workshop", carpenter_id=CarpenterId(2))
    customer_owner = AccessPrincipal(kind="customer", customer_id=CustomerId(5), quote_id=QuoteId(10))
    other_customer = AccessPrincipal(kind="customer", customer_id=CustomerId(5), quote_id=QuoteId(99))

    authorize_workshop_or_customer(
        workshop_owner, carpenter_id=CarpenterId(1), quote_id=QuoteId(10), resource_name="quote"
    )
    authorize_workshop_or_customer(
        customer_owner, carpenter_id=CarpenterId(1), quote_id=QuoteId(10), resource_name="order"
    )

    with pytest.raises(ForbiddenError, match="Not authorized to access this quote"):
        authorize_workshop_or_customer(
            other_workshop, carpenter_id=CarpenterId(1), quote_id=QuoteId(10), resource_name="quote"
        )

    with pytest.raises(ForbiddenError, match="Not authorized to access this order"):
        authorize_workshop_or_customer(
            other_customer, carpenter_id=CarpenterId(1), quote_id=QuoteId(10), resource_name="order"
        )


def test_domain_symbolic_constants_expose_editable_and_transition_rules():
    """Domain state rules are declared as immutable symbolic constants."""
    assert "draft" in QUOTE_EDITABLE_STATUSES
    assert "approved" not in QUOTE_EDITABLE_STATUSES
    assert ORDER_STATUS_TRANSITIONS["in_progress"] == frozenset({"delivered", "cancelled"})
    assert ORDER_STATUS_TRANSITIONS["delivered"] == frozenset()
    assert ORDER_STATUS_TRANSITIONS["cancelled"] == frozenset()


# ==============================================================================
# O: Open/Closed Principle (OCP)
# ==============================================================================

def test_ocp_ai_service_factory_extensibility():
    """build_ai_service dispatches via provider registry and handles unconfigured smoothly."""
    s_none = Settings(ai_provider="none")
    assert isinstance(build_ai_service(s_none), UnconfiguredAIService)

    s_openai = Settings(ai_provider="openai", ai_api_key="sk-test")
    assert isinstance(build_ai_service(s_openai), OpenAIAIService)

    s_unknown = Settings(ai_provider="unknown-provider")
    unknown_svc = build_ai_service(s_unknown)
    assert isinstance(unknown_svc, UnconfiguredAIService)
    with pytest.raises(DomainError) as exc:
        unknown_svc.generate_quote_proposal("Mesa")
    assert "Unknown AI provider" in str(exc.value)


def test_ocp_payment_processor_factory_extensibility():
    """build_payment_processor dispatches via mode registry and handles unconfigured smoothly."""
    s_none = Settings(paypal_mode="none")
    assert isinstance(build_payment_processor(s_none), UnconfiguredPaymentProcessor)

    s_sandbox = Settings(paypal_mode="sandbox", paypal_client_id="id", paypal_client_secret="sec", paypal_return_url="https://example.org/return", paypal_cancel_url="https://example.org/cancel")
    assert isinstance(build_payment_processor(s_sandbox), PayPalPaymentProcessor)

    s_unknown = Settings(paypal_mode="unknown-mode")
    unknown_proc = build_payment_processor(s_unknown)
    assert isinstance(unknown_proc, UnconfiguredPaymentProcessor)
    with pytest.raises(DomainError) as exc:
        unknown_proc.create_order("100.00", "USD")
    assert "Unknown PayPal mode" in str(exc.value)


def test_ocp_price_lookup_service_factory_extensibility():
    """build_price_lookup_service dispatches via provider registry and handles unconfigured smoothly."""
    s_none = Settings(price_lookup_provider="none")
    assert isinstance(build_price_lookup_service(s_none), UnconfiguredPriceLookupService)

    s_c3 = Settings(price_lookup_provider="channel3", price_lookup_api_key="c3-test")
    assert isinstance(build_price_lookup_service(s_c3), HttpxChannel3PriceLookupService)

    s_unknown = Settings(price_lookup_provider="unknown-provider")
    assert isinstance(build_price_lookup_service(s_unknown), UnconfiguredPriceLookupService)


# ==============================================================================
# L: Liskov Substitution Principle (LSP)
# ==============================================================================

def test_lsp_unconfigured_services_raise_consistent_domain_errors():
    """Unconfigured implementations faithfully adhere to the Protocol signature and raise DomainError."""
    ai_service: AIService = UnconfiguredAIService()
    with pytest.raises(DomainError) as exc:
        ai_service.generate_quote_proposal("Mesa")
    assert exc.value.code == "SERVICE_UNAVAILABLE"

    payment_proc: PaymentProcessor = UnconfiguredPaymentProcessor()
    with pytest.raises(DomainError) as exc:
        payment_proc.create_order("10.00", "USD")
    assert exc.value.code == "SERVICE_UNAVAILABLE"

    with pytest.raises(DomainError) as exc:
        payment_proc.capture_order("PAYPAL-123")
    assert exc.value.code == "SERVICE_UNAVAILABLE"


# ==============================================================================
# I: Interface Segregation Principle (ISP)
# ==============================================================================

def test_isp_quote_repository_requires_only_active_use_case_methods():
    """QuoteRepository protocol only obligates save and get_by_id, not dead methods."""
    class MinimalQuoteRepo:
        def __init__(self) -> None:
            self.saved = []

        def save(self, quote: Quote) -> Quote:
            self.saved.append(quote)
            return quote

        def get_by_id(self, quote_id: QuoteId) -> Quote | None:
            return None

    # Verifies MinimalQuoteRepo conforms to QuoteRepository protocol without extra methods
    repo: QuoteRepository = MinimalQuoteRepo()
    assert repo.get_by_id(QuoteId(1)) is None


# ==============================================================================
# D: Dependency Inversion Principle (DIP)
# ==============================================================================

def test_dip_presentation_dependencies_inject_abstract_services():
    """Presentation dependencies extract services from app.state as abstract interfaces."""
    mock_request = MagicMock()
    mock_ai = MagicMock(spec=AIService)
    mock_pay = MagicMock(spec=PaymentProcessor)
    mock_request.app.state.ai_service = mock_ai
    mock_request.app.state.payment_processor = mock_pay

    assert get_ai_service(mock_request) is mock_ai
    assert get_payment_processor(mock_request) is mock_pay

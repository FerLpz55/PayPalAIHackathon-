"""Extensión de las factorías sin modificar los casos de uso (OCP)."""

from __future__ import annotations

from pathlib import Path

from tallerclaro.application.dtos import QuoteProposalResult
from tallerclaro.bootstrap.settings import Settings
from tallerclaro.domain.accounting import WorkshopFinancialSummary, summarize_workshop_finances
from tallerclaro.infrastructure.ai.accounting_service import (
    _ASSISTANT_FACTORIES,
    build_accounting_assistant,
    register_accounting_assistant,
)
from tallerclaro.infrastructure.ai.service import (
    _AI_FACTORIES,
    build_ai_service,
    register_ai_provider,
)
from tallerclaro.infrastructure.payment.paypal_processor import (
    _PAYMENT_PROCESSOR_FACTORIES,
    build_payment_processor,
    register_payment_processor,
)

SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "tallerclaro"


def test_registering_ai_provider_requires_no_use_case_change():
    class TestAIService:
        def generate_quote_proposal(self, request: str) -> QuoteProposalResult:
            return QuoteProposalResult(description=request, line_items=[])

    service = TestAIService()
    provider = "test-provider"
    try:
        register_ai_provider(provider, lambda settings: service)
        assert build_ai_service(Settings(ai_provider=provider)) is service
    finally:
        _AI_FACTORIES.pop(provider, None)


def test_registering_payment_processor_requires_no_use_case_change():
    class TestPaymentProcessor:
        def create_order(self, amount: str, currency: str):
            raise AssertionError("not used")

        def capture_order(self, paypal_order_id: str):
            raise AssertionError("not used")

    processor = TestPaymentProcessor()
    mode = "test-mode"
    try:
        register_payment_processor(mode, lambda settings: processor)
        assert build_payment_processor(Settings(paypal_mode=mode)) is processor
    finally:
        _PAYMENT_PROCESSOR_FACTORIES.pop(mode, None)


def test_application_has_no_provider_configuration_branches():
    """Añadir un proveedor no debe requerir ramas por proveedor en aplicación."""
    offenders = []
    for path in (SRC_ROOT / "application").rglob("*.py"):
        source = path.read_text(encoding="utf-8").lower()
        for marker in ("ai_provider", "paypal_mode", "openrouter", "sandbox"):
            if marker in source:
                offenders.append(f"{path.relative_to(SRC_ROOT)}: {marker}")
    assert offenders == []


def test_registering_accounting_assistant_requires_no_use_case_change():
    class TestAssistant:
        def explain(self, summary: WorkshopFinancialSummary, question: str) -> str:
            return f"Answer for {question}"

    assistant = TestAssistant()
    provider = "test-assistant-provider"
    try:
        register_accounting_assistant(provider, lambda settings: assistant)
        assert build_accounting_assistant(Settings(ai_provider=provider)) is assistant
    finally:
        _ASSISTANT_FACTORIES.pop(provider, None)


def test_composition_uses_registries_for_providers():
    """La composición se realiza mediante factorías registradas, no con isinstance."""
    payment_source = (SRC_ROOT / "infrastructure" / "payment" / "paypal_processor.py").read_text()
    ai_source = (SRC_ROOT / "infrastructure" / "ai" / "service.py").read_text()
    accounting_source = (SRC_ROOT / "infrastructure" / "ai" / "accounting_service.py").read_text()

    assert "_PAYMENT_PROCESSOR_FACTORIES" in payment_source
    assert "register_payment_processor" in payment_source
    assert "_AI_FACTORIES" in ai_source
    assert "register_ai_provider" in ai_source
    assert "_ASSISTANT_FACTORIES" in accounting_source
    assert "register_accounting_assistant" in accounting_source

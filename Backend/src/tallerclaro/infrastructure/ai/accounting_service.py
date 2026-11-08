"""Asistente contable con IA compatible con OpenAI.

La IA solo explica cifras ya calculadas por el dominio. El texto enviado al
proveedor contiene únicamente totales agregados del taller: nunca nombres,
correos ni identificadores de clientes.
"""

from __future__ import annotations

from collections.abc import Callable

import httpx

from tallerclaro.application.interfaces import AccountingAssistant
from tallerclaro.bootstrap.settings import Settings
from tallerclaro.domain.accounting import WorkshopFinancialSummary
from tallerclaro.domain.exceptions import DomainError


class UnconfiguredAccountingAssistant:
    """Implementación por defecto cuando la IA no está configurada."""

    def __init__(self, message: str = "AI service is not configured") -> None:
        self._message = message

    def explain(self, summary: WorkshopFinancialSummary, question: str) -> str:
        raise DomainError(code="SERVICE_UNAVAILABLE", message=self._message)


class AccountingFactsFormatter:
    """Convierte el resumen en hechos de texto para el modelo (Single Responsibility)."""

    @staticmethod
    def format(summary: WorkshopFinancialSummary) -> str:
        currency = summary.currency
        lines = [
            f"Currency: {currency}",
            f"Orders: {summary.orders_count} total, {summary.active_orders_count} active, "
            f"{summary.delivered_orders_count} delivered",
            f"Orders still waiting for their deposit: {summary.orders_awaiting_deposit}",
            f"Orders with a balance still due: {summary.orders_with_balance_due}",
            f"Total value of all orders: {summary.total_contracted.amount} {currency}",
            f"Money collected through verified PayPal payments: {summary.collected_total.amount} {currency}",
            f"  of which deposits: {summary.collected_deposits.amount} {currency}",
            f"  of which final balances: {summary.collected_balances.amount} {currency}",
            f"Money still to collect: {summary.pending_to_collect.amount} {currency}",
            f"Average order value: {summary.average_order_value.amount} {currency}",
            "Material costs and other expenses: not recorded in the system yet",
        ]
        return "\n".join(lines)


SYSTEM_PROMPT = (
    "You are the bookkeeping assistant of TallerClaro, an app for small carpentry and craft "
    "workshops. The owner is not an accountant, so explain things in plain, friendly words.\n"
    "Rules:\n"
    "- Answer in the same language as the owner's question.\n"
    "- Use ONLY the numbers in the workshop facts. Never invent, estimate or recalculate figures.\n"
    "- Expenses and material costs are not recorded, so you cannot know profit. If asked about "
    "profit, say so and explain what the facts do show.\n"
    "- If the facts cannot answer the question, say it clearly.\n"
    "- Do not give legal or tax advice.\n"
    "- Keep the answer under 120 words, in plain text without markdown tables."
)


class OpenAIAccountingAssistant:
    """Asistente contable usando APIs compatibles con OpenAI."""

    def __init__(
        self,
        settings: Settings,
        client: httpx.Client | None = None,
        formatter: AccountingFactsFormatter | None = None,
    ) -> None:
        self._client = client or httpx.Client(timeout=60.0)
        self._base_url = settings.ai_base_url or "https://api.openai.com/v1"
        self._api_key = settings.ai_api_key
        self._model = settings.ai_model or "gpt-4o-mini"
        self._formatter = formatter or AccountingFactsFormatter()

    def explain(self, summary: WorkshopFinancialSummary, question: str) -> str:
        if not self._api_key:
            raise DomainError(code="SERVICE_UNAVAILABLE", message="AI API key is missing")

        facts = self._formatter.format(summary)
        try:
            response = self._client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": f"Workshop facts:\n{facts}\n\nOwner's question:\n{question}",
                        },
                    ],
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        except Exception:
            raise DomainError(code="SERVICE_UNAVAILABLE", message="AI service unavailable") from None

        if not isinstance(content, str) or not content.strip():
            raise DomainError(code="AI_RESPONSE_INVALID", message="AI returned an empty answer")
        return content.strip()


# Registro extensible de proveedores (Open/Closed Principle)
_ASSISTANT_FACTORIES: dict[str, Callable[[Settings], AccountingAssistant]] = {
    "openai": lambda s: OpenAIAccountingAssistant(s),
    "openrouter": lambda s: OpenAIAccountingAssistant(s),
}


def register_accounting_assistant(
    name: str, factory: Callable[[Settings], AccountingAssistant]
) -> None:
    """Registra una implementación de asistente contable sin modificar casos de uso."""
    _ASSISTANT_FACTORIES[name.lower().strip()] = factory


def build_accounting_assistant(settings: Settings) -> AccountingAssistant:
    provider = (settings.ai_provider or "").lower().strip()
    if not provider or provider == "none":
        return UnconfiguredAccountingAssistant()

    factory = _ASSISTANT_FACTORIES.get(provider)
    if factory is not None:
        return factory(settings)

    return UnconfiguredAccountingAssistant(f"Unknown AI provider: {settings.ai_provider}")


"""Servicio de integración con IA.

Provee la comunicación con APIs de IA compatibles con OpenAI para la
estimación de cotizaciones en TallerClaro.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
import json

import httpx

from tallerclaro.application.dtos import QuoteLineItemInput, QuoteProposalResult
from tallerclaro.application.interfaces import AIService
from tallerclaro.bootstrap.settings import Settings
from tallerclaro.domain.exceptions import DomainError


class UnconfiguredAIService:
    """Implementación por defecto cuando el servicio de IA no está configurado."""

    def __init__(self, message: str = "AI service is not configured") -> None:
        self._message = message

    def generate_quote_proposal(self, request: str) -> QuoteProposalResult:
        raise DomainError(code="SERVICE_UNAVAILABLE", message=self._message)


class AIProposalParser:
    """Responsable exclusivamente de validar y convertir la respuesta JSON de IA a DTOs."""

    @staticmethod
    def parse(content: str) -> QuoteProposalResult:
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, TypeError) as exc:
            raise DomainError(
                code="AI_RESPONSE_INVALID",
                message=f"AI returned invalid JSON: {exc}",
            ) from None

        if not isinstance(data, dict):
            raise DomainError(
                code="AI_RESPONSE_INVALID",
                message="AI response must be a JSON object",
            )

        if data.get("needs_information"):
            return AIProposalParser._parse_needs_information(data, content)

        return AIProposalParser._parse_completed_proposal(data, content)

    @staticmethod
    def _parse_needs_information(data: dict, content: str) -> QuoteProposalResult:
        missing = data.get("missing_info")
        if isinstance(missing, list):
            missing_info = [str(m).strip() for m in missing if str(m).strip()]
        elif isinstance(missing, str) and missing.strip():
            missing_info = [missing.strip()]
        else:
            missing_info = []

        return QuoteProposalResult(
            description=str(data.get("description") or ""),
            line_items=[],
            assumptions=[],
            missing_info=missing_info,
            needs_information=True,
            raw_response=content,
        )

    @staticmethod
    def _parse_completed_proposal(data: dict, content: str) -> QuoteProposalResult:
        raw_items = data.get("items")
        if not isinstance(raw_items, list) or len(raw_items) == 0:
            raise DomainError(
                code="AI_RESPONSE_INVALID",
                message="Line items cannot be empty",
            )

        items: list[QuoteLineItemInput] = []
        for raw in raw_items:
            items.append(AIProposalParser._parse_item(raw))

        raw_assumptions = data.get("assumptions")
        if isinstance(raw_assumptions, list):
            assumptions = [str(a).strip() for a in raw_assumptions if str(a).strip()]
        else:
            assumptions = []

        return QuoteProposalResult(
            description=str(data.get("description") or ""),
            line_items=items,
            assumptions=assumptions,
            needs_information=False,
            raw_response=content,
        )

    @staticmethod
    def _parse_item(raw: object) -> QuoteLineItemInput:
        if not isinstance(raw, dict):
            raise DomainError(
                code="AI_RESPONSE_INVALID",
                message="Each line item must be a JSON object",
            )

        item_type = raw.get("type")
        if item_type not in {"material", "labor", "other"}:
            raise DomainError(
                code="AI_RESPONSE_INVALID",
                message=f"Invalid line item type: {item_type}",
            )

        description = raw.get("description")
        if not isinstance(description, str) or not description.strip():
            raise DomainError(
                code="AI_RESPONSE_INVALID",
                message="Line item description must be a non-empty string",
            )

        unit = raw.get("unit", "unit")
        if not isinstance(unit, str) or not unit.strip():
            unit = "unit"

        raw_qty = raw.get("quantity")
        try:
            quantity = Decimal(str(raw_qty))
            if quantity.is_nan() or quantity.is_infinite() or quantity <= 0:
                raise ValueError
        except Exception:
            raise DomainError(
                code="AI_RESPONSE_INVALID",
                message=f"Line item quantity must be a positive decimal: {raw_qty}",
            )

        raw_price = raw.get("unit_price")
        try:
            unit_price = Decimal(str(raw_price))
            if unit_price.is_nan() or unit_price.is_infinite() or unit_price < 0:
                raise ValueError
        except Exception:
            raise DomainError(
                code="AI_RESPONSE_INVALID",
                message=f"Line item unit_price must be a non-negative decimal: {raw_price}",
            )

        return QuoteLineItemInput(
            type=item_type,
            description=description.strip(),
            unit=unit.strip(),
            quantity=quantity,
            unit_price=unit_price,
        )


class OpenAIAIService:
    """Servicio de IA usando APIs compatibles con OpenAI."""

    def __init__(
        self,
        settings: Settings,
        client: httpx.Client | None = None,
        parser: AIProposalParser | None = None,
    ) -> None:
        self._settings = settings
        self._client = client or httpx.Client(timeout=60.0)
        self._base_url = settings.ai_base_url or "https://api.openai.com/v1"
        self._api_key = settings.ai_api_key
        self._model = settings.ai_model or "gpt-4o-mini"
        self._parser = parser or AIProposalParser()

    def generate_quote_proposal(self, request: str) -> QuoteProposalResult:
        if not self._api_key:
            raise DomainError(code="SERVICE_UNAVAILABLE", message="AI API key is missing")

        prompt = self._build_prompt(request)
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
                        {"role": "system", "content": prompt["system"]},
                        {"role": "user", "content": prompt["user"]},
                    ],
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
        except DomainError:
            raise
        except Exception:
            raise DomainError(code="SERVICE_UNAVAILABLE", message="AI service unavailable") from None

        return self._parser.parse(content)

    def _parse_proposal(self, content: str) -> QuoteProposalResult:
        """Delega el parseo de la propuesta al parser especializado (Single Responsibility)."""
        return self._parser.parse(content)

    def _build_prompt(self, request: str) -> dict[str, str]:
        system = (
            "You are a carpentry estimator for TallerClaro. The shop only accepts USD. "
            "Respond in JSON with this exact structure:\n"
            '{"needs_information": bool, "missing_info": [string], "description": string, '
            '"items": [{"type": "material"|"labor"|"other", "description": string, '
            '"unit": string, "quantity": number, "unit_price": number}], '
            '"assumptions": [string]}.\n'
            "If the request lacks enough detail, set needs_information=true and list missing_info. "
            "Otherwise provide line items and a clear description. "
            "Prices are in USD. Do not include totals; the server calculates them."
        )
        return {"system": system, "user": request}


# Registro extensible de proveedores (Open/Closed Principle)
_AI_FACTORIES: dict[str, Callable[[Settings], AIService]] = {
    "openai": lambda s: OpenAIAIService(s),
    "openrouter": lambda s: OpenAIAIService(s),
}


def register_ai_provider(name: str, factory: Callable[[Settings], AIService]) -> None:
    """Registra una implementación para un proveedor sin tocar los casos de uso."""
    _AI_FACTORIES[name.lower().strip()] = factory


def build_ai_service(settings: Settings) -> AIService:
    provider = (settings.ai_provider or "").lower().strip()
    if not provider or provider == "none":
        return UnconfiguredAIService()

    factory = _AI_FACTORIES.get(provider)
    if factory is not None:
        return factory(settings)

    return UnconfiguredAIService(f"Unknown AI provider: {settings.ai_provider}")

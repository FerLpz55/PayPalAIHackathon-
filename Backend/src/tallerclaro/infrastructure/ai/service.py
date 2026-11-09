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
from tallerclaro.application.interfaces import AIService, PriceLookupService
from tallerclaro.bootstrap.settings import Settings
from tallerclaro.domain.exceptions import DomainError
from tallerclaro.infrastructure.ai.price_lookup import (
    PriceContextFormatter,
    build_price_lookup_service,
)

SYSTEM_PROMPT = (
    "You are an expert carpentry and furniture estimator for TallerClaro. The shop only accepts USD.\n"
    "Respond in JSON with this exact structure:\n"
    '{"needs_information": bool, "missing_info": [string], "description": string, '
    '"items": [{"type": "material"|"labor"|"other", "description": string, '
    '"unit": string, "quantity": number, "unit_price": number}], '
    '"assumptions": [string]}.\n\n'
    "RULES:\n"
    "1. PROACTIVE ESTIMATION: For any woodworking request (tables, cabinets, shelves, desks, doors, furniture, etc.), ALWAYS generate a complete, priced proposal with 'needs_information': false. "
    "Do NOT ask for clarification unless the request is completely incomprehensible or unrelated to woodwork. "
    "If dimensions, wood species, or finish details are omitted, assume standard professional carpentry specifications (e.g. standard table 1.80m x 0.90m, pine/oak, polyurethane finish) and clearly document these choices in 'assumptions'.\n"
    "2. LINE ITEMS: Provide granular items across 'material' (lumber, boards), 'labor' (fabrication, sanding, assembly, finishing), and 'other' (hardware, hinges, delivery, consumables).\n"
    "3. PRICES: Use realistic market USD rates and ground them on verified merchant price references when provided. Do not include totals; the server calculates them.\n"
    "4. DESCRIPTIONS: Write a clear, professional description in Spanish of the piece to be crafted."
)


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
        clean_content = content.strip()
        if clean_content.startswith("```"):
            lines = clean_content.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            clean_content = "\n".join(lines).strip()

        try:
            data = json.loads(clean_content)
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

        items = [AIProposalParser._parse_item(raw) for raw in raw_items]

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

        quantity = AIProposalParser._parse_decimal_field(
            raw.get("quantity"),
            error_message=f"Line item quantity must be a positive decimal: {raw.get('quantity')}",
            allow_zero=False,
        )
        unit_price = AIProposalParser._parse_decimal_field(
            raw.get("unit_price"),
            error_message=(
                f"Line item unit_price must be a non-negative decimal: {raw.get('unit_price')}"
            ),
            allow_zero=True,
        )

        return QuoteLineItemInput(
            type=item_type,
            description=description.strip(),
            unit=unit.strip(),
            quantity=quantity,
            unit_price=unit_price,
        )

    @staticmethod
    def _parse_decimal_field(
        raw_value: object, *, error_message: str, allow_zero: bool
    ) -> Decimal:
        try:
            parsed = Decimal(str(raw_value))
            is_out_of_bounds = parsed < 0 if allow_zero else parsed <= 0
            if parsed.is_nan() or parsed.is_infinite() or is_out_of_bounds:
                raise ValueError
            return parsed
        except Exception:
            raise DomainError(
                code="AI_RESPONSE_INVALID",
                message=error_message,
            ) from None


class OpenAIAIService:
    """Servicio de IA usando APIs compatibles con OpenAI."""

    def __init__(
        self,
        settings: Settings,
        client: httpx.Client | None = None,
        parser: AIProposalParser | None = None,
        price_lookup: PriceLookupService | None = None,
        price_formatter: PriceContextFormatter | None = None,
    ) -> None:
        self._settings = settings
        self._client = client or httpx.Client(timeout=60.0)
        self._base_url = settings.ai_base_url or "https://api.openai.com/v1"
        self._api_key = settings.ai_api_key
        self._model = settings.ai_model or "gpt-4o-mini"
        self._parser = parser or AIProposalParser()
        self._price_lookup = (
            price_lookup
            if price_lookup is not None
            else build_price_lookup_service(settings)
        )
        self._price_formatter = price_formatter or PriceContextFormatter()

    def generate_quote_proposal(self, request: str) -> QuoteProposalResult:
        if not self._api_key:
            raise DomainError(code="SERVICE_UNAVAILABLE", message="AI API key is missing")

        prompt, market_prices = self._build_prompt(request)
        content = self._request_completion(prompt)
        proposal = self._parse_proposal(content)
        # Adjuntar referencias de mercado al resultado para su exposición
        if market_prices:
            return QuoteProposalResult(
                description=proposal.description,
                line_items=proposal.line_items,
                assumptions=proposal.assumptions,
                needs_information=proposal.needs_information,
                missing_info=proposal.missing_info,
                raw_response=proposal.raw_response,
                suggested_products=market_prices,
            )
        return proposal

    def _request_completion(self, prompt: dict[str, str]) -> str:
        base_payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": prompt["user"]},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self._base_url}/chat/completions"

        try:
            response = self._client.post(
                url,
                headers=headers,
                json={**base_payload, "response_format": {"type": "json_object"}},
            )
            # Reintento sin response_format si el proveedor devuelve 400 por no soportar el formato
            if response.status_code == 400 and "response_format" in response.text.lower():
                response = self._client.post(
                    url,
                    headers=headers,
                    json=base_payload,
                )
            response.raise_for_status()
            payload = response.json()
            return payload["choices"][0]["message"]["content"]
        except DomainError:
            raise
        except Exception:
            raise DomainError(code="SERVICE_UNAVAILABLE", message="AI service unavailable") from None

    def _parse_proposal(self, content: str) -> QuoteProposalResult:
        """Delega el parseo de la propuesta al parser especializado (Single Responsibility)."""
        return self._parser.parse(content)

    def _build_prompt(self, request: str) -> tuple[dict[str, str], list[MarketPriceReference]]:
        user_content = request
        market_prices: list[MarketPriceReference] = []
        try:
            market_prices = self._price_lookup.lookup_prices(request)
            formatted_context = self._price_formatter.format(market_prices)
            if formatted_context:
                user_content = (
                    f"{request}\n\n"
                    f"--- MARKET PRICE REFERENCES ---\n"
                    f"{formatted_context}\n"
                    f"Please base your line item unit prices on these real market rates when applicable, "
                    f"and cite the store/source in the assumptions list."
                )
        except Exception:
            # Degradación elegante: el fallo en la búsqueda de precios no detiene la cotización
            pass

        return {"system": SYSTEM_PROMPT, "user": user_content}, market_prices


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

"""Adaptadores de IA."""

from __future__ import annotations

import json
from decimal import Decimal

import httpx

from tallerclaro.application.dtos import QuoteLineItemInput, QuoteProposalResult
from tallerclaro.application.ports import AIService
from tallerclaro.bootstrap.settings import Settings
from tallerclaro.domain.exceptions import DomainError


class UnconfiguredAIService:
    """Doble de prueba y adaptador por defecto cuando no hay proveedor."""

    def __init__(self, message: str = "AI service is not configured") -> None:
        self._message = message

    def generate_quote_proposal(self, request: str) -> QuoteProposalResult:
        raise DomainError(code="SERVICE_UNAVAILABLE", message=self._message)


class OpenAIAIService:
    """Adaptador de IA usando OpenAI-compatible API."""

    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self._settings = settings
        self._client = client or httpx.Client(timeout=60.0)
        self._base_url = settings.ai_base_url or "https://api.openai.com/v1"
        self._api_key = settings.ai_api_key
        self._model = settings.ai_model or "gpt-4o-mini"

    def generate_quote_proposal(self, request: str) -> QuoteProposalResult:
        if not self._api_key:
            raise DomainError(code="SERVICE_UNAVAILABLE", message="AI API key is missing")

        prompt = self._build_prompt(request)
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
        return self._parse_proposal(content)

    def _build_prompt(self, request: str) -> dict[str, str]:
        system = (
            "You are a carpentry estimator for TallerClaro. The shop only accepts USD. "
            "Respond in JSON with this exact structure:\n"
            "{\"needs_information\": bool, \"missing_info\": [string], \"description\": string, "
            "\"items\": [{\"type\": \"material\"|\"labor\"|\"other\", \"description\": string, "
            "\"unit\": string, \"quantity\": number, \"unit_price\": number}], "
            "\"assumptions\": [string]}.\n"
            "If the request lacks enough detail, set needs_information=true and list missing_info. "
            "Otherwise provide line items and a clear description. "
            "Prices are in USD. Do not include totals; the server calculates them."
        )
        return {"system": system, "user": request}

    def _parse_proposal(self, content: str) -> QuoteProposalResult:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise DomainError(
                code="AI_RESPONSE_INVALID",
                message=f"AI returned invalid JSON: {exc}",
            ) from exc

        if data.get("needs_information"):
            return QuoteProposalResult(
                description="",
                line_items=[],
                missing_info=data.get("missing_info") or [],
                needs_information=True,
                raw_response=content,
            )

        items = []
        for raw in data.get("items", []):
            items.append(
                QuoteLineItemInput(
                    type=raw.get("type", "other"),
                    description=raw.get("description", ""),
                    unit=raw.get("unit", "unit"),
                    quantity=Decimal(str(raw.get("quantity", 0))),
                    unit_price=Decimal(str(raw.get("unit_price", 0))),
                )
            )

        return QuoteProposalResult(
            description=data.get("description", ""),
            line_items=items,
            assumptions=data.get("assumptions") or [],
            needs_information=False,
            raw_response=content,
        )


def build_ai_service(settings: Settings) -> AIService:
    if settings.ai_provider == "none" or not settings.ai_provider:
        return UnconfiguredAIService()
    if settings.ai_provider in {"openai", "openrouter"}:
        return OpenAIAIService(settings)
    return UnconfiguredAIService(f"Unknown AI provider: {settings.ai_provider}")

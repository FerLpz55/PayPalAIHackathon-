"""Pruebas del asistente contable de infraestructura."""

import json

import httpx
import pytest

from tallerclaro.bootstrap.settings import Settings
from tallerclaro.domain.accounting import summarize_workshop_finances
from tallerclaro.domain.exceptions import DomainError
from tallerclaro.infrastructure.ai.accounting_service import (
    AccountingFactsFormatter,
    OpenAIAccountingAssistant,
    UnconfiguredAccountingAssistant,
    build_accounting_assistant,
)


def _settings(**overrides) -> Settings:
    base = {"ai_provider": "openai", "ai_api_key": "test-key", "ai_model": "test-model"}
    base.update(overrides)
    return Settings(**base)


def _summary():
    return summarize_workshop_finances([], {})


def test_formatter_lists_aggregates_and_missing_expenses():
    text = AccountingFactsFormatter.format(_summary())
    assert "Currency: USD" in text
    assert "Money still to collect: 0.00 USD" in text
    assert "not recorded" in text


def test_openai_assistant_sends_facts_and_returns_text():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        captured["auth"] = request.headers["authorization"]
        return httpx.Response(200, json={"choices": [{"message": {"content": " All good. "}}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assistant = OpenAIAccountingAssistant(_settings(), client=client)

    answer = assistant.explain(_summary(), "How am I doing?")

    assert answer == "All good."
    assert captured["url"].endswith("/chat/completions")
    assert captured["auth"] == "Bearer test-key"
    assert captured["body"]["model"] == "test-model"
    user_message = captured["body"]["messages"][1]["content"]
    assert "Workshop facts" in user_message
    assert "How am I doing?" in user_message


def test_openai_assistant_maps_provider_errors_to_service_unavailable():
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(500)))
    assistant = OpenAIAccountingAssistant(_settings(), client=client)
    with pytest.raises(DomainError) as exc:
        assistant.explain(_summary(), "How am I doing?")
    assert exc.value.code == "SERVICE_UNAVAILABLE"


def test_openai_assistant_requires_api_key():
    assistant = OpenAIAccountingAssistant(_settings(ai_api_key=None))
    with pytest.raises(DomainError) as exc:
        assistant.explain(_summary(), "How am I doing?")
    assert exc.value.code == "SERVICE_UNAVAILABLE"


def test_factory_selects_assistant_by_provider():
    assert isinstance(build_accounting_assistant(Settings()), UnconfiguredAccountingAssistant)
    assert isinstance(build_accounting_assistant(_settings()), OpenAIAccountingAssistant)
    unknown = build_accounting_assistant(_settings(ai_provider="mystery"))
    assert isinstance(unknown, UnconfiguredAccountingAssistant)
    with pytest.raises(DomainError) as exc:
        unknown.explain(_summary(), "How am I doing?")
    assert "Unknown AI provider" in exc.value.message


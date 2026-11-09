"""Pruebas unitarias para el servicio de consulta de precios reales de materiales."""

from decimal import Decimal
from unittest.mock import MagicMock
import httpx
import pytest

from tallerclaro.application.dtos import MarketPriceReference
from tallerclaro.bootstrap.settings import Settings
from tallerclaro.infrastructure.ai.price_lookup import (
    Channel3ResponseParser,
    HttpxChannel3PriceLookupService,
    MaterialQueryExtractor,
    PriceContextFormatter,
    UnconfiguredPriceLookupService,
    build_price_lookup_service,
)
from tallerclaro.infrastructure.ai.service import OpenAIAIService


def test_material_query_extractor_identifies_carpentry_terms():
    extractor = MaterialQueryExtractor()

    queries = extractor.extract_queries("Mesa de comedor de roble con barniz poliuretano mate")
    assert any("oak" in q.lower() or "roble" in q.lower() for q in queries)
    assert any("polyurethane" in q.lower() or "barniz" in q.lower() for q in queries)

    queries_cedar = extractor.extract_queries("Silla de cedro con bisagras y tornillos")
    assert any("cedar" in q.lower() for q in queries_cedar)

    queries_fallback = extractor.extract_queries("Objeto decorativo abstracto")
    assert len(queries_fallback) >= 1


def test_channel3_response_parser_handles_valid_and_malformed_payloads():
    payload = {
        "products": [
            {
                "title": "Minwax Clear Polyurethane Varnish 1 Qt",
                "offers": [
                    {
                        "domain": "homedepot.com",
                        "url": "https://buy.trychannel3.com/hd-poly",
                        "price": {"price": 18.98, "currency": "USD"},
                    }
                ],
            },
            {
                "title": "Solid Oak Board 1x6x8ft",
                "offers": [
                    {
                        "domain": "lowes.com",
                        "url": "https://buy.trychannel3.com/lowes-oak",
                        "price": {"price": "34.50", "currency": "USD"},
                    }
                ],
            },
            # Malformed product without title
            {"offers": [{"price": {"price": 10.0}}]},
            # Malformed product with negative price
            {
                "title": "Invalid Price Item",
                "offers": [{"price": {"price": -5.0}}],
            },
            # Malformed product with zero price
            {
                "title": "Zero Price Item",
                "offers": [{"price": {"price": 0.0}}],
            },
            # Product with root price
            {
                "title": "Wood Glue 16oz",
                "price": "7.99",
                "url": "https://buy.trychannel3.com/glue",
            },
        ]
    }

    refs = Channel3ResponseParser.parse(payload)
    assert len(refs) == 3

    assert refs[0].title == "Minwax Clear Polyurethane Varnish 1 Qt"
    assert refs[0].price_usd == Decimal("18.98")
    assert refs[0].source == "homedepot.com"
    assert refs[0].url == "https://buy.trychannel3.com/hd-poly"

    assert refs[1].title == "Solid Oak Board 1x6x8ft"
    assert refs[1].price_usd == Decimal("34.50")
    assert refs[1].source == "lowes.com"

    assert refs[2].title == "Wood Glue 16oz"
    assert refs[2].price_usd == Decimal("7.99")
    assert refs[2].source == "Channel3"


def test_channel3_response_parser_handles_empty_or_non_dict_inputs():
    assert Channel3ResponseParser.parse({}) == []
    assert Channel3ResponseParser.parse({"products": "not-a-list"}) == []
    assert Channel3ResponseParser.parse({"products": [None, 123, "string"]}) == []


def test_price_context_formatter_formats_bullets():
    refs = [
        MarketPriceReference(
            title="Barniz Poly",
            price_usd=Decimal("15.50"),
            source="Home Depot",
            url="https://example.com/barniz",
        ),
        MarketPriceReference(
            title="Tabla de Roble",
            price_usd=Decimal("45.00"),
            source="Amazon",
            url=None,
        ),
    ]

    formatted = PriceContextFormatter.format(refs)
    assert "Barniz Poly: $15.50 USD [Store: Home Depot] (https://example.com/barniz)" in formatted
    assert "Tabla de Roble: $45.00 USD [Store: Amazon]" in formatted

    assert PriceContextFormatter.format([]) == ""


def test_httpx_channel3_price_lookup_success_and_fallback():
    settings = Settings(
        price_lookup_provider="channel3",
        price_lookup_api_key="c3-test-key",
        price_lookup_base_url="https://api.testchannel3.com",
    )

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "products": [
            {
                "title": "Red Oak Lumber 1x4",
                "offers": [
                    {
                        "domain": "homedepot.com",
                        "price": {"price": 22.50, "currency": "USD"},
                        "url": "https://example.com/oak",
                    }
                ],
            }
        ]
    }
    mock_client.post.return_value = mock_resp

    service = HttpxChannel3PriceLookupService(settings, client=mock_client)
    refs = service.lookup_prices("Mesa de roble")

    assert len(refs) >= 1
    assert refs[0].title == "Red Oak Lumber 1x4"
    assert refs[0].price_usd == Decimal("22.50")
    assert mock_client.post.called


def test_httpx_channel3_price_lookup_graceful_degradation_on_network_error():
    settings = Settings(
        price_lookup_provider="channel3",
        price_lookup_api_key="c3-test-key",
    )
    mock_client = MagicMock()
    mock_client.post.side_effect = httpx.RequestError("Network connection reset")

    service = HttpxChannel3PriceLookupService(settings, client=mock_client)
    # Does not raise, returns empty list
    refs = service.lookup_prices("Mesa de roble")
    assert refs == []


def test_httpx_channel3_price_lookup_no_key_returns_empty():
    settings = Settings(price_lookup_provider="channel3", price_lookup_api_key="")
    mock_client = MagicMock()

    service = HttpxChannel3PriceLookupService(settings, client=mock_client)
    refs = service.lookup_prices("Mesa de roble")
    assert refs == []
    assert not mock_client.post.called


def test_openai_ai_service_enriches_prompt_with_price_references():
    settings = Settings(ai_api_key="sk-test", ai_provider="openai")
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"description": "Mesa", "items": [{"type": "material", "description": "Roble", "quantity": 1, "unit_price": 50}], "assumptions": ["Precio basado en Home Depot"]}'
                }
            }
        ]
    }
    mock_client.post.return_value = mock_resp

    mock_lookup = MagicMock()
    mock_lookup.lookup_prices.return_value = [
        MarketPriceReference(
            title="Tablón de Roble 2x4",
            price_usd=Decimal("50.00"),
            source="Home Depot",
            url="https://homedepot.com/roble",
        )
    ]

    service = OpenAIAIService(settings=settings, client=mock_client, price_lookup=mock_lookup)
    result = service.generate_quote_proposal("Mesa de roble")

    assert result.description == "Mesa"
    # Verify that the user prompt passed to the LLM contains the market price references
    call_args = mock_client.post.call_args[1]
    messages = call_args["json"]["messages"]
    user_msg = next(m["content"] for m in messages if m["role"] == "user")
    assert "--- MARKET PRICE REFERENCES ---" in user_msg
    assert "Tablón de Roble 2x4: $50.00 USD [Store: Home Depot]" in user_msg

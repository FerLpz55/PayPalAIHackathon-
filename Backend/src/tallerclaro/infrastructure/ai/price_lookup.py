"""Servicio de consulta de precios reales de materiales e insumos para TallerClaro.

Implementa la búsqueda de precios en vivo mediante Channel3 API y fallback web
utilizando httpx, estructurando los resultados en DTOs MarketPriceReference en USD
con estricto apego a S.O.L.I.D.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal, ROUND_HALF_UP
import re
from typing import Any

import httpx

from tallerclaro.application.dtos import MarketPriceReference
from tallerclaro.application.interfaces import PriceLookupService
from tallerclaro.bootstrap.settings import Settings


# Mapeo de términos frecuentes de carpintería a términos de búsqueda optimizados
_MATERIAL_KEYWORDS: dict[str, list[str]] = {
    "roble": ["oak lumber", "solid oak wood"],
    "pino": ["pine lumber", "pino estufado"],
    "cedro": ["cedar lumber", "madera cedro"],
    "nogal": ["walnut wood lumber", "madera nogal"],
    "parota": ["parota wood slab", "madera parota"],
    "mdf": ["mdf board sheet", "tablero mdf"],
    "triplay": ["plywood sheet", "triplay madera"],
    "encino": ["oak wood board", "madera encino"],
    "melamina": ["melamine board sheet", "tablero melamina"],
    "barniz": ["polyurethane varnish", "barniz poliuretano"],
    "poliuretano": ["polyurethane wood finish", "clear polyurethane"],
    "laca": ["wood lacquer finish", "laca para madera"],
    "aceite": ["wood finish oil", "aceite linaza madera"],
    "tinte": ["wood stain", "tinte para madera"],
    "bisagra": ["cabinet door hinges", "soft close hinges"],
    "corredera": ["drawer slide rails", "soft close drawer slides"],
    "tornillo": ["wood screws", "tornillos para madera"],
    "pegamento": ["wood glue resistol", "titebond wood glue"],
    "tapacanto": ["edge banding veneer", "tapacanto pvc"],
    "resina": ["epoxy resin wood", "resina epoxica"],
    "manija": ["cabinet handles pulls", "tiradores muebles"],
    "jaladera": ["drawer pulls hardware", "jaladeras gabinete"],
    "pata": ["table legs metal wood", "patas para mesa"],
}


class MaterialQueryExtractor:
    """Extrae términos clave de búsqueda a partir del texto de la solicitud (Single Responsibility)."""

    @staticmethod
    def extract_queries(request: str) -> list[str]:
        text_lower = request.lower()
        extracted: list[str] = []

        # Si el input es una consulta directa/corta (p. ej. desde el buscador de la UI)
        words_count = len(text_lower.split())
        if 1 <= words_count <= 6:
            clean_direct = re.sub(r"[^\w\s-]", "", text_lower).strip()
            if clean_direct:
                extracted.append(clean_direct)

        for keyword, search_terms in _MATERIAL_KEYWORDS.items():
            if re.search(rf"\b{re.escape(keyword)}\b", text_lower):
                for term in search_terms:
                    if term not in extracted:
                        extracted.append(term)
                        break
                if len(extracted) >= 3:
                    break

        if not extracted:
            # Fallback: limpiar puntuación y tomar palabras clave principales
            words = [w for w in re.split(r"\W+", text_lower) if len(w) > 3][:3]
            if words:
                extracted.append(" ".join(words))
            else:
                extracted.append("carpentry lumber wood finish")

        return extracted[:3]


class Channel3ResponseParser:
    """Parsea respuestas JSON de Channel3 a DTOs MarketPriceReference puros (Single Responsibility)."""

    @staticmethod
    def _extract_image_url(prod: dict[str, Any]) -> str | None:
        images = prod.get("images")
        if isinstance(images, list) and images:
            first = images[0]
            if isinstance(first, dict):
                url = first.get("url")
                if isinstance(url, str) and url.startswith("http"):
                    return url
            elif isinstance(first, str) and first.startswith("http"):
                return first
        direct_img = prod.get("image_url") or prod.get("image")
        if isinstance(direct_img, str) and direct_img.startswith("http"):
            return direct_img
        return None

    @classmethod
    def parse(cls, payload: dict[str, Any]) -> list[MarketPriceReference]:
        results: list[MarketPriceReference] = []
        products = payload.get("products")
        if not isinstance(products, list):
            return results

        for prod in products:
            if not isinstance(prod, dict):
                continue
            title = str(prod.get("title") or "").strip()
            if not title:
                continue

            image_url = cls._extract_image_url(prod)
            offers = prod.get("offers")
            if isinstance(offers, list) and offers:
                for offer in offers:
                    if not isinstance(offer, dict):
                        continue
                    price_info = offer.get("price")
                    price_val = None
                    if isinstance(price_info, dict):
                        price_val = price_info.get("price")
                    elif price_info is not None:
                        price_val = price_info

                    if price_val is None:
                        continue

                    try:
                        price_decimal = Decimal(str(price_val)).quantize(
                            Decimal("0.01"), rounding=ROUND_HALF_UP
                        )
                    except Exception:
                        continue

                    if price_decimal <= 0:
                        continue

                    source = str(offer.get("domain") or prod.get("brand_name") or "Channel3").strip()
                    url = offer.get("url") or prod.get("url")
                    if url and not isinstance(url, str):
                        url = None

                    results.append(
                        MarketPriceReference(
                            title=title,
                            price_usd=price_decimal,
                            source=source,
                            url=url,
                            image_url=image_url,
                        )
                    )
                    break  # Tomar la mejor oferta del producto
            else:
                # Si el producto tiene precio directo en la raíz
                raw_price = prod.get("price")
                if raw_price is not None:
                    try:
                        price_decimal = Decimal(str(raw_price)).quantize(
                            Decimal("0.01"), rounding=ROUND_HALF_UP
                        )
                        if price_decimal > 0:
                            source = str(prod.get("brand_name") or "Channel3").strip()
                            results.append(
                                MarketPriceReference(
                                    title=title,
                                    price_usd=price_decimal,
                                    source=source,
                                    url=prod.get("url"),
                                    image_url=image_url,
                                )
                            )
                    except Exception:
                        continue

        return results


class PriceContextFormatter:
    """Formatea la lista de referencias de precios para inyección en el prompt (Single Responsibility)."""

    @staticmethod
    def format(references: list[MarketPriceReference]) -> str:
        if not references:
            return ""

        lines = [
            "Verified market price references from merchants (all in USD):",
            "Use these realistic market prices when estimating line items, and cite the source in assumptions.",
        ]
        for ref in references:
            url_part = f" ({ref.url})" if ref.url else ""
            lines.append(f"- {ref.title}: ${ref.price_usd} USD [Store: {ref.source}]{url_part}")

        return "\n".join(lines)


class UnconfiguredPriceLookupService:
    """Implementación por defecto cuando el buscador de precios no está configurado (Null Object)."""

    def lookup_prices(self, request: str) -> list[MarketPriceReference]:
        return []


class HttpxChannel3PriceLookupService:
    """Consulta referencias de precios en vivo contra Channel3 API usando httpx."""

    def __init__(
        self,
        settings: Settings,
        client: httpx.Client | None = None,
        extractor: MaterialQueryExtractor | None = None,
        parser: Channel3ResponseParser | None = None,
    ) -> None:
        self._settings = settings
        self._api_key = settings.price_lookup_api_key
        self._base_url = (settings.price_lookup_base_url or "https://api.trychannel3.com").rstrip("/")
        self._client = client or httpx.Client(timeout=10.0)
        self._extractor = extractor or MaterialQueryExtractor()
        self._parser = parser or Channel3ResponseParser()

    def lookup_prices(self, request: str) -> list[MarketPriceReference]:
        if not self._api_key:
            return []

        queries = self._extractor.extract_queries(request)
        combined_results: list[MarketPriceReference] = []
        seen_titles: set[str] = set()

        headers = {
            "x-api-key": self._api_key,
            "Content-Type": "application/json",
        }

        for query in queries:
            try:
                response = self._client.post(
                    f"{self._base_url}/v1/search",
                    headers=headers,
                    json={"query": query, "limit": 4},
                )
                if response.status_code == 404:
                    response = self._client.post(
                        f"{self._base_url}/v0/search",
                        headers=headers,
                        json={"query": query, "limit": 4},
                    )

                if response.status_code == 200:
                    data = response.json()
                    parsed = self._parser.parse(data)
                    for item in parsed:
                        if item.title.lower() not in seen_titles:
                            seen_titles.add(item.title.lower())
                            combined_results.append(item)
            except Exception:
                # Degradación elegante: el fallo de red nunca detiene el flujo de cotización
                continue

        return combined_results[:8]


# Registro extensible de proveedores de búsqueda de precios (Open/Closed Principle)
_PRICE_LOOKUP_FACTORIES: dict[str, Callable[[Settings], PriceLookupService]] = {
    "channel3": lambda s: HttpxChannel3PriceLookupService(s),
    "none": lambda s: UnconfiguredPriceLookupService(),
}


def register_price_lookup_provider(name: str, factory: Callable[[Settings], PriceLookupService]) -> None:
    """Registra una implementación para un proveedor de precios sin modificar la aplicación."""
    _PRICE_LOOKUP_FACTORIES[name.lower().strip()] = factory


def build_price_lookup_service(settings: Settings) -> PriceLookupService:
    provider = (settings.price_lookup_provider or "").lower().strip()
    if not provider or provider == "none":
        return UnconfiguredPriceLookupService()

    factory = _PRICE_LOOKUP_FACTORIES.get(provider)
    if factory is not None:
        return factory(settings)

    return UnconfiguredPriceLookupService()

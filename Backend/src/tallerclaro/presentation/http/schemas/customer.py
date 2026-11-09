"""Esquemas HTTP para la recuperación autorizada del cliente."""

from pydantic import BaseModel, Field

from tallerclaro.presentation.http.schemas.orders import OrderResponse
from tallerclaro.presentation.http.schemas.payments import PaymentResponse
from tallerclaro.presentation.http.schemas.quotes import QuoteResponse


class CustomerContextResponse(BaseModel):
    """Recursos vinculados al token de cliente válido."""

    quote: QuoteResponse
    order: OrderResponse | None = None
    payments: list[PaymentResponse] = Field(default_factory=list)


class ReissueAccessResponse(BaseModel):
    """Nuevo enlace de acceso; solo el taller autenticado puede solicitarlo."""

    quote_id: str
    customer_token: str

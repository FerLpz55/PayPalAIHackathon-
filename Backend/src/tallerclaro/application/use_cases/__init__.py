"""Casos de uso de la aplicación."""

from tallerclaro.application.use_cases.orders import GetOrder, ListOrders, UpdateOrder
from tallerclaro.application.use_cases.payments import CapturePayment, CreateOrderPayment, GetPayment
from tallerclaro.application.use_cases.quotes import (
    ApproveQuote,
    CreateQuote,
    GenerateQuoteProposal,
    GetQuote,
    RejectQuote,
)

__all__ = [
    "CreateQuote",
    "GetQuote",
    "GenerateQuoteProposal",
    "ApproveQuote",
    "RejectQuote",
    "ListOrders",
    "GetOrder",
    "UpdateOrder",
    "CreateOrderPayment",
    "CapturePayment",
    "GetPayment",
]

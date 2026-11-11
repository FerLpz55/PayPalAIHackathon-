"""Casos de uso de la aplicación."""

from tallerclaro.application.use_cases.accounting import AskAccountingAssistant, GetWorkshopFinancialSummary
from tallerclaro.application.use_cases.orders import GetOrder, ListOrders, UpdateOrder
from tallerclaro.application.use_cases.payments import CapturePayment, CreateOrderPayment, GetPayment
from tallerclaro.application.use_cases.quotes import (
    ApproveQuote,
    CreateQuote,
    GenerateQuoteProposal,
    GetQuote,
    ListQuotes,
    RejectQuote,
    VerifyCustomerToken,
)

__all__ = [
    "GetWorkshopFinancialSummary",
    "AskAccountingAssistant",
    "CreateQuote",
    "GetQuote",
    "ListQuotes",
    "GenerateQuoteProposal",
    "ApproveQuote",
    "RejectQuote",
    "VerifyCustomerToken",
    "ListOrders",
    "GetOrder",
    "UpdateOrder",
    "CreateOrderPayment",
    "CapturePayment",
    "GetPayment",
]

"""Casos de uso de la aplicación."""

from tallerclaro.application.use_cases.accounting import AskAccountingAssistant, GetWorkshopFinancialSummary
from tallerclaro.application.use_cases.authorization import (
    EndWorkshopSession,
    ResolveWorkshopSession,
    StartWorkshopSession,
)
from tallerclaro.application.use_cases.orders import GetOrder, ListOrders, UpdateOrder
from tallerclaro.application.use_cases.payment_reconciliation import (
    HandlePayPalWebhook,
    ReconcileStalePayments,
)
from tallerclaro.application.use_cases.payments import (
    CancelPayment,
    CapturePayment,
    CreateOrderPayment,
    GetPayment,
    SyncPayment,
)
from tallerclaro.application.use_cases.quotes import (
    ApproveQuote,
    CreateQuote,
    GenerateQuoteProposal,
    GetCustomerContext,
    GetQuote,
    ListQuotes,
    ReissueCustomerAccess,
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
    "StartWorkshopSession",
    "ResolveWorkshopSession",
    "EndWorkshopSession",
    "GetCustomerContext",
    "ReissueCustomerAccess",
    "ListOrders",
    "GetOrder",
    "UpdateOrder",
    "CreateOrderPayment",
    "CapturePayment",
    "GetPayment",
    "SyncPayment",
    "CancelPayment",
    "HandlePayPalWebhook",
    "ReconcileStalePayments",
]

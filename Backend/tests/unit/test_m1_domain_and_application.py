"""Pruebas unitarias de Dominio y Aplicación para Milestone 1 (R1 & R2)."""

from decimal import Decimal

import pytest

from tallerclaro.application.dtos import (
    AccessPrincipal,
    CreatedQuoteResult,
    CreateQuoteInput,
    CustomerInput,
    OrderDetailResult,
    QuoteLineItemInput,
    QuoteProposalResult,
    UpdateOrderInput,
)
from tallerclaro.application.exceptions import (
    ConflictError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    ValidationDomainError,
)
from tallerclaro.application.use_cases import (
    ApproveQuote,
    CapturePayment,
    CreateOrderPayment,
    CreateQuote,
    GenerateQuoteProposal,
    GetOrder,
    GetPayment,
    GetQuote,
    RejectQuote,
    UpdateOrder,
)
from tallerclaro.domain.entities import (
    ORDER_STATUS_IN_PROGRESS,
    ORDER_STATUS_PAID,
    ORDER_STATUS_PENDING,
    QUOTE_STATUS_APPROVED,
    QUOTE_STATUS_DRAFT,
    QUOTE_STATUS_NEEDS_INFORMATION,
    QUOTE_STATUS_PENDING_REVIEW,
    Carpenter,
    CarpenterId,
    CustomerId,
    Money,
    Order,
    OrderId,
    Payment,
    PaymentId,
    Quote,
    QuoteId,
    QuoteLineItem,
)
from tests.fakes import FakeAIService, FakePaymentProcessor, FakeUnitOfWork


def test_forbidden_error_properties():
    err = ForbiddenError("Access denied")
    assert err.code == "FORBIDDEN"
    assert err.message == "Access denied"
    assert isinstance(err, DomainError)

    default_err = ForbiddenError()
    assert default_err.code == "FORBIDDEN"
    assert default_err.message == "Forbidden"


def test_quote_entity_clarification_and_assumptions():
    quote = Quote(
        id=QuoteId(1),
        customer_id=CustomerId(1),
        carpenter_id=CarpenterId(1),
        request="Mesa de comedor",
        description=None,
        line_items=[
            QuoteLineItem(
                id=None,
                type="material",
                description="Pino",
                unit="tablón",
                quantity=Decimal("3"),
                unit_price=Money(Decimal("50")),
            )
        ],
        total=Money(Decimal("150")),
        status=QUOTE_STATUS_DRAFT,
    )
    assert quote.assumptions == []
    assert quote.missing_info == []

    # Marcar que requiere información
    quote.mark_needs_information(["Dimensiones largo x ancho", "Tipo de acabado"])
    assert quote.status == QUOTE_STATUS_NEEDS_INFORMATION
    assert quote.missing_info == ["Dimensiones largo x ancho", "Tipo de acabado"]

    # Asignar supuestos y enviar a revisión
    quote.assumptions = ["Madera de pino tratada", "Barniz mate"]
    quote.submit_for_review()
    assert quote.status == QUOTE_STATUS_PENDING_REVIEW
    assert quote.missing_info == []
    assert quote.assumptions == ["Madera de pino tratada", "Barniz mate"]


def test_access_principal_dtos():
    cust_p = AccessPrincipal(kind="customer", customer_id=CustomerId(10), quote_id=QuoteId(20))
    assert cust_p.is_customer is True
    assert cust_p.is_workshop is False
    assert cust_p.role == "customer"
    assert cust_p.customer_id == 10
    assert cust_p.quote_id == 20

    work_p = AccessPrincipal(kind="workshop", carpenter_id=CarpenterId(5))
    assert work_p.is_customer is False
    assert work_p.is_workshop is True
    assert work_p.role == "workshop"
    assert work_p.carpenter_id == 5


def test_fake_customer_token_repository():
    uow = FakeUnitOfWork()
    with uow:
        token = uow.tokens.create(CustomerId(1), QuoteId(100))
        uow.commit()
    assert token.startswith("fake-token-")
    with uow:
        verified = uow.tokens.verify(token)
    assert verified == (CustomerId(1), QuoteId(100))
    with uow:
        assert uow.tokens.verify("non-existent-token") is None


def test_create_quote_normalization_and_token():
    uow = FakeUnitOfWork()
    with uow:
        uow.carpenters.seed(
            Carpenter(id=CarpenterId(1), name="José", workshop_name="Taller", email="j@example.com", phone=None)
        )
        uow.commit()
    use_case = CreateQuote(uow)
    result = use_case.execute(
        CreateQuoteInput(
            customer=CustomerInput(name="  María López  ", email=" Maria.Lopez@EXample.com ", phone=" +502 12345678 "),
            carpenter_id=CarpenterId(1),
            request="Estante flotante",
        )
    )
    assert isinstance(result, CreatedQuoteResult)
    assert result.quote.id is not None
    assert result.customer_token.startswith("fake-token-")

    # Verificar que el token se asocia al cliente y cotización
    with uow:
        verified = uow.tokens.verify(result.customer_token)
    assert verified == (result.quote.customer_id, result.quote.id)

    # Verificar normalización
    with uow:
        saved_customer = uow.customers.get_by_id(result.quote.customer_id)
    assert saved_customer.name == "María López"
    assert saved_customer.email == "maria.lopez@example.com"
    assert saved_customer.phone == "+502 12345678"


def test_get_quote_authorization():
    uow = FakeUnitOfWork()
    with uow:
        uow.carpenters.seed(
            Carpenter(id=CarpenterId(1), name="José", workshop_name="Taller 1", email="j@example.com", phone=None)
        )
        uow.commit()
    with uow:
        uow.carpenters.seed(
            Carpenter(id=CarpenterId(2), name="Pedro", workshop_name="Taller 2", email="p@example.com", phone=None)
        )
        uow.commit()
    created = CreateQuote(uow).execute(
        CreateQuoteInput(
            customer=CustomerInput(name="Carlos", email="carlos@example.com", phone=None),
            carpenter_id=CarpenterId(1),
            request="Silla",
        )
    )
    quote_id = created.quote.id

    # Workshop propio accede
    quote = GetQuote(uow).execute(
        quote_id, AccessPrincipal(kind="workshop", carpenter_id=CarpenterId(1))
    )
    assert quote.id == quote_id

    # Workshop ajeno recibe ForbiddenError
    with pytest.raises(ForbiddenError):
        GetQuote(uow).execute(
            quote_id, AccessPrincipal(kind="workshop", carpenter_id=CarpenterId(2))
        )

    # Cliente propietario accede
    quote = GetQuote(uow).execute(
        quote_id, AccessPrincipal(kind="customer", quote_id=quote_id)
    )
    assert quote.id == quote_id

    # Cliente ajeno recibe ForbiddenError
    with pytest.raises(ForbiddenError):
        GetQuote(uow).execute(
            quote_id, AccessPrincipal(kind="customer", quote_id=QuoteId(9999))
        )


def test_approve_and_reject_quote_authorization():
    uow = FakeUnitOfWork()
    with uow:
        uow.carpenters.seed(
            Carpenter(id=CarpenterId(1), name="José", workshop_name="Taller 1", email="j@example.com", phone=None)
        )
        uow.commit()
    created = CreateQuote(uow).execute(
        CreateQuoteInput(
            customer=CustomerInput(name="Carlos", email="carlos@example.com", phone=None),
            carpenter_id=CarpenterId(1),
            request="Mesa",
        )
    )
    quote_id = created.quote.id
    GenerateQuoteProposal(uow, FakeAIService()).execute(quote_id)

    # Intento de aprobación por cliente ajeno -> ForbiddenError
    with pytest.raises(ForbiddenError):
        ApproveQuote(uow).execute(
            quote_id, AccessPrincipal(kind="customer", quote_id=QuoteId(888))
        )

    # Aprobación por taller propio -> éxito
    order = ApproveQuote(uow).execute(
        quote_id, AccessPrincipal(kind="workshop", carpenter_id=CarpenterId(1))
    )
    assert order.quote_id == quote_id

    # Crear otra cotización para prueba de rechazo
    created2 = CreateQuote(uow).execute(
        CreateQuoteInput(
            customer=CustomerInput(name="Ana", email="ana@example.com", phone=None),
            carpenter_id=CarpenterId(1),
            request="Banco",
        )
    )
    quote_id2 = created2.quote.id
    GenerateQuoteProposal(uow, FakeAIService()).execute(quote_id2)

    # Rechazo por cliente ajeno -> ForbiddenError
    with pytest.raises(ForbiddenError):
        RejectQuote(uow).execute(
            quote_id2, AccessPrincipal(kind="customer", quote_id=QuoteId(888))
        )

    # Rechazo por cliente propio -> éxito
    rejected = RejectQuote(uow).execute(
        quote_id2, AccessPrincipal(kind="customer", quote_id=quote_id2)
    )
    assert rejected.status == "rejected"


def test_generate_quote_proposal_needs_information_and_additional_info():
    uow = FakeUnitOfWork()
    with uow:
        uow.carpenters.seed(
            Carpenter(id=CarpenterId(1), name="José", workshop_name="Taller", email="j@example.com", phone=None)
        )
        uow.commit()
    created = CreateQuote(uow).execute(
        CreateQuoteInput(
            customer=CustomerInput(name="Carlos", email="carlos@example.com", phone=None),
            carpenter_id=CarpenterId(1),
            request="Quiero un mueble para sala",
        )
    )
    quote_id = created.quote.id

    # 1. IA responde que necesita información
    ai_needs_info = FakeAIService(
        proposal=QuoteProposalResult(
            description="",
            line_items=[],
            needs_information=True,
            missing_info=["Medidas del espacio", "Tipo de madera preferida"],
        )
    )
    quote = GenerateQuoteProposal(uow, ai_needs_info).execute(quote_id)
    assert quote.status == QUOTE_STATUS_NEEDS_INFORMATION
    assert quote.missing_info == ["Medidas del espacio", "Tipo de madera preferida"]

    # 2. Cliente envía additional_info para aclarar
    ai_complete = FakeAIService(
        proposal=QuoteProposalResult(
            description="Mueble de sala en cedro",
            line_items=[
                QuoteLineItemInput(
                    type="material",
                    description="Madera de cedro",
                    unit="m2",
                    quantity=Decimal("4"),
                    unit_price=Decimal("80"),
                ),
                QuoteLineItemInput(
                    type="labor",
                    description="Fabricación y ensamble",
                    unit="servicio",
                    quantity=Decimal("1"),
                    unit_price=Decimal("150"),
                ),
            ],
            assumptions=["Acabado con sellador poliuretano", "Incluye tiradores estándar"],
        )
    )
    updated_quote = GenerateQuoteProposal(uow, ai_complete).execute(
        quote_id, additional_info="El espacio mide 2x1 metros y prefiero madera de cedro."
    )
    assert updated_quote.status == QUOTE_STATUS_PENDING_REVIEW
    assert "Información adicional: El espacio mide 2x1 metros" in updated_quote.request
    assert updated_quote.missing_info == []
    assert updated_quote.assumptions == ["Acabado con sellador poliuretano", "Incluye tiradores estándar"]
    assert updated_quote.total.amount == Decimal("470.00")


def test_get_order_authorization_and_details():
    uow = FakeUnitOfWork()
    with uow:
        uow.carpenters.seed(
            Carpenter(id=CarpenterId(1), name="José", workshop_name="Taller 1", email="j@example.com", phone=None)
        )
        uow.commit()
    created = CreateQuote(uow).execute(
        CreateQuoteInput(
            customer=CustomerInput(name="Carlos Gómez", email="carlos@example.com", phone=None),
            carpenter_id=CarpenterId(1),
            request="Escritorio moderno",
        )
    )
    quote_id = created.quote.id
    GenerateQuoteProposal(uow, FakeAIService()).execute(quote_id)
    order = ApproveQuote(uow).execute(
        quote_id, AccessPrincipal(kind="customer", quote_id=quote_id)
    )

    # Cliente propio consulta orden
    detail = GetOrder(uow).execute(
        order.id, AccessPrincipal(kind="customer", quote_id=quote_id)
    )
    assert isinstance(detail, OrderDetailResult)
    assert detail.order.id == order.id
    assert detail.customer_name == "Carlos Gómez"
    assert detail.customer_email == "carlos@example.com"
    assert detail.project_request == "Escritorio moderno"
    assert detail.payments == []

    # Cliente ajeno recibe ForbiddenError
    with pytest.raises(ForbiddenError):
        GetOrder(uow).execute(
            order.id, AccessPrincipal(kind="customer", quote_id=QuoteId(444))
        )

    # Taller ajeno recibe ForbiddenError
    with pytest.raises(ForbiddenError):
        GetOrder(uow).execute(
            order.id, AccessPrincipal(kind="workshop", carpenter_id=CarpenterId(99))
        )

    # Taller propio consulta orden
    detail_ws = GetOrder(uow).execute(
        order.id, AccessPrincipal(kind="workshop", carpenter_id=CarpenterId(1))
    )
    assert detail_ws.order.id == order.id


def test_update_order_carpenter_authorization():
    uow = FakeUnitOfWork()
    with uow:
        uow.carpenters.seed(
            Carpenter(id=CarpenterId(1), name="José", workshop_name="Taller 1", email="j@example.com", phone=None)
        )
        uow.commit()
    created = CreateQuote(uow).execute(
        CreateQuoteInput(
            customer=CustomerInput(name="Carlos", email="carlos@example.com", phone=None),
            carpenter_id=CarpenterId(1),
            request="Mesa",
        )
    )
    GenerateQuoteProposal(uow, FakeAIService()).execute(created.quote.id)
    order = ApproveQuote(uow).execute(
        created.quote.id, AccessPrincipal(kind="workshop", carpenter_id=CarpenterId(1))
    )

    # Carpintero ajeno intenta actualizar -> ForbiddenError
    with pytest.raises(ForbiddenError):
        UpdateOrder(uow).execute(
            order.id,
            carpenter_id=CarpenterId(99),
            input=UpdateOrderInput(status="in_progress"),
        )

    # Carpintero propio actualiza con éxito
    updated = UpdateOrder(uow).execute(
        order.id,
        carpenter_id=CarpenterId(1),
        input=UpdateOrderInput(status="in_progress"),
    )
    assert updated.status == "in_progress"


def test_payments_authorization_and_capture_id():
    uow = FakeUnitOfWork()
    with uow:
        uow.carpenters.seed(
            Carpenter(id=CarpenterId(1), name="José", workshop_name="Taller 1", email="j@example.com", phone=None)
        )
        uow.commit()
    created = CreateQuote(uow).execute(
        CreateQuoteInput(
            customer=CustomerInput(name="Carlos", email="carlos@example.com", phone=None),
            carpenter_id=CarpenterId(1),
            request="Mesa",
        )
    )
    quote_id = created.quote.id
    GenerateQuoteProposal(uow, FakeAIService()).execute(quote_id)
    order = ApproveQuote(uow).execute(
        quote_id, AccessPrincipal(kind="customer", quote_id=quote_id)
    )

    processor = FakePaymentProcessor(success=True)

    # 1. CreateOrderPayment: cliente ajeno -> ForbiddenError
    with pytest.raises(ForbiddenError):
        CreateOrderPayment(uow, processor).execute(
            order.id, "deposit", authorized_quote_id=QuoteId(888)
        )

    # CreateOrderPayment: cliente autorizado -> éxito
    intent = CreateOrderPayment(uow, processor).execute(
        order.id, "deposit", authorized_quote_id=quote_id
    )
    assert intent.payment_id is not None

    # 2. CapturePayment: cliente ajeno -> ForbiddenError
    with pytest.raises(ForbiddenError):
        CapturePayment(uow, processor).execute(
            intent.payment_id, authorized_quote_id=QuoteId(888)
        )

    # CapturePayment: cliente autorizado -> éxito y payment_id coincide con el persistido
    captured = CapturePayment(uow, processor).execute(
        intent.payment_id, authorized_quote_id=quote_id
    )
    assert captured.status == "completed"
    assert captured.payment_id == intent.payment_id

    # 3. GetPayment: cliente ajeno -> ForbiddenError
    with pytest.raises(ForbiddenError):
        GetPayment(uow).execute(
            intent.payment_id, authorized_quote_id=QuoteId(888)
        )

    # GetPayment: cliente autorizado -> éxito
    payment = GetPayment(uow).execute(
        intent.payment_id, authorized_quote_id=quote_id
    )
    assert payment.id == intent.payment_id
    assert payment.status == "completed"


def test_create_quote_whitespace_phone_normalizes_to_none():
    uow = FakeUnitOfWork()
    with uow:
        uow.carpenters.seed(
            Carpenter(id=CarpenterId(1), name="José", workshop_name="Taller", email="j@example.com", phone=None)
        )
        uow.commit()
    res = CreateQuote(uow).execute(
        CreateQuoteInput(
            customer=CustomerInput(name="Juan", email="juan@example.com", phone="   \t   "),
            carpenter_id=CarpenterId(1),
            request="Mesa de centro",
        )
    )
    with uow:
        saved_cust = uow.customers.get_by_id(res.quote.customer_id)
    assert saved_cust.phone is None


def test_quote_mark_needs_information_clears_assumptions():
    quote = Quote(
        id=QuoteId(1),
        customer_id=CustomerId(1),
        carpenter_id=CarpenterId(1),
        request="Mesa",
        description="Mesa de cedro",
        line_items=[],
        total=Money(Decimal("200")),
        status=QUOTE_STATUS_PENDING_REVIEW,
        assumptions=["Madera tratada", "Barniz natural"],
        missing_info=[],
    )
    assert len(quote.assumptions) == 2
    quote.mark_needs_information(["Tipo de madera exacta"])
    assert quote.status == QUOTE_STATUS_NEEDS_INFORMATION
    assert quote.assumptions == []
    assert quote.missing_info == ["Tipo de madera exacta"]


def test_payment_capture_when_order_in_progress_does_not_crash():
    uow = FakeUnitOfWork()
    with uow:
        uow.carpenters.seed(
            Carpenter(id=CarpenterId(1), name="José", workshop_name="Taller", email="j@example.com", phone=None)
        )
        uow.commit()
    created = CreateQuote(uow).execute(
        CreateQuoteInput(
            customer=CustomerInput(name="Ana", email="ana@example.com", phone="12345678"),
            carpenter_id=CarpenterId(1),
            request="Mesa comedor",
        )
    )
    qid = created.quote.id
    GenerateQuoteProposal(uow, FakeAIService()).execute(qid)
    order = ApproveQuote(uow).execute(qid, AccessPrincipal(kind="customer", quote_id=qid))

    processor = FakePaymentProcessor(success=True)
    # Pagar anticipo
    dep_intent = CreateOrderPayment(uow, processor).execute(order.id, "deposit", authorized_quote_id=qid)
    CapturePayment(uow, processor).execute(dep_intent.payment_id, authorized_quote_id=qid)

    # Al confirmarse el anticipo el pedido pasa solo a in_progress
    with uow:
        order_in_prog = uow.orders.get_by_id(order.id)
    assert order_in_prog.status == ORDER_STATUS_IN_PROGRESS

    # Cliente paga saldo mientras está in_progress
    bal_intent = CreateOrderPayment(uow, processor).execute(order.id, "balance", authorized_quote_id=qid)
    captured = CapturePayment(uow, processor).execute(bal_intent.payment_id, authorized_quote_id=qid)
    assert captured.status == "completed"

    with uow:
        order_final = uow.orders.get_by_id(order.id)
    assert order_final.status == ORDER_STATUS_IN_PROGRESS


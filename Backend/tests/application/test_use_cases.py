"""Pruebas de casos de uso."""

from decimal import Decimal

import pytest

from tallerclaro.application.dtos import CreateQuoteInput, CustomerInput, UpdateOrderInput
from tallerclaro.application.exceptions import ConflictError, NotFoundError
from tallerclaro.application.use_cases import (
    ApproveQuote,
    CapturePayment,
    CreateOrderPayment,
    CreateQuote,
    GenerateQuoteProposal,
    GetOrder,
    ListOrders,
    RejectQuote,
    UpdateOrder,
)
from tallerclaro.domain.entities import (
    ORDER_STATUS_DELIVERED,
    ORDER_STATUS_IN_PROGRESS,
    ORDER_STATUS_PAID,
    ORDER_STATUS_PENDING,
    QUOTE_STATUS_PENDING_REVIEW,
    Carpenter,
    CarpenterId,
    CustomerId,
    Money,
    Order,
    OrderId,
    Payment,
    QuoteId,
)
from tallerclaro.domain.value_objects import Money as MoneyVO
from tests.fakes import FakeAIService, FakePaymentProcessor, FakeUnitOfWork


def test_create_quote():
    uow = FakeUnitOfWork()
    with uow:
        uow.carpenters.seed(Carpenter(id=CarpenterId(1), name="José", workshop_name="Taller", email="j@example.com", phone=None))
        uow.commit()
    use_case = CreateQuote(uow)
    quote = use_case.execute(
        CreateQuoteInput(
            customer=CustomerInput(name="Carlos", email="carlos@example.com", phone=None),
            carpenter_id=1,
            request="Mesa de centro",
        )
    )
    assert quote.id is not None
    assert quote.status == "draft"


def test_generate_quote_proposal():
    uow = FakeUnitOfWork()
    with uow:
        uow.carpenters.seed(Carpenter(id=CarpenterId(1), name="José", workshop_name="Taller", email="j@example.com", phone=None))
        uow.commit()
    create = CreateQuote(uow)
    quote = create.execute(
        CreateQuoteInput(
            customer=CustomerInput(name="Carlos", email="carlos@example.com", phone=None),
            carpenter_id=1,
            request="Mesa",
        )
    )
    ai = FakeAIService()
    use_case = GenerateQuoteProposal(uow, ai)
    result = use_case.execute(quote.id)
    assert result.status == QUOTE_STATUS_PENDING_REVIEW
    assert result.total.amount == Decimal("200.00")


def test_generate_quote_rejects_changes_during_ai_call():
    uow = FakeUnitOfWork()
    with uow:
        uow.carpenters.seed(Carpenter(id=CarpenterId(1), name="José", workshop_name="Taller", email="j@example.com", phone=None))
        uow.commit()
    quote = CreateQuote(uow).execute(CreateQuoteInput(customer=CustomerInput(name="Carlos", email="carlos@example.com", phone=None), carpenter_id=1, request="Mesa"))

    class ConcurrentAI(FakeAIService):
        def generate_quote_proposal(self, request):
            with uow:
                current = uow.quotes.get_by_id(quote.id)
                current.request = "Mesa modificada"
                uow.quotes.save(current)
                uow.commit()
            return super().generate_quote_proposal(request)

    with pytest.raises(ConflictError, match="changed"):
        GenerateQuoteProposal(uow, ConcurrentAI()).execute(quote.id)


def test_create_payment_rejects_amount_change_during_provider_call():
    uow = FakeUnitOfWork()
    with uow:
        order = uow.orders.save(Order(id=None, quote_id=QuoteId(1), carpenter_id=CarpenterId(1), code="TC-1", total=Money("200"), deposit_amount=Money("100"), currency="USD", status=ORDER_STATUS_PENDING, created_at=None, updated_at=None))
        uow.commit()

    class ChangingProcessor(FakePaymentProcessor):
        def create_order(self, amount, currency, request_id=None):
            intent = super().create_order(amount, currency, request_id)
            with uow:
                changed = uow.orders.get_by_id(order.id)
                changed.deposit_amount = Money("90")
                uow.orders.save(changed)
                uow.commit()
            return intent

    with pytest.raises(ConflictError, match="changed"):
        CreateOrderPayment(uow, ChangingProcessor()).execute(order.id, "deposit")


def test_uncertain_capture_blocks_other_payment_until_reconciled():
    uow = FakeUnitOfWork()
    with uow:
        order = uow.orders.save(Order(id=None, quote_id=QuoteId(1), carpenter_id=CarpenterId(1), code="TC-1", total=Money("200"), deposit_amount=Money("100"), currency="USD", status=ORDER_STATUS_PENDING, created_at=None, updated_at=None))
        uow.commit()
    processor = FakePaymentProcessor()
    first = CreateOrderPayment(uow, processor).execute(order.id, "deposit")
    second = CreateOrderPayment(uow, processor).execute(order.id, "balance")

    class UncertainProcessor:
        def capture_order(self, paypal_order_id):
            raise RuntimeError("timeout")

    with pytest.raises(RuntimeError, match="timeout"):
        CapturePayment(uow, UncertainProcessor()).execute(first.payment_id)
    with pytest.raises(ConflictError, match="capture"):
        CapturePayment(uow, processor).execute(second.payment_id)


def test_capture_recovers_after_local_commit_failure():
    class FailingCommitUow(FakeUnitOfWork):
        fail_next_commit = False

        def commit(self):
            if self.fail_next_commit:
                self.fail_next_commit = False
                raise RuntimeError("commit failed")
            return super().commit()

    uow = FailingCommitUow()
    with uow:
        order = uow.orders.save(Order(id=None, quote_id=QuoteId(1), carpenter_id=CarpenterId(1), code="TC-1", total=Money("200"), deposit_amount=Money("100"), currency="USD", status=ORDER_STATUS_PENDING, created_at=None, updated_at=None))
        uow.commit()

    class CapturingProcessor(FakePaymentProcessor):
        fail_once = True

        def capture_order(self, paypal_order_id):
            result = super().capture_order(paypal_order_id)
            if self.fail_once:
                self.fail_once = False
                uow.fail_next_commit = True
            return result

    processor = CapturingProcessor()
    intent = CreateOrderPayment(uow, processor).execute(order.id, "deposit")
    with pytest.raises(RuntimeError, match="commit failed"):
        CapturePayment(uow, processor).execute(intent.payment_id)
    with uow:
        assert uow.payments.get_by_id(intent.payment_id).status == "pending"
    result = CapturePayment(uow, processor).execute(intent.payment_id)
    assert result.status == "completed"
    with uow:
        assert len([p for p in uow.payments.list_by_order(order.id) if p.status == "completed"]) == 1


def test_approve_quote_creates_order_idempotently():
    uow = FakeUnitOfWork()
    with uow:
        uow.carpenters.seed(Carpenter(id=CarpenterId(1), name="José", workshop_name="Taller", email="j@example.com", phone=None))
        uow.commit()
    create = CreateQuote(uow)
    quote = create.execute(
        CreateQuoteInput(
            customer=CustomerInput(name="Carlos", email="carlos@example.com", phone=None),
            carpenter_id=1,
            request="Mesa",
        )
    )
    GenerateQuoteProposal(uow, FakeAIService()).execute(quote.id)
    use_case = ApproveQuote(uow)
    order1 = use_case.execute(quote.id)
    order2 = use_case.execute(quote.id)
    assert order1.id == order2.id
    assert order1.deposit_amount.amount == Decimal("100.00")


def test_reject_quote_not_pending_review_fails():
    uow = FakeUnitOfWork()
    with uow:
        uow.carpenters.seed(Carpenter(id=CarpenterId(1), name="José", workshop_name="Taller", email="j@example.com", phone=None))
        uow.commit()
    quote = CreateQuote(uow).execute(
        CreateQuoteInput(
            customer=CustomerInput(name="Carlos", email="carlos@example.com", phone=None),
            carpenter_id=1,
            request="Mesa",
        )
    )
    with pytest.raises(ConflictError):
        RejectQuote(uow).execute(quote.id)


def test_create_payment_and_capture():
    uow = FakeUnitOfWork()
    with uow:
        uow.carpenters.seed(Carpenter(id=CarpenterId(1), name="José", workshop_name="Taller", email="j@example.com", phone=None))
        uow.commit()
    quote = CreateQuote(uow).execute(
        CreateQuoteInput(
            customer=CustomerInput(name="Carlos", email="carlos@example.com", phone=None),
            carpenter_id=1,
            request="Mesa",
        )
    )
    GenerateQuoteProposal(uow, FakeAIService()).execute(quote.id)
    order = ApproveQuote(uow).execute(quote.id)

    processor = FakePaymentProcessor(success=True)
    deposit_intent = CreateOrderPayment(uow, processor).execute(order.id, "deposit")
    assert deposit_intent.amount == Decimal("100.00")

    CapturePayment(uow, processor).execute(deposit_intent.payment_id)
    updated = GetOrder(uow).execute(order.id)
    assert updated.status == ORDER_STATUS_PENDING

    balance_intent = CreateOrderPayment(uow, processor).execute(order.id, "balance")
    assert balance_intent.amount == Decimal("100.00")
    CapturePayment(uow, processor).execute(balance_intent.payment_id)

    updated = GetOrder(uow).execute(order.id)
    assert updated.status == ORDER_STATUS_PAID


def test_capture_duplicate_returns_existing():
    uow = FakeUnitOfWork()
    with uow:
        uow.carpenters.seed(Carpenter(id=CarpenterId(1), name="José", workshop_name="Taller", email="j@example.com", phone=None))
        uow.commit()
    quote = CreateQuote(uow).execute(
        CreateQuoteInput(
            customer=CustomerInput(name="Carlos", email="carlos@example.com", phone=None),
            carpenter_id=1,
            request="Mesa",
        )
    )
    GenerateQuoteProposal(uow, FakeAIService()).execute(quote.id)
    order = ApproveQuote(uow).execute(quote.id)
    processor = FakePaymentProcessor(success=True)
    intent = CreateOrderPayment(uow, processor).execute(order.id, "deposit")
    CapturePayment(uow, processor).execute(intent.payment_id)
    captured2 = CapturePayment(uow, processor).execute(intent.payment_id)
    assert captured2.status == "completed"


def test_cannot_deliver_unpaid_order():
    uow = FakeUnitOfWork()
    with uow:
        uow.carpenters.seed(Carpenter(id=CarpenterId(1), name="José", workshop_name="Taller", email="j@example.com", phone=None))
        uow.commit()
    quote = CreateQuote(uow).execute(
        CreateQuoteInput(
            customer=CustomerInput(name="Carlos", email="carlos@example.com", phone=None),
            carpenter_id=1,
            request="Mesa",
        )
    )
    GenerateQuoteProposal(uow, FakeAIService()).execute(quote.id)
    order = ApproveQuote(uow).execute(quote.id)
    with uow:
        uow.orders.save(Order(
            id=order.id,
            quote_id=order.quote_id,
            carpenter_id=order.carpenter_id,
            code=order.code,
            total=order.total,
            deposit_amount=order.deposit_amount,
            currency=order.currency,
            status=ORDER_STATUS_IN_PROGRESS,
            created_at=order.created_at,
            updated_at=order.updated_at,
        ))
        uow.commit()
    with pytest.raises(ConflictError):
        UpdateOrder(uow).execute(order.id, UpdateOrderInput(status=ORDER_STATUS_DELIVERED))


def test_postgres_uow_interleaved_operations_do_not_leak_connections():
    """Verify interleaving/nesting PostgresUnitOfWork never overwrites or leaks a connection."""
    from tallerclaro.infrastructure.db.unit_of_work import PostgresUnitOfWork

    class FakeConn:
        def __init__(self, cid: int) -> None:
            self.cid = cid
            self.committed = 0
            self.rolled_back = 0

        def commit(self) -> None:
            self.committed += 1

        def rollback(self) -> None:
            self.rolled_back += 1

    class FakeDatabase:
        def __init__(self) -> None:
            self.borrowed: list[FakeConn] = []
            self.returned: list[FakeConn] = []
            self._next = 1

        def get_connection(self) -> FakeConn:
            c = FakeConn(self._next)
            self._next += 1
            self.borrowed.append(c)
            return c

        def put_connection(self, conn: FakeConn) -> None:
            self.returned.append(conn)

    db = FakeDatabase()
    uow = PostgresUnitOfWork(db)

    with uow:
        conn1 = uow.get_connection()
        with uow:
            conn2 = uow.get_connection()
            assert conn1.cid != conn2.cid
            uow.commit()
        assert uow.get_connection() is conn1

    assert len(db.borrowed) == 2
    assert len(db.returned) == 2
    assert {c.cid for c in db.returned} == {1, 2}
    assert conn2.committed == 1
    assert conn1.rolled_back == 1


def test_external_ai_and_paypal_calls_occur_outside_db_transactions():
    """Verify AI and PayPal calls execute when UnitOfWork transaction is NOT open."""
    from tallerclaro.application.dtos import CapturedPayment, PaymentIntent, QuoteProposalResult, QuoteLineItemInput

    class TrackingUnitOfWork(FakeUnitOfWork):
        def __init__(self) -> None:
            super().__init__()
            self.active_depth = 0

        def __enter__(self):
            self.active_depth += 1
            return super().__enter__()

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.active_depth -= 1
            return super().__exit__(exc_type, exc_val, exc_tb)

    uow = TrackingUnitOfWork()
    with uow:
        uow.carpenters.seed(Carpenter(id=CarpenterId(1), name="José", workshop_name="Taller", email="j@example.com", phone=None))
        uow.commit()
    created = CreateQuote(uow).execute(
        CreateQuoteInput(
            customer=CustomerInput(name="Carlos", email="carlos@example.com", phone=None),
            carpenter_id=CarpenterId(1),
            request="Mesa",
        )
    )

    class AssertingOutsideTxAI:
        def generate_quote_proposal(self, request: str) -> QuoteProposalResult:
            assert uow.active_depth == 0, "AI called inside open DB transaction!"
            return QuoteProposalResult(
                description="Mesa",
                line_items=[QuoteLineItemInput(type="material", description="Pino", unit="u", quantity=Decimal("2"), unit_price=Decimal("100"))],
            )

    GenerateQuoteProposal(uow, AssertingOutsideTxAI()).execute(created.quote.id)
    order = ApproveQuote(uow).execute(created.quote.id)

    class AssertingOutsideTxPayPal:
        def create_order(self, amount: str, currency: str, request_id: str | None = None) -> PaymentIntent:
            assert uow.active_depth == 0, "PayPal create_order called inside open DB transaction!"
            return PaymentIntent(
                payment_id=0,
                paypal_order_id="PP-OUTSIDE-1",
                amount=Decimal(amount),
                currency=currency,
                approval_url="https://sandbox.paypal.com/checkoutnow?token=PP-OUTSIDE-1",
            )

        def capture_order(self, paypal_order_id: str) -> CapturedPayment:
            assert uow.active_depth == 0, "PayPal capture_order called inside open DB transaction!"
            return CapturedPayment(
                payment_id=0,
                status="completed",
                paypal_order_id=paypal_order_id,
                paypal_capture_id="CAP-OUTSIDE-1",
                amount=Decimal("100.00"),
                currency="USD",
                paid_at="2026-11-02T20:00:00+00:00",
            )

    processor = AssertingOutsideTxPayPal()
    intent = CreateOrderPayment(uow, processor).execute(order.id, "deposit")
    captured = CapturePayment(uow, processor).execute(intent.payment_id)
    assert captured.status == "completed"


def test_capture_payment_rejects_mismatched_amount_and_currency():
    """Verify CapturePayment rejects tampered amount, currency, or PayPal order ID."""
    from tallerclaro.application.dtos import CapturedPayment, PaymentIntent

    uow = FakeUnitOfWork()
    with uow:
        uow.carpenters.seed(Carpenter(id=CarpenterId(1), name="José", workshop_name="Taller", email="j@example.com", phone=None))
        uow.commit()
    created = CreateQuote(uow).execute(
        CreateQuoteInput(
            customer=CustomerInput(name="Carlos", email="carlos@example.com", phone=None),
            carpenter_id=CarpenterId(1),
            request="Mesa",
        )
    )
    GenerateQuoteProposal(uow, FakeAIService()).execute(created.quote.id)
    order = ApproveQuote(uow).execute(created.quote.id)

    class TamperedPayPalProcessor:
        def __init__(self, amount: Decimal, currency: str, order_id: str = "PP-1") -> None:
            self._amount = amount
            self._currency = currency
            self._order_id = order_id

        def create_order(self, amount: str, currency: str, request_id: str | None = None) -> PaymentIntent:
            return PaymentIntent(
                payment_id=0,
                paypal_order_id="PP-1",
                amount=Decimal(amount),
                currency=currency,
                approval_url=None,
            )

        def capture_order(self, paypal_order_id: str) -> CapturedPayment:
            return CapturedPayment(
                payment_id=0,
                status="completed",
                paypal_order_id=self._order_id,
                paypal_capture_id="CAP-1",
                amount=self._amount,
                currency=self._currency,
                paid_at="2026-11-02T20:00:00+00:00",
            )

    # 1. Wrong amount (50.00 instead of expected 100.00 deposit)
    proc_wrong_amount = TamperedPayPalProcessor(amount=Decimal("50.00"), currency="USD")
    intent1 = CreateOrderPayment(uow, proc_wrong_amount).execute(order.id, "deposit")
    with pytest.raises(ConflictError, match="Captured amount"):
        CapturePayment(uow, proc_wrong_amount).execute(intent1.payment_id)

    # 2. Wrong currency (MXN instead of USD)
    proc_wrong_currency = TamperedPayPalProcessor(amount=Decimal("100.00"), currency="MXN")
    with pytest.raises(ConflictError, match="Captured currency"):
        CapturePayment(uow, proc_wrong_currency).execute(intent1.payment_id)

    # 3. Wrong PayPal order ID
    proc_wrong_order = TamperedPayPalProcessor(amount=Decimal("100.00"), currency="USD", order_id="PP-OTHER")
    with pytest.raises(ConflictError, match="Captured PayPal order ID"):
        CapturePayment(uow, proc_wrong_order).execute(intent1.payment_id)

    # More precision than the expected amount must not be rounded into a match.
    proc_fractional = TamperedPayPalProcessor(amount=Decimal("100.004"), currency="USD")
    with pytest.raises(ConflictError, match="Captured payment amount"):
        CapturePayment(uow, proc_fractional).execute(intent1.payment_id)
    proc_extra_precision = TamperedPayPalProcessor(amount=Decimal("100.000"), currency="USD")
    with pytest.raises(ConflictError, match="Captured payment amount"):
        CapturePayment(uow, proc_extra_precision).execute(intent1.payment_id)


def test_generate_quote_proposal_enforces_workshop_authorization():
    """Verify Carpenter 1 cannot generate a proposal for Carpenter 2's quote."""
    from tallerclaro.application.dtos import AccessPrincipal
    from tallerclaro.application.exceptions import ForbiddenError

    uow = FakeUnitOfWork()
    with uow:
        uow.carpenters.seed(Carpenter(id=CarpenterId(1), name="Carp 1", workshop_name="W1", email="c1@ex.com", phone=None))
        uow.commit()
    with uow:
        uow.carpenters.seed(Carpenter(id=CarpenterId(2), name="Carp 2", workshop_name="W2", email="c2@ex.com", phone=None))
        uow.commit()

    created = CreateQuote(uow).execute(
        CreateQuoteInput(
            customer=CustomerInput(name="Carlos", email="carlos@example.com", phone=None),
            carpenter_id=CarpenterId(2),
            request="Mesa",
        )
    )
    principal_carp1 = AccessPrincipal(kind="workshop", carpenter_id=CarpenterId(1))
    with pytest.raises(ForbiddenError):
        GenerateQuoteProposal(uow, FakeAIService()).execute(
            created.quote.id,
            principal=principal_carp1,
        )


def test_capture_payment_rejects_overpayment_and_stale_balance_intents():
    """Verify stale pending balance intents cannot exceed the remaining order balance."""
    uow = FakeUnitOfWork()
    with uow:
        uow.carpenters.seed(Carpenter(id=CarpenterId(1), name="José", workshop_name="Taller", email="j@example.com", phone=None))
        uow.commit()
    created = CreateQuote(uow).execute(
        CreateQuoteInput(
            customer=CustomerInput(name="Carlos", email="carlos@example.com", phone=None),
            carpenter_id=CarpenterId(1),
            request="Mesa",
        )
    )
    GenerateQuoteProposal(uow, FakeAIService()).execute(created.quote.id)
    order = ApproveQuote(uow).execute(created.quote.id)

    processor = FakePaymentProcessor(success=True)
    # El segundo POST de anticipo reutiliza el mismo intento: no hay duplicado.
    deposit_intent = CreateOrderPayment(uow, processor).execute(order.id, "deposit")
    replay = CreateOrderPayment(uow, processor).execute(order.id, "deposit")
    assert replay.payment_id == deposit_intent.payment_id

    # El saldo se crea mientras aún no hay dinero cobrado ($200).
    stale_balance_intent = CreateOrderPayment(uow, processor).execute(order.id, "balance")

    # Capturar el anticipo deja $100 pendientes.
    CapturePayment(uow, processor).execute(deposit_intent.payment_id)

    # Recapturar el mismo intento es idempotente y no crea un segundo cobro.
    captured = CapturePayment(uow, processor).execute(replay.payment_id)
    assert captured.status == "completed"
    with uow:
        deposit_rows = [
            payment
            for payment in uow.payments.list_by_order(order.id)
            if payment.type == "deposit"
        ]
        assert len(deposit_rows) == 1

    # Capturar el saldo obsoleto de $200 debe fallar: solo quedan $100.
    with pytest.raises(ConflictError, match="exceeds remaining balance"):
        CapturePayment(uow, processor).execute(stale_balance_intent.payment_id)


def test_paypal_adapter_verifies_real_response_structure_and_capture_status():
    """Verify PayPalPaymentProcessor validates returned order id, capture status, and payload structure."""
    from unittest.mock import MagicMock
    from tallerclaro.bootstrap.settings import Settings
    from tallerclaro.domain.exceptions import DomainError
    from tallerclaro.infrastructure.payment.paypal_processor import PayPalPaymentProcessor

    settings = Settings(
        paypal_mode="sandbox",
        paypal_client_id="client-id",
        paypal_client_secret="client-secret",
        paypal_return_url="https://example.org/return",
        paypal_cancel_url="https://example.org/cancel",
    )

    def _make_client(capture_json: dict) -> MagicMock:
        client = MagicMock()
        token_resp = MagicMock(status_code=200)
        token_resp.json.return_value = {"access_token": "tok-123"}
        cap_resp = MagicMock(status_code=201)
        cap_resp.json.return_value = capture_json
        client.post.side_effect = [token_resp, cap_resp]
        return client

    # 1. Mismatched order ID in PayPal response
    bad_order_id_client = _make_client({
        "id": "PP-DIFFERENT",
        "status": "COMPLETED",
        "purchase_units": [{"payments": {"captures": [{"id": "CAP-1", "status": "COMPLETED", "amount": {"value": "100.00", "currency_code": "USD"}}]}}],
    })
    with pytest.raises(DomainError, match="order id mismatch"):
        PayPalPaymentProcessor(settings, client=bad_order_id_client).capture_order("PP-EXPECTED")

    # 2. Capture status is PENDING/DECLINED even if top-level order says COMPLETED
    declined_capture_client = _make_client({
        "id": "PP-EXPECTED",
        "status": "COMPLETED",
        "purchase_units": [{"payments": {"captures": [{"id": "CAP-1", "status": "DECLINED", "amount": {"value": "100.00", "currency_code": "USD"}}]}}],
    })
    with pytest.raises(DomainError, match="not COMPLETED"):
        PayPalPaymentProcessor(settings, client=declined_capture_client).capture_order("PP-EXPECTED")

    # 3. Valid response succeeds
    valid_client = _make_client({
        "id": "PP-EXPECTED",
        "status": "COMPLETED",
        "purchase_units": [{
            "payments": {
                "captures": [{
                    "id": "CAP-OK",
                    "status": "COMPLETED",
                    "amount": {"value": "100.00", "currency_code": "USD"},
                    "update_time": "2026-11-02T21:00:00Z",
                }]
            }
        }],
    })
    res = PayPalPaymentProcessor(settings, client=valid_client).capture_order("PP-EXPECTED")
    assert res.paypal_order_id == "PP-EXPECTED"
    assert res.paypal_capture_id == "CAP-OK"
    assert res.amount == Decimal("100.00")
    assert res.currency == "USD"
    assert res.paid_at == "2026-11-02T21:00:00+00:00"


def test_fake_unit_of_work_rolls_back_uncommitted_changes_and_exceptions():
    """Verify FakeUnitOfWork reverts in-memory state when commit() is not called or an exception occurs."""
    from tallerclaro.domain.entities import Customer

    uow = FakeUnitOfWork()

    # 1. Exiting without commit() reverts changes
    with uow:
        uow.customers.save(Customer(id=None, name="Ghost", email="ghost@example.com", phone=None))
    with uow:
        assert uow.customers.get_by_id(CustomerId(1)) is None

    # 2. Exception after save() reverts changes
    with pytest.raises(RuntimeError):
        with uow:
            uow.customers.save(Customer(id=None, name="Crash", email="crash@example.com", phone=None))
            raise RuntimeError("boom")
    with uow:
        assert uow.customers.get_by_id(CustomerId(1)) is None

    # 3. Explicit commit() persists changes
    with uow:
        saved = uow.customers.save(Customer(id=None, name="Real", email="real@example.com", phone=None))
        uow.commit()
    with uow:
        assert uow.customers.get_by_id(saved.id) is not None
    with uow:
        assert uow.customers.get_by_id(saved.id).name == "Real"



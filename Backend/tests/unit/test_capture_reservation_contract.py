"""Contrato de reserva de captura: paridad entre el doble y el SQL local."""

from __future__ import annotations

from unittest.mock import MagicMock

from tallerclaro.application.interfaces import (
    CaptureReservationRepository,
    OrderRepository,
    PaymentRepository,
)
from tallerclaro.domain.entities import OrderId, PaymentId
from tallerclaro.infrastructure.db.repositories import PostgresCaptureReservationRepository
from tests.fakes import FakeCaptureReservationRepository, FakeUnitOfWork


class ReservationConnection:
    """Conexión simulada que emula ``pedido.captura_en_curso`` (sin PostgreSQL real)."""

    def __init__(self) -> None:
        self.captures: dict[int, int] = {}
        self.queries: list[tuple[str, tuple]] = []

    def execute(self, sql: str, params: tuple = ()):
        clean_sql = " ".join(sql.split())
        self.queries.append((clean_sql, params))
        cursor = MagicMock()
        if "RETURNING" in clean_sql:
            payment_id, order_id, expected = params
            current = self.captures.get(order_id)
            if current is None or current == expected:
                self.captures[order_id] = payment_id
                cursor.fetchone.return_value = (order_id,)
            else:
                cursor.fetchone.return_value = None
            return cursor

        order_id, payment_id = params
        if self.captures.get(order_id) == payment_id:
            self.captures.pop(order_id)
        return cursor


def _run_scenario(repository: CaptureReservationRepository) -> list[bool]:
    results = [
        repository.reserve(OrderId(1), PaymentId(10)),
        repository.reserve(OrderId(1), PaymentId(10)),
        repository.reserve(OrderId(1), PaymentId(11)),
        repository.reserve(OrderId(2), PaymentId(11)),
    ]
    repository.release(OrderId(1), PaymentId(11))
    results.append(repository.reserve(OrderId(1), PaymentId(12)))
    repository.release(OrderId(1), PaymentId(10))
    results.append(repository.reserve(OrderId(1), PaymentId(12)))
    return results


def test_fake_and_postgres_reservation_implementations_are_equivalent():
    fake = FakeCaptureReservationRepository()
    conn = ReservationConnection()
    postgres = PostgresCaptureReservationRepository(conn)

    assert _run_scenario(fake) == _run_scenario(postgres) == [True, True, False, True, False, True]
    assert fake._captures == {OrderId(1): PaymentId(12), OrderId(2): PaymentId(11)}
    assert conn.captures == {1: 12, 2: 11}


def test_postgres_reservation_uses_conditional_update_and_parameters():
    conn = ReservationConnection()
    repo = PostgresCaptureReservationRepository(conn)

    assert repo.reserve(OrderId(7), PaymentId(3)) is True
    repo.release(OrderId(7), PaymentId(3))

    reserve_sql, reserve_params = conn.queries[0]
    assert "UPDATE tallerclaro.pedido" in reserve_sql
    assert "captura_en_curso" in reserve_sql
    assert "RETURNING id_pedido" in reserve_sql
    assert reserve_params == (3, 7, 3)

    release_sql, release_params = conn.queries[1]
    assert "captura_en_curso = NULL" in release_sql
    assert release_params == (7, 3)


def test_release_only_frees_own_reservation():
    fake = FakeCaptureReservationRepository()
    assert fake.reserve(OrderId(1), PaymentId(10)) is True

    fake.release(OrderId(1), PaymentId(99))
    assert fake.reserve(OrderId(1), PaymentId(11)) is False

    fake.release(OrderId(1), PaymentId(10))
    assert fake.reserve(OrderId(1), PaymentId(11)) is True


def test_reservation_is_reverted_when_unit_of_work_is_not_committed():
    uow = FakeUnitOfWork()

    with uow:
        uow.capture_reservations.reserve(OrderId(1), PaymentId(10))

    with uow:
        assert uow.capture_reservations.reserve(OrderId(1), PaymentId(11)) is True
        uow.commit()


def test_reservation_is_kept_after_commit():
    uow = FakeUnitOfWork()

    with uow:
        uow.capture_reservations.reserve(OrderId(1), PaymentId(10))
        uow.commit()

    with uow:
        assert uow.capture_reservations.reserve(OrderId(1), PaymentId(11)) is False
        uow.commit()


def test_order_protocol_no_longer_carries_capture_reservation_methods():
    assert "reserve_capture" not in OrderRepository.__dict__
    assert "release_capture" not in OrderRepository.__dict__
    assert "reserve" in CaptureReservationRepository.__dict__
    assert "release" in CaptureReservationRepository.__dict__


def test_payment_protocol_has_no_unconsumed_lookup():
    assert "get_by_paypal_order_id" not in PaymentRepository.__dict__

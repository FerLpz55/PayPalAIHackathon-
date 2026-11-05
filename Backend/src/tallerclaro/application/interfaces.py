"""Contratos e interfaces de la capa de aplicación.

Define las abstracciones (Protocols) que la capa de aplicación requiere para
persistencia, servicios de IA y procesadores de pago. Cada protocolo documenta
precondiciones, resultados, errores y semántica transaccional; las
implementaciones de infraestructura y los dobles de prueba deben respetarlos.

Los protocolos no importan frameworks ni infraestructura: solo dominio y DTOs de
aplicación.
"""

from __future__ import annotations

from typing import Protocol

from tallerclaro.application.dtos import (
    CapturedPayment,
    PaymentIntent,
    QuoteProposalResult,
)
from tallerclaro.domain.entities import (
    Carpenter,
    CarpenterId,
    Customer,
    CustomerId,
    Order,
    OrderId,
    Payment,
    PaymentId,
    Quote,
    QuoteId,
)


class CustomerRepository(Protocol):
    """Persistencia de clientes.

    Precondición: ``save`` recibe una entidad con datos válidos de dominio.
    Resultado: devuelve la entidad con ``id`` y marcas de tiempo asignadas.
    Errores: propaga el error del motor de persistencia; no lo silencia.
    """

    def save(self, customer: Customer) -> Customer:
        ...

    def get_by_id(self, customer_id: CustomerId) -> Customer | None:
        """Devuelve ``None`` si el cliente no existe; no lanza por ausencia."""
        ...


class CarpenterRepository(Protocol):
    """Consulta de talleres."""

    def get_by_id(self, carpenter_id: CarpenterId) -> Carpenter | None:
        """Devuelve ``None`` si el taller no existe; no lanza por ausencia."""
        ...


class QuoteRepository(Protocol):
    """Persistencia de cotizaciones y sus partidas.

    Precondición: ``save`` recibe una cotización con total recalculado.
    Resultado: devuelve la cotización con identificadores persistidos.
    """

    def save(self, quote: Quote) -> Quote:
        ...

    def get_by_id(self, quote_id: QuoteId) -> Quote | None:
        """Devuelve ``None`` si la cotización no existe."""
        ...


class OrderRepository(Protocol):
    """Persistencia de pedidos (sin la reserva de captura)."""

    def save(self, order: Order) -> Order:
        ...

    def get_by_id(self, order_id: OrderId) -> Order | None:
        """Devuelve ``None`` si el pedido no existe."""
        ...

    def get_by_quote_id(self, quote_id: QuoteId) -> Order | None:
        """Devuelve el pedido de la cotización, si existe."""
        ...

    def list_by_carpenter(
        self, carpenter_id: CarpenterId, limit: int, offset: int
    ) -> list[Order]:
        """Devuelve pedidos del taller ordenados del más reciente al más antiguo."""
        ...

    def count_by_carpenter(self, carpenter_id: CarpenterId) -> int:
        ...


class CaptureReservationRepository(Protocol):
    """Reserva exclusiva de captura por pedido.

    Contrato: solo un intento de pago puede tener la reserva de un pedido.
    ``reserve`` es idempotente para el mismo ``payment_id`` y devuelve ``False``
    si otro pago ya la posee. ``release`` solo libera la reserva del pago
    indicado; liberar una reserva ajena o inexistente es un no-op.

    La reserva debe persistirse dentro de la transacción del ``UnitOfWork``
    actual: si la transacción no se confirma, no debe quedar visible.
    """

    def reserve(self, order_id: OrderId, payment_id: PaymentId) -> bool:
        ...

    def release(self, order_id: OrderId, payment_id: PaymentId) -> None:
        ...


class PaymentRepository(Protocol):
    """Persistencia de intentos de pago."""

    def save(self, payment: Payment) -> Payment:
        ...

    def get_by_id(self, payment_id: PaymentId) -> Payment | None:
        """Devuelve ``None`` si el pago no existe."""
        ...

    def list_by_order(self, order_id: OrderId) -> list[Payment]:
        """Devuelve todos los intentos del pedido, incluidos los no completados."""
        ...


class CustomerTokenRepository(Protocol):
    """Emisión y verificación de tokens de enlace de cliente.

    Verificar devuelve None para tokens desconocidos, alterados, usados o con
    vencimiento anterior al instante UTC actual. En el instante exacto de
    vencimiento siguen siendo válidos (expiration < now).
    """

    def create(self, customer_id: CustomerId, quote_id: QuoteId) -> str:
        ...

    def verify(self, token: str) -> tuple[CustomerId, QuoteId] | None:
        """Devuelve ``None`` para tokens inválidos, manipulados o expirados."""
        ...


class UnitOfWork(Protocol):
    """Frontera transaccional por petición.

    Precondiciones: cada petición crea su propia instancia; no se comparte
    entre hilos ni peticiones. ``__enter__`` abre la transacción y expone los
    repositorios; ``__exit__`` devuelve la conexión siempre.

    Semántica transaccional: sin ``commit`` explícito se hace ``rollback`` al
    salir del contexto, incluso sin excepción. Una excepción también revierte.
    Resolver repositorios a través del UoW requiere un contexto activo.
    No se garantiza invalidación automática de referencias ya obtenidas.
    """

    def __enter__(self) -> UnitOfWork:
        ...

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        ...

    @property
    def customers(self) -> CustomerRepository:
        ...

    @property
    def carpenters(self) -> CarpenterRepository:
        ...

    @property
    def quotes(self) -> QuoteRepository:
        ...

    @property
    def orders(self) -> OrderRepository:
        ...

    @property
    def capture_reservations(self) -> CaptureReservationRepository:
        ...

    @property
    def payments(self) -> PaymentRepository:
        ...

    @property
    def tokens(self) -> CustomerTokenRepository:
        ...

    def commit(self) -> None:
        """Confirma la transacción activa; los cambios pasan a ser visibles."""
        ...

    def rollback(self) -> None:
        """Revierte la transacción activa sin devolver la conexión todavía."""
        ...


class AIService(Protocol):
    """Generación de propuestas de cotización.

    Errores: ante falta de configuración o fallo del proveedor lanza
    ``DomainError`` (``SERVICE_UNAVAILABLE``/``AI_RESPONSE_INVALID``); nunca
    devuelve una propuesta simulada como si fuera real.
    """

    def generate_quote_proposal(self, request: str) -> QuoteProposalResult:
        ...


class PaymentProcessor(Protocol):
    """Procesador de pagos externo.

    Precondiciones: importes en USD con dos decimales; ``capture_order`` recibe
    el identificador de una orden creada por ``create_order``.
    Resultado: DTOs con el identificador del proveedor y el importe confirmado.
    Errores: ``DomainError`` con código ``SERVICE_UNAVAILABLE``,
    ``PAYMENT_PROVIDER_ERROR`` o ``PAYMENT_FAILED``; la indisponibilidad nunca
    se expresa como un pago exitoso.
    Los fallos de conexión, timeout y protocolo HTTP se normalizan a
    ``PAYMENT_PROVIDER_ERROR``; no se exponen excepciones del cliente HTTP.
    """

    def create_order(self, amount: str, currency: str) -> PaymentIntent:
        ...

    def capture_order(self, paypal_order_id: str) -> CapturedPayment:
        ...

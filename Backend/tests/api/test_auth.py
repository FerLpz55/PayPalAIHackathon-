"""Pruebas de autenticación, autorización (IDOR), adaptadores y flujos API."""

from decimal import Decimal
import pytest
from unittest.mock import MagicMock
from fastapi import Request
from fastapi.testclient import TestClient

from tallerclaro.application.dtos import (
    AccessPrincipal,
    CreatedQuoteResult,
    QuoteLineItemInput,
    QuoteProposalResult,
)
from tallerclaro.bootstrap.settings import Settings
from tallerclaro.domain.entities import (
    Carpenter,
    CarpenterId,
    CustomerId,
    Money,
    Quote,
    QuoteId,
    QuoteLineItem,
    QuoteLineItemId,
)
from tallerclaro.domain.exceptions import DomainError
from tallerclaro.infrastructure.ai.adapter import OpenAIAIService
from tallerclaro.infrastructure.db.repositories import PostgresQuoteRepository
from tallerclaro.main import create_app
from tallerclaro.presentation.http.dependencies import get_unit_of_work
from tests.fakes import FakeAIService, FakePaymentProcessor, FakeUnitOfWork


@pytest.fixture
def unmocked_auth_app():
    settings = Settings(
        workshop_username="taller",
        workshop_password="demo-password",
        workshop_carpenter_id=1,
        cors_origins=["http://localhost:5173"],
    )
    uow = FakeUnitOfWork()
    uow.carpenters.seed(
        Carpenter(
            id=CarpenterId(1),
            name="José Carpintero",
            workshop_name="Taller José",
            email="jose@tallerclaro.com",
            phone=None,
        )
    )
    ai_service = FakeAIService()
    payment_processor = FakePaymentProcessor(success=True)

    app = create_app(
        settings=settings,
        ai_service=ai_service,
        payment_processor=payment_processor,
    )

    # Solo sobreescribimos get_unit_of_work para usar los fakes en memoria;
    # NO sobreescribimos dependencias de autenticación para probar los checks reales.
    def override_uow(request: Request):
        return uow

    app.dependency_overrides[get_unit_of_work] = override_uow
    return TestClient(app), uow, ai_service, payment_processor


def test_auth_401_when_credentials_or_tokens_absent_or_invalid(unmocked_auth_app):
    client, uow, ai_service, payment_processor = unmocked_auth_app

    # 1. Rutas de taller sin credenciales -> 401
    resp = client.get("/api/orders")
    assert resp.status_code == 401
    assert "Basic" in resp.headers.get("www-authenticate", "")

    # Rutas de taller con credenciales inválidas -> 401
    resp = client.get("/api/orders", auth=("taller", "wrong-password"))
    assert resp.status_code == 401

    # 2. Generar cotización sin credenciales de taller -> 401
    resp = client.post("/api/quotes/1/generate")
    assert resp.status_code == 401

    # 3. Consultar cotización sin token ni credenciales -> 401
    resp = client.get("/api/quotes/1")
    assert resp.status_code == 401

    # Consultar cotización con token inválido -> 401
    resp = client.get("/api/quotes/1", headers={"X-Customer-Token": "invalid-token-123"})
    assert resp.status_code == 401

    # 4. Aprobar o rechazar cotización sin token -> 401
    resp = client.post("/api/quotes/1/approve")
    assert resp.status_code == 401
    resp = client.post("/api/quotes/1/reject")
    assert resp.status_code == 401

    # 5. Consultar pedido sin auth -> 401
    resp = client.get("/api/orders/1")
    assert resp.status_code == 401

    # 6. Actualizar pedido sin auth -> 401
    resp = client.patch("/api/orders/1", json={"status": "in_progress"})
    assert resp.status_code == 401

    # 7. Rutas de pagos sin token de cliente -> 401
    resp = client.post("/api/orders/1/payments", json={"type": "deposit"})
    assert resp.status_code == 401
    resp = client.post("/api/payments/1/capture")
    assert resp.status_code == 401
    resp = client.get("/api/payments/1")
    assert resp.status_code == 401


def test_auth_403_idor_prevention(unmocked_auth_app):
    client, uow, ai_service, payment_processor = unmocked_auth_app

    # Crear Cotización A para Cliente A
    resp_a = client.post(
        "/api/quotes",
        json={
            "customer": {"name": "Cliente A", "email": "a@example.com"},
            "carpenter_id": 1,
            "request": "Mesa de roble para Cliente A",
        },
    )
    assert resp_a.status_code == 201
    data_a = resp_a.json()
    quote_a_id = data_a["id"]
    token_a = data_a["customer_token"]

    # Crear Cotización B para Cliente B
    resp_b = client.post(
        "/api/quotes",
        json={
            "customer": {"name": "Cliente B", "email": "b@example.com"},
            "carpenter_id": 1,
            "request": "Escritorio para Cliente B",
        },
    )
    assert resp_b.status_code == 201
    data_b = resp_b.json()
    quote_b_id = data_b["id"]
    token_b = data_b["customer_token"]

    # El taller genera las propuestas para ambas
    client.post(f"/api/quotes/{quote_a_id}/generate", auth=("taller", "demo-password"))
    client.post(f"/api/quotes/{quote_b_id}/generate", auth=("taller", "demo-password"))

    # Cliente A aprueba su cotización -> Pedido A
    order_a_resp = client.post(
        f"/api/quotes/{quote_a_id}/approve",
        headers={"X-Customer-Token": token_a},
    )
    assert order_a_resp.status_code == 200
    order_a_id = order_a_resp.json()["id"]

    # Cliente B aprueba su cotización -> Pedido B
    order_b_resp = client.post(
        f"/api/quotes/{quote_b_id}/approve",
        headers={"X-Customer-Token": token_b},
    )
    assert order_b_resp.status_code == 200
    order_b_id = order_b_resp.json()["id"]

    # Cliente B genera un pago para su Pedido B -> Pago B
    pay_b_resp = client.post(
        f"/api/orders/{order_b_id}/payments",
        json={"type": "deposit"},
        headers={"X-Customer-Token": token_b},
    )
    assert pay_b_resp.status_code == 200
    payment_b_id = pay_b_resp.json()["payment_id"]

    # --- PRUEBAS DE PREVENCIÓN DE IDOR (Cliente A intentando acceder a recursos de B) ---

    # 1. Cliente A no puede consultar Cotización B
    resp = client.get(f"/api/quotes/{quote_b_id}", headers={"X-Customer-Token": token_a})
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"

    # 2. Cliente A no puede aprobar Cotización B
    resp = client.post(f"/api/quotes/{quote_b_id}/approve", headers={"X-Customer-Token": token_a})
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"

    # 3. Cliente A no puede rechazar Cotización B
    resp = client.post(f"/api/quotes/{quote_b_id}/reject", headers={"X-Customer-Token": token_a})
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"

    # 4. Cliente A no puede consultar Pedido B
    resp = client.get(f"/api/orders/{order_b_id}", headers={"X-Customer-Token": token_a})
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"

    # 5. Cliente A no puede crear un pago para Pedido B
    resp = client.post(
        f"/api/orders/{order_b_id}/payments",
        json={"type": "deposit"},
        headers={"X-Customer-Token": token_a},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"

    # 6. Cliente A no puede capturar Pago B
    resp = client.post(
        f"/api/payments/{payment_b_id}/capture",
        headers={"X-Customer-Token": token_a},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"

    # 7. Cliente A no puede consultar Pago B
    resp = client.get(
        f"/api/payments/{payment_b_id}",
        headers={"X-Customer-Token": token_a},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"


def test_workshop_access_to_orders_and_quotes(unmocked_auth_app):
    client, uow, ai_service, payment_processor = unmocked_auth_app

    # Crear una cotización
    resp = client.post(
        "/api/quotes",
        json={
            "customer": {"name": "María", "email": "maria@example.com"},
            "carpenter_id": 1,
            "request": "Cama King en nogal",
        },
    )
    assert resp.status_code == 201
    quote_id = resp.json()["id"]

    # El taller puede consultar la cotización
    get_resp = client.get(f"/api/quotes/{quote_id}", auth=("taller", "demo-password"))
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == quote_id

    # El taller puede generar propuesta
    gen_resp = client.post(f"/api/quotes/{quote_id}/generate", auth=("taller", "demo-password"))
    assert gen_resp.status_code == 200
    assert gen_resp.json()["status"] == "pending_review"

    # El taller puede aprobar en nombre del taller
    app_resp = client.post(f"/api/quotes/{quote_id}/approve", auth=("taller", "demo-password"))
    assert app_resp.status_code == 200
    order_id = app_resp.json()["id"]

    # El taller puede listar pedidos
    list_resp = client.get("/api/orders", auth=("taller", "demo-password"))
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    # El taller puede consultar el pedido detallado
    order_detail = client.get(f"/api/orders/{order_id}", auth=("taller", "demo-password"))
    assert order_detail.status_code == 200
    assert order_detail.json()["customer_name"] == "María"

    # El taller puede actualizar el estado del pedido
    update_resp = client.patch(
        f"/api/orders/{order_id}",
        json={"status": "in_progress"},
        auth=("taller", "demo-password"),
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "in_progress"


def test_needs_information_clarification_flow_via_api(unmocked_auth_app):
    client, uow, ai_service, payment_processor = unmocked_auth_app

    # 1. Crear cotización con solicitud ambigua
    resp = client.post(
        "/api/quotes",
        json={
            "customer": {"name": "Lucía", "email": "lucia@example.com", "phone": "12345678"},
            "carpenter_id": 1,
            "request": "Quiero una estantería de libros",
        },
    )
    assert resp.status_code == 201
    quote_id = resp.json()["id"]
    token = resp.json()["customer_token"]

    # 2. IA indica que necesita información adicional
    ai_service._proposal = QuoteProposalResult(
        description="",
        line_items=[],
        needs_information=True,
        missing_info=["Medidas exactas (alto, ancho, fondo)", "Madera deseada"],
    )

    gen_resp = client.post(
        f"/api/quotes/{quote_id}/generate",
        auth=("taller", "demo-password"),
    )
    assert gen_resp.status_code == 200
    data_gen = gen_resp.json()
    assert data_gen["status"] == "needs_information"
    assert data_gen["missing_info"] == ["Medidas exactas (alto, ancho, fondo)", "Madera deseada"]

    # Cliente consulta su cotización y ve que requiere información
    get_resp = client.get(f"/api/quotes/{quote_id}", headers={"X-Customer-Token": token})
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "needs_information"
    assert get_resp.json()["missing_info"] == ["Medidas exactas (alto, ancho, fondo)", "Madera deseada"]

    # 3. Se proporciona aclaración (additional_info) y la IA genera la propuesta completa
    ai_service._proposal = QuoteProposalResult(
        description="Estantería para libros en pino macizo",
        line_items=[
            QuoteLineItemInput(
                type="material",
                description="Tablas de pino tratado",
                unit="m",
                quantity=Decimal("12"),
                unit_price=Decimal("15"),
            ),
            QuoteLineItemInput(
                type="labor",
                description="Corte, ensamble y barnizado",
                unit="servicio",
                quantity=Decimal("1"),
                unit_price=Decimal("100"),
            ),
        ],
        assumptions=["Acabado satinado transparente", "Fijación a muro incluida"],
    )

    clarif_resp = client.post(
        f"/api/quotes/{quote_id}/generate",
        json={"additional_info": "Alto: 2m, Ancho: 1m, Fondo: 30cm en pino"},
        auth=("taller", "demo-password"),
    )
    assert clarif_resp.status_code == 200
    data_clarif = clarif_resp.json()
    assert data_clarif["status"] == "pending_review"
    assert data_clarif["total"] == 280.0
    assert len(data_clarif["items"]) == 2
    assert "Fijación a muro incluida" in data_clarif["assumptions"]

    # Cliente aprueba la cotización clarificada
    approve_resp = client.post(
        f"/api/quotes/{quote_id}/approve",
        headers={"X-Customer-Token": token},
    )
    assert approve_resp.status_code == 200
    order_data = approve_resp.json()
    assert order_data["status"] == "pending"
    assert order_data["total"] == 280.0
    assert order_data["deposit_amount"] == 140.0


def test_schema_extra_forbid_and_cors_headers(unmocked_auth_app):
    client, uow, ai_service, payment_processor = unmocked_auth_app

    # Extra fields forbidden en CreateQuoteRequest -> 422
    resp = client.post(
        "/api/quotes",
        json={
            "customer": {"name": "Carlos", "email": "carlos@example.com"},
            "carpenter_id": 1,
            "request": "Mesa",
            "malicious_field": "injected",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"

    # CORS header presente ante request de origen permitido
    cors_resp = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert cors_resp.status_code == 200
    assert cors_resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_openai_ai_service_validation_and_error_handling():
    # 1. Error de red o HTTP no expone API keys y lanza SERVICE_UNAVAILABLE
    settings = Settings(ai_api_key="sk-secret-key-12345", ai_provider="openai")
    mock_client = MagicMock()
    mock_client.post.side_effect = RuntimeError("Connection timeout to api.openai.com")

    service = OpenAIAIService(settings=settings, client=mock_client)
    with pytest.raises(DomainError) as exc_info:
        service.generate_quote_proposal("Mesa")
    assert exc_info.value.code == "SERVICE_UNAVAILABLE"
    assert "sk-secret-key-12345" not in str(exc_info.value)

    # 2. Validación estricta de partidas
    valid_mock = MagicMock()
    service_valid = OpenAIAIService(settings=settings, client=valid_mock)

    # Partida con tipo inválido
    invalid_type_json = '{"items": [{"type": "gold", "description": "mesa", "quantity": 1, "unit_price": 50}]}'
    with pytest.raises(DomainError) as exc_info:
        service_valid._parse_proposal(invalid_type_json)
    assert exc_info.value.code == "AI_RESPONSE_INVALID"

    # Partida con descripción vacía
    empty_desc_json = '{"items": [{"type": "material", "description": "  ", "quantity": 1, "unit_price": 50}]}'
    with pytest.raises(DomainError) as exc_info:
        service_valid._parse_proposal(empty_desc_json)
    assert exc_info.value.code == "AI_RESPONSE_INVALID"

    # Partida con cantidad <= 0
    zero_qty_json = '{"items": [{"type": "material", "description": "madera", "quantity": 0, "unit_price": 50}]}'
    with pytest.raises(DomainError) as exc_info:
        service_valid._parse_proposal(zero_qty_json)
    assert exc_info.value.code == "AI_RESPONSE_INVALID"

    # Partida con precio unitario negativo
    neg_price_json = '{"items": [{"type": "material", "description": "madera", "quantity": 2, "unit_price": -10}]}'
    with pytest.raises(DomainError) as exc_info:
        service_valid._parse_proposal(neg_price_json)
    assert exc_info.value.code == "AI_RESPONSE_INVALID"


def test_postgres_quote_repository_sync_without_delete():
    # Verificamos que PostgresQuoteRepository.save nunca emita DELETE y sincronice filas existentes
    mock_conn = MagicMock()
    # Simular que la cotización ya existe
    mock_conn.execute.return_value.fetchone.return_value = (10, None, None)
    # Simular que en la BD ya existen las partidas 101 y 102
    mock_conn.execute.return_value.fetchall.return_value = [(101,), (102,)]

    repo = PostgresQuoteRepository(mock_conn)

    quote = Quote(
        id=QuoteId(10),
        customer_id=CustomerId(1),
        carpenter_id=CarpenterId(1),
        request="Mesa",
        description="Mesa de centro",
        line_items=[
            QuoteLineItem(
                id=QuoteLineItemId(101),
                type="material",
                description="Madera actualizada",
                unit="m2",
                quantity=Decimal("3"),
                unit_price=Money(Decimal("40")),
            ),
            QuoteLineItem(
                id=None,  # Nueva partida o reutilización de 102
                type="labor",
                description="Mano de obra nueva",
                unit="hr",
                quantity=Decimal("5"),
                unit_price=Money(Decimal("25")),
            ),
        ],
        total=Money(Decimal("245")),
        status="pending_review",
    )

    repo.save(quote)

    # Verificar que NINGUNA sentencia ejecutada fue DELETE FROM detalle_cotizacion
    executed_statements = [call.args[0] for call in mock_conn.execute.call_args_list if call.args]
    for sql in executed_statements:
        assert "DELETE FROM tallerclaro.detalle_cotizacion" not in sql
        assert "DELETE" not in sql.upper() or "detalle_cotizacion" not in sql

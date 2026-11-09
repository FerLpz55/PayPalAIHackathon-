"""Router HTTP para cotizaciones."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request, status

from tallerclaro.application.dtos import CreateQuoteInput, CustomerInput
from tallerclaro.application.use_cases import (
    ApproveQuote,
    CreateQuote,
    GenerateQuoteProposal,
    GetQuote,
    ReissueCustomerAccess,
    RejectQuote,
)
from tallerclaro.domain.entities import QUOTE_STATUS_NEEDS_INFORMATION, QuoteId
from tallerclaro.presentation.http.dependencies import (
    AIServiceDep,
    PriceLookupServiceDep,
    PrincipalDep,
    SettingsDep,
    UnitOfWorkDep,
    WorkshopCarpenterDep,
)
from tallerclaro.presentation.http.mappers import (
    to_line_item_response as _to_line_item_response,
    to_order_response as _to_order_response,
    to_quote_response as _to_quote_response,
    to_suggested_product_response as _to_suggested_product_response,
)
from tallerclaro.presentation.http.rate_limits import (
    actor_key,
    client_ip,
    enforce_catalog_lookup,
    enforce_quote_creation,
    enforce_quote_generation,
)
from tallerclaro.presentation.http.schemas.customer import ReissueAccessResponse
from tallerclaro.presentation.http.schemas.orders import OrderResponse
from tallerclaro.presentation.http.schemas.quotes import (
    CreateQuoteRequest,
    GenerateQuoteRequest,
    QuoteGenerateResponse,
    QuoteResponse,
)

router = APIRouter(prefix="/api", tags=["quotes"])


@router.post("/quotes", status_code=status.HTTP_201_CREATED)
def create_quote(
    payload: CreateQuoteRequest,
    request: Request,
    uow: UnitOfWorkDep,
    price_lookup: PriceLookupServiceDep,
    settings: SettingsDep,
) -> QuoteResponse:
    ip = client_ip(request, settings)
    enforce_quote_creation(uow, ip)
    # Consumir el cupo de catálogo antes de crear evita dejar cotizaciones
    # huérfanas si el actor ya agotó el límite.
    enforce_catalog_lookup(uow, f"ip:{ip}")
    result = CreateQuote(uow).execute(
        CreateQuoteInput(
            customer=CustomerInput(
                name=payload.customer.name,
                email=payload.customer.email,
                phone=payload.customer.phone,
            ),
            carpenter_id=payload.carpenter_id,
            request=payload.request,
        )
    )
    # Fuera de SQL: obtener referencias iniciales
    suggestions = price_lookup.lookup_prices(payload.request)
    return _to_quote_response(
        result.quote, customer_token=result.customer_token, suggested_products=suggestions
    )


@router.get("/quotes/{quote_id}")
def get_quote(
    quote_id: int,
    principal: PrincipalDep,
    uow: UnitOfWorkDep,
    price_lookup: PriceLookupServiceDep,
    q: str | None = Query(None, description="Búsqueda interactiva de materiales y productos"),
) -> QuoteResponse:
    quote = GetQuote(uow).execute(QuoteId(quote_id), principal)
    # Fuera de SQL: buscar productos por término personalizado o requerimiento original
    enforce_catalog_lookup(uow, actor_key(principal))
    query_text = q.strip() if q and q.strip() else quote.request
    suggestions = price_lookup.lookup_prices(query_text)
    return _to_quote_response(quote, suggested_products=suggestions)


@router.post("/quotes/{quote_id}/generate")
def generate_quote(
    quote_id: int,
    principal: PrincipalDep,
    uow: UnitOfWorkDep,
    ai_service: AIServiceDep,
    price_lookup: PriceLookupServiceDep,
    body: GenerateQuoteRequest | None = None,
) -> QuoteGenerateResponse:
    """Genera o aclara una cotización con token del cliente propietario o sesión del taller.

    El actor se resuelve antes de llamar a la IA. El límite por cotización y el
    presupuesto global del taller se consumen antes del proveedor; si el control
    no está disponible, la excepción impide la llamada externa.
    """
    # Autoriza y obtiene el taller dueño sin llamar a la IA.
    current = GetQuote(uow).execute(QuoteId(quote_id), principal)
    enforce_quote_generation(uow, quote_id, int(current.carpenter_id))
    # El cupo de catálogo también se consume antes del proveedor de IA.
    enforce_catalog_lookup(uow, actor_key(principal))

    additional_info = body.additional_info if body is not None else None
    quote = GenerateQuoteProposal(uow, ai_service).execute(
        QuoteId(quote_id),
        additional_info=additional_info,
        principal=principal,
    )
    # Fuera de SQL: consultar productos sugeridos relevantes
    suggestions = price_lookup.lookup_prices(quote.request)
    return QuoteGenerateResponse(
        id=str(quote.id) if quote.id is not None else "",
        status=quote.status,
        description=quote.description,
        items=[_to_line_item_response(item) for item in quote.line_items],
        total=float(quote.total.amount) if quote.total is not None else None,
        assumptions=list(quote.assumptions) if quote.assumptions else None,
        missing_info=(
            list(quote.missing_info)
            if quote.status == QUOTE_STATUS_NEEDS_INFORMATION
            else None
        ),
        suggested_products=[_to_suggested_product_response(p) for p in suggestions],
    )


@router.post("/quotes/{quote_id}/approve")
def approve_quote(
    quote_id: int,
    principal: PrincipalDep,
    uow: UnitOfWorkDep,
) -> OrderResponse:
    order = ApproveQuote(uow).execute(QuoteId(quote_id), principal)
    return _to_order_response(order)


@router.post("/quotes/{quote_id}/reject")
def reject_quote(
    quote_id: int,
    principal: PrincipalDep,
    uow: UnitOfWorkDep,
) -> QuoteResponse:
    quote = RejectQuote(uow).execute(QuoteId(quote_id), principal)
    return _to_quote_response(quote)


@router.post("/quotes/{quote_id}/customer-access")
def reissue_customer_access(
    quote_id: int,
    principal: WorkshopCarpenterDep,
    uow: UnitOfWorkDep,
) -> ReissueAccessResponse:
    """Emite un token nuevo y revoca los anteriores; exclusivo del taller.

    No permite recuperar acceso usando solo el ID de la cotización: exige sesión
    del taller (o Basic explícito) y valida la pertenencia del recurso.
    """
    token = ReissueCustomerAccess(uow).execute(QuoteId(quote_id), principal)
    return ReissueAccessResponse(quote_id=str(quote_id), customer_token=token)

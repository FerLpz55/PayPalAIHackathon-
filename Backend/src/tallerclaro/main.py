"""Aplicación FastAPI de TallerClaro."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tallerclaro.bootstrap.settings import Settings
from tallerclaro.infrastructure.ai.service import build_ai_service
from tallerclaro.infrastructure.db.connection import Database
from tallerclaro.infrastructure.db.unit_of_work import PostgresUnitOfWork
from tallerclaro.infrastructure.payment.paypal_processor import build_payment_processor
from tallerclaro.presentation.http.exception_handlers import register as register_exception_handlers
from tallerclaro.presentation.http.routers.health import router as health_router
from tallerclaro.presentation.http.routers.orders import router as orders_router
from tallerclaro.presentation.http.routers.payments import router as payments_router
from tallerclaro.presentation.http.routers.quotes import router as quotes_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    database = getattr(app.state, "database", None)
    if database is None:
        database = Database(settings)
        try:
            database.connect()
        except Exception:
            pass
        app.state.database = database

    if getattr(app.state, "uow_factory", None) is None:
        app.state.uow_factory = lambda: PostgresUnitOfWork(
            database,
            token_secret=settings.customer_token_secret,
            token_ttl_hours=settings.customer_token_ttl_hours,
        )
    if getattr(app.state, "ai_service", None) is None:
        app.state.ai_service = build_ai_service(settings)
    if getattr(app.state, "payment_processor", None) is None:
        app.state.payment_processor = build_payment_processor(settings)
    yield
    database.close()


def create_app(
    settings: Settings | None = None,
    database: Database | None = None,
    ai_service=None,
    payment_processor=None,
) -> FastAPI:
    settings = settings if settings is not None else Settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.state.settings = settings
    if database is not None:
        app.state.database = database
    if ai_service is not None:
        app.state.ai_service = ai_service
    if payment_processor is not None:
        app.state.payment_processor = payment_processor

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(quotes_router)
    app.include_router(orders_router)
    app.include_router(payments_router)
    return app


app = create_app()

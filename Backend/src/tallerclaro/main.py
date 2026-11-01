from fastapi import FastAPI

from tallerclaro.bootstrap.settings import Settings
from tallerclaro.presentation.http.routers.health import router as health_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings if settings is not None else Settings()
    app = FastAPI(title=settings.app_name)
    app.include_router(health_router)
    return app


app = create_app()

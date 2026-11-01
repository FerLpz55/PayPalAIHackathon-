from fastapi import APIRouter

from tallerclaro.presentation.http.schemas.health import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health() -> HealthResponse:
    return HealthResponse()

"""Application health endpoint."""

from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter(tags=["system"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="检查应用是否正常运行",
)
async def get_health() -> HealthResponse:
    """Report whether the FastAPI process can serve requests."""
    return HealthResponse(status="ok")


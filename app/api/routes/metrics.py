from fastapi import APIRouter, Depends

from app.api.deps import verify_internal_token
from app.models.schemas import MetricsResponse
from app.services.metrics import MetricsService

router = APIRouter(tags=["metrics"])


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    dependencies=[Depends(verify_internal_token)],
)
async def get_metrics():
    svc = MetricsService()
    return svc.fetch_metrics()

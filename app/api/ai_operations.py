"""Protected AI Gateway operations and Prometheus endpoints."""

import hmac
import os

from fastapi import APIRouter, Header, HTTPException, Response

from app.core.config import get_aura_env
from app.infrastructure.redis.client import is_redis_available
from app.services.ai_observability import metrics_snapshot, prometheus_text
from app.services.ai_provider_router import provider_health

router = APIRouter(prefix="/internal/ai", tags=["ai-operations"])


def _authorize(authorization: str | None) -> None:
    expected = os.getenv("AI_METRICS_BEARER_TOKEN", "").strip()
    if not expected:
        if get_aura_env() == "production":
            raise HTTPException(status_code=503, detail="Operations endpoint is not configured.")
        return
    supplied = (authorization or "").removeprefix("Bearer ").strip()
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Invalid operations token.")


@router.get("/health")
def gateway_health(authorization: str | None = Header(default=None)):
    _authorize(authorization)
    return {
        "status": "operational",
        "redis_shared_state": is_redis_available(),
        "providers": provider_health.snapshot(),
        "metrics": metrics_snapshot(),
    }


@router.get("/metrics")
def gateway_metrics(authorization: str | None = Header(default=None)):
    _authorize(authorization)
    return Response(prometheus_text(), media_type="text/plain; version=0.0.4")

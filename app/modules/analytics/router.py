"""Analytics API routes."""

from fastapi import APIRouter, Depends

from app.core.deps import require_auth
from app.modules.analytics import service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/kpis")
def kpis(ctx=Depends(require_auth)):
    return service.get_kpis(ctx.company_id)


@router.get("/charts")
def charts(ctx=Depends(require_auth)):
    return service.get_charts(ctx.company_id)


@router.get("/growth")
def growth(ctx=Depends(require_auth)):
    return service.get_growth_metrics(ctx.company_id)


@router.get("/customers")
def customer_stats(ctx=Depends(require_auth)):
    return service.get_customer_statistics(ctx.company_id)


@router.get("/widgets")
def widgets(ctx=Depends(require_auth)):
    return service.get_dashboard_widgets(ctx.company_id)

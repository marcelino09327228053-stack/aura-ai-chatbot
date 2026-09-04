"""Subscription API routes."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import SubscriptionUpdateRequest
from app.core.deps import require_auth
from app.database import (
    ai_gateway_repository,
    ai_usage_repository,
    usage_repository,
)
from app.cloud.billing import repository as billing_repository
from app.services.subscription_service import (
    get_plan_catalog,
    get_plan_limits,
    get_subscription_status,
)

router = APIRouter(prefix="/subscription", tags=["subscription"])


@router.get("/plans")
def list_plans():
    return get_plan_catalog()


@router.get("/status")
def get_subscription(ctx=Depends(require_auth)):
    sub = get_subscription_status(ctx.company_id)
    usage = usage_repository.get_usage_summary(ctx.company_id)
    limits = get_plan_limits(sub["plan"] if sub else "free")
    return {
        "subscription": sub,
        "usage": usage,
        "limits": limits,
        "payment_history": billing_repository.list_payment_history(ctx.company_id),
        "billing_history": billing_repository.list_billing(ctx.company_id),
        "notification": sub.get("notification"),
        "ai_usage": ai_usage_repository.get_summary(ctx.company_id),
        "recent_ai_usage": ai_usage_repository.list_recent(ctx.company_id),
        "recent_gateway_requests": ai_gateway_repository.list_recent(ctx.company_id),
    }


@router.post("/upgrade")
def upgrade_plan(body: SubscriptionUpdateRequest, ctx=Depends(require_auth)):
    del body, ctx
    raise HTTPException(
        status_code=501,
        detail="Plan activation is not available until a verified payment webhook is configured.",
    )

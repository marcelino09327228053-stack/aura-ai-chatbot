"""Subscription API routes."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import MockPaymentEventRequest, SubscriptionUpdateRequest
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
from app.services.mock_payment_service import process_successful_payment

router = APIRouter(prefix="/subscription", tags=["subscription"])


@router.get("/plans")
def list_plans():
    return get_plan_catalog()


@router.get("/status")
def get_subscription(ctx=Depends(require_auth)):
    sub = get_subscription_status(ctx.company_id)
    usage = usage_repository.get_usage_summary(ctx.company_id)
    limits = get_plan_limits(sub["plan"] if sub else "free")
    raw_ai_usage = ai_usage_repository.get_summary(ctx.company_id)
    customer_ai_usage = {
        "total_requests": raw_ai_usage["total_requests"],
        "total_input_tokens": raw_ai_usage["total_input_tokens"],
        "total_output_tokens": raw_ai_usage["total_output_tokens"],
    }
    recent_ai_usage = [
        {
            "request_id": item["request_id"],
            "input_tokens": item["input_tokens"],
            "output_tokens": item["output_tokens"],
            "allowance_deducted_minor": item["allowance_deducted_minor"],
            "status": item["status"],
            "created_at": item["created_at"],
        }
        for item in ai_usage_repository.list_recent(ctx.company_id)
    ]
    recent_requests = [
        {
            "request_id": item["request_id"],
            "status": item["status"],
            "created_at": item["created_at"],
            "completed_at": item["completed_at"],
        }
        for item in ai_gateway_repository.list_recent(ctx.company_id)
    ]
    return {
        "subscription": sub,
        "usage": usage,
        "limits": limits,
        "payment_history": billing_repository.list_payment_history(ctx.company_id),
        "billing_history": billing_repository.list_billing(ctx.company_id),
        "notification": sub.get("notification"),
        "ai_usage": customer_ai_usage,
        "recent_ai_usage": recent_ai_usage,
        "recent_gateway_requests": recent_requests,
    }


@router.post("/upgrade")
def upgrade_plan(body: SubscriptionUpdateRequest, ctx=Depends(require_auth)):
    del body, ctx
    raise HTTPException(
        status_code=501,
        detail="Plan activation is not available until a verified payment webhook is configured.",
    )


@router.post("/mock-payment/succeeded")
def mock_payment_succeeded(body: MockPaymentEventRequest, ctx=Depends(require_auth)):
    if body.status.lower() != "succeeded":
        raise HTTPException(status_code=400, detail="Only successful mock events are supported.")
    return process_successful_payment(body.event_id, ctx.company_id, body.plan)

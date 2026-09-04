"""Subscription plan limits and checks."""

from datetime import datetime, timezone

from fastapi import HTTPException

from app.core.config import AI_PLAN_CONFIG, PLAN_LIMITS
from app.database import company_repository, subscription_repository, usage_repository


def get_plan_limits(plan: str) -> dict:
    return PLAN_LIMITS.get(plan.lower(), PLAN_LIMITS["free"])


def get_company_plan(company_id: int) -> str:
    sub = subscription_repository.get_subscription_by_company(company_id)
    if sub is None:
        return "free"
    return sub["plan"]


def get_subscription_status(company_id: int) -> dict:
    sub = subscription_repository.get_subscription_by_company(company_id)
    if sub is None:
        return {
            "plan": "free",
            "status": "active",
            "expires_at": None,
            "days_remaining": None,
            "notification": None,
        }

    plan_config = AI_PLAN_CONFIG.get(sub["plan"], {})
    sub = subscription_repository.reset_allowance_if_due(
        company_id, int(plan_config.get("monthly_ai_allowance", 0))
    ) or sub
    days_remaining = None
    notification = None
    if sub["plan"] != "free" and sub.get("expires_at"):
        expiry = datetime.fromisoformat(sub["expires_at"])
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        seconds = (expiry - datetime.now(timezone.utc)).total_seconds()
        days_remaining = max(0, int((seconds + 86399) // 86400))
        if seconds <= 0:
            if sub["status"] != "expired":
                sub = subscription_repository.mark_expired(company_id) or sub
            notification = {
                "level": "danger",
                "message": "Your MB Future Tech AI Chatbot subscription has expired. Renew to continue using AI services.",
                "action": "Renew subscription",
            }
        elif days_remaining in (1, 3, 7) or days_remaining < 7:
            notification = {
                "level": "warning",
                "message": f"Your MB Future Tech AI Chatbot subscription expires in {days_remaining} day(s).",
                "action": "Renew now",
            }

    return {
        **sub,
        "days_remaining": days_remaining,
        "notification": notification,
    }


def check_subscription_active(company_id: int) -> None:
    status = get_subscription_status(company_id)
    if status["plan"] != "free" and status["status"] != "active":
        raise HTTPException(
            status_code=402,
            detail="Your MB Future Tech AI Chatbot subscription has expired. Renew your subscription to continue.",
        )


def prepare_gateway_access(company_id: int) -> dict:
    """Reset a due cycle and enforce active, non-exhausted managed AI access."""
    status = get_subscription_status(company_id)
    if status["status"] == "suspended":
        raise HTTPException(status_code=403, detail="AI access is suspended.")
    if status["status"] not in ("active",):
        raise HTTPException(status_code=402, detail="An active subscription is required.")
    if int(status.get("remaining_allowance", 0)) <= 0:
        if status.get("monthly_ai_allowance", 0):
            # Normalize an old active row whose allowance was just consumed.
            conn_status = subscription_repository.get_subscription_by_company(company_id)
            status = conn_status or status
        raise HTTPException(status_code=402, detail="Monthly AI allowance is exhausted.")
    return status


def activate_paid_cycle(
    company_id: int,
    plan: str,
    cycle_start=None,
    cycle_end=None,
) -> dict:
    """Payment-provider-neutral activation entry point for a future webhook."""
    config = AI_PLAN_CONFIG.get(plan)
    if config is None:
        raise ValueError("Unknown subscription plan.")
    subscription = subscription_repository.activate_subscription(
        company_id,
        plan,
        int(config.get("monthly_ai_allowance", 0)),
        cycle_start,
        cycle_end,
    )
    if subscription is None:
        raise ValueError("Subscription not found.")
    return subscription


def check_can_create_company(user_id: int) -> None:
    plan = subscription_repository.get_user_plan(user_id)
    limits = get_plan_limits(plan)
    max_companies = limits["max_companies"]
    if max_companies is None:
        return
    count = company_repository.count_companies_by_owner(user_id)
    if count >= max_companies:
        raise HTTPException(
            status_code=403,
            detail=f"Your {plan} plan allows up to {max_companies} company(ies).",
        )


def check_message_limit(company_id: int) -> None:
    check_subscription_active(company_id)
    plan = get_company_plan(company_id)
    limits = get_plan_limits(plan)
    max_messages = limits["max_messages_per_day"]
    if max_messages is None:
        return
    used = usage_repository.count_messages_today(company_id)
    if used >= max_messages:
        raise HTTPException(
            status_code=429,
            detail=f"Daily message limit reached ({max_messages}) for your {plan} plan.",
        )


def get_plan_catalog() -> list[dict]:
    return [
        {
            "plan": plan,
            "monthly_ai_allowance": int(config.get("monthly_ai_allowance", 0)),
            "max_companies": config.get("max_companies"),
            "price": None,
            "currency": None,
        }
        for plan, config in AI_PLAN_CONFIG.items()
    ]

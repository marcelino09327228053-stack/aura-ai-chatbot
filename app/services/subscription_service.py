"""Subscription plan limits and checks."""

from datetime import datetime, timezone

from fastapi import HTTPException

from app.core.config import PLAN_LIMITS
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
            "plan": "free",
            "max_companies": 1,
            "max_messages_per_day": 100,
            "price": 0,
        },
        {
            "plan": "pro",
            "max_companies": 5,
            "max_messages_per_day": 5000,
            "price": 29,
        },
        {
            "plan": "enterprise",
            "max_companies": None,
            "max_messages_per_day": None,
            "price": None,
        },
    ]

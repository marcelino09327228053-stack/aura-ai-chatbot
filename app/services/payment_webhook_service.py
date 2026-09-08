"""Signed provider-neutral subscription payment webhook processing."""
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os

from fastapi import HTTPException
from app.core.config import AI_PLAN_CONFIG, PAYMENT_WEBHOOK_MAX_AGE_SECONDS
from app.referrals.repository import current_pricing
from app.database.payment_event_repository import activate_from_event

def verify_signature(raw_body: bytes, signature: str | None) -> None:
    secret = os.getenv("PAYMENT_WEBHOOK_SECRET", "").strip()
    if not secret:
        raise HTTPException(status_code=503, detail="Payment webhook is not configured.")
    supplied = (signature or "").removeprefix("sha256=").strip().lower()
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Invalid payment webhook signature.")

def process_event(raw_body: bytes, signature: str | None) -> dict:
    verify_signature(raw_body, signature)
    try: payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid payment event JSON.") from exc
    required = ("event_id", "provider", "company_id", "plan", "amount_minor", "currency", "status", "occurred_at")
    if any(key not in payload for key in required):
        raise HTTPException(status_code=400, detail="Payment event is missing required fields.")
    configured_provider = os.getenv("PAYMENT_WEBHOOK_PROVIDER", "").strip().lower()
    if configured_provider and str(payload["provider"]).lower() != configured_provider:
        raise HTTPException(status_code=400, detail="Unexpected payment provider.")
    event_type = str(payload.get("event_type", "initial_subscription")).lower()
    if event_type not in {"initial_subscription","subscription_renewal","ai_topup","refund","chargeback"}:
        raise HTTPException(status_code=400, detail="Unknown payment event type.")
    if str(payload["status"]).lower() != "succeeded":
        return {"accepted": True, "activated": False, "reason": "payment_not_successful"}
    try:
        occurred = datetime.fromisoformat(str(payload["occurred_at"]).replace("Z", "+00:00"))
        if occurred.tzinfo is None: occurred = occurred.replace(tzinfo=timezone.utc)
        if abs((datetime.now(timezone.utc) - occurred).total_seconds()) > PAYMENT_WEBHOOK_MAX_AGE_SECONDS:
            raise HTTPException(status_code=400, detail="Payment event timestamp is outside the allowed window.")
        company_id = int(payload["company_id"]); amount_minor = int(payload["amount_minor"])
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid payment event values.") from exc
    plan = str(payload["plan"]).lower(); config = AI_PLAN_CONFIG.get(plan)
    currency = str(payload["currency"]).upper()
    if not config or plan == "free": raise HTTPException(status_code=400, detail="Unknown paid plan.")
    pricing = current_pricing()
    expected = {
        "initial_subscription": int(pricing["monthly_platform_price_minor"]) + int(pricing["initial_ai_credit_minor"]),
        "subscription_renewal": int(pricing["monthly_platform_price_minor"]),
        "ai_topup": amount_minor,
        "refund": amount_minor,
        "chargeback": amount_minor,
    }[event_type]
    if event_type == "ai_topup" and amount_minor < int(pricing["minimum_ai_topup_minor"]):
        raise HTTPException(status_code=400, detail="AI top-up is below the configured minimum.")
    if event_type in {"initial_subscription","subscription_renewal"} and amount_minor != expected:
        raise HTTPException(status_code=400, detail="Payment amount does not match current pricing.")
    if currency != str(pricing["currency"]).upper():
        raise HTTPException(status_code=400, detail="Payment amount or currency does not match the plan.")
    refund_of = str(payload.get("refund_of_event_id", "")).strip() or None
    if event_type in {"refund","chargeback"} and not refund_of:
        raise HTTPException(status_code=400, detail="Refund/chargeback must reference the original payment event.")
    credit_grant = int(pricing["initial_ai_credit_minor"]) if event_type == "initial_subscription" else (amount_minor if event_type == "ai_topup" else 0)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    try:
        event, subscription, duplicate = activate_from_event(
            str(payload["event_id"]), str(payload["provider"]).lower(), company_id,
            plan, amount_minor, currency, credit_grant,
            hashlib.sha256(canonical).hexdigest(), event_type, refund_of,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"accepted": True, "activated": True, "duplicate": duplicate,
            "event": event, "subscription": subscription}

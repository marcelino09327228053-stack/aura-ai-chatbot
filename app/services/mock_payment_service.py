"""Development-only successful-payment simulator."""

from fastapi import HTTPException

from app.core.config import AI_PLAN_CONFIG, MOCK_PAYMENTS_ENABLED, get_aura_env
from app.database import mock_payment_repository
from app.services.subscription_service import activate_paid_cycle, get_subscription_status


def process_successful_payment(event_id: str, company_id: int, plan: str) -> dict:
    if get_aura_env() == "production" or not MOCK_PAYMENTS_ENABLED:
        raise HTTPException(status_code=404, detail="Mock payments are disabled.")
    event_id = event_id.strip()
    plan = plan.strip().lower()
    if not event_id or len(event_id) > 128:
        raise HTTPException(status_code=400, detail="Invalid payment event ID.")
    config = AI_PLAN_CONFIG.get(plan)
    if not config or plan == "free":
        raise HTTPException(status_code=400, detail="Unknown test subscription plan.")
    amount = int(config.get("price_minor", 0))
    currency = str(config.get("currency", "PHP"))
    event, created = mock_payment_repository.begin_event(
        event_id, company_id, plan, amount, currency
    )
    if not created:
        expected = (company_id, plan, amount, currency)
        actual = (event["company_id"], event["plan"], event["amount_minor"], event["currency"])
        if actual != expected:
            raise HTTPException(status_code=409, detail="Payment event ID is already in use.")
        if event["status"] == "completed":
            return {
                "mock": True, "duplicate": True, "event": event,
                "subscription": get_subscription_status(company_id),
            }
        raise HTTPException(status_code=409, detail="Payment event is already being processed.")
    try:
        subscription = activate_paid_cycle(company_id, plan)
        event = mock_payment_repository.set_status(event_id, "completed")
    except Exception:
        mock_payment_repository.set_status(event_id, "failed")
        raise
    return {
        "mock": True, "duplicate": False, "event": event,
        "subscription": subscription,
    }

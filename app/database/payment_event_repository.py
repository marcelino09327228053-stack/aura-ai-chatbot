"""Atomic production payment-event activation ledger."""
from datetime import datetime, timedelta, timezone
from app.database.connection import get_connection
from app.database.subscription_repository import get_subscription_by_company

def get_event(event_id: str) -> dict | None:
    row = get_connection().cursor().execute(
        "SELECT * FROM payment_webhook_events WHERE event_id=?", (event_id,)
    ).fetchone()
    return dict(row) if row else None

def activate_from_event(event_id: str, provider: str, company_id: int, plan: str,
                        amount_minor: int, currency: str, allowance_minor: int,
                        payload_hash: str) -> tuple[dict, dict, bool]:
    conn = get_connection(); cursor = conn.cursor()
    start = datetime.now(timezone.utc); end = start + timedelta(days=30)
    try:
        cursor.execute("BEGIN IMMEDIATE")
        existing = cursor.execute(
            "SELECT * FROM payment_webhook_events WHERE event_id=?", (event_id,)
        ).fetchone()
        if existing:
            conn.rollback()
            event = dict(existing)
            if event["payload_hash"] != payload_hash:
                raise ValueError("Payment event ID was reused with a different payload.")
            return event, get_subscription_by_company(company_id), True
        cursor.execute(
            """INSERT INTO payment_webhook_events
               (event_id,provider,company_id,plan,amount_minor,currency,payload_hash,status)
               VALUES (?,?,?,?,?,?,?,'processing')""",
            (event_id, provider, company_id, plan, amount_minor, currency, payload_hash),
        )
        cursor.execute(
            """UPDATE subscriptions SET plan=?,status='active',expires_at=?,
               billing_cycle_start=?,billing_cycle_end=?,plan_price_minor=?,
               monthly_ai_allowance_minor=?,ai_usage_consumed_minor=0,
               allowance_currency=?,allowance_reset_at=? WHERE company_id=?""",
            (plan, end.isoformat(), start.isoformat(), end.isoformat(), amount_minor,
             allowance_minor, currency, end.isoformat(), company_id),
        )
        if cursor.rowcount != 1: raise ValueError("Customer subscription was not found.")
        cursor.execute(
            "UPDATE payment_webhook_events SET status='completed',processed_at=? WHERE event_id=?",
            (datetime.now(timezone.utc).isoformat(), event_id),
        )
        conn.commit()
    except Exception:
        conn.rollback(); raise
    return get_event(event_id), get_subscription_by_company(company_id), False

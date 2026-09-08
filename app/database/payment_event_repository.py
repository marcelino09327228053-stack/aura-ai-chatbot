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
                        payload_hash: str, event_type: str = "initial_subscription",
                        refund_of_event_id: str | None = None) -> tuple[dict, dict, bool]:
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
            if event.get("status") == "completed":
                from app.referrals import repository as referral_repository
                if event_type in ("initial_subscription", "subscription_renewal"):
                    referral_repository.create_commission(event_id, company_id, amount_minor, currency)
            return event, get_subscription_by_company(company_id), True
        cursor.execute(
            """INSERT INTO payment_webhook_events
               (event_id,provider,company_id,plan,amount_minor,currency,payload_hash,status,event_type,refund_of_event_id)
               VALUES (?,?,?,?,?,?,?,'processing',?,?)""",
            (event_id, provider, company_id, plan, amount_minor, currency, payload_hash, event_type, refund_of_event_id),
        )
        if event_type == "ai_topup":
            cursor.execute("""UPDATE subscriptions SET ai_credit_balance_minor=ai_credit_balance_minor+?,
                monthly_ai_allowance_minor=monthly_ai_allowance_minor+? WHERE company_id=?""",
                (allowance_minor,allowance_minor,company_id))
        elif event_type in ("initial_subscription", "subscription_renewal"):
            cursor.execute("""UPDATE subscriptions SET plan=?,status='active',expires_at=?,
               billing_cycle_start=?,billing_cycle_end=?,plan_price_minor=?,allowance_currency=?,
               allowance_reset_at=?,monthly_ai_allowance_minor=monthly_ai_allowance_minor+?,
               ai_credit_balance_minor=ai_credit_balance_minor+? WHERE company_id=?""",
               (plan,end.isoformat(),start.isoformat(),end.isoformat(),amount_minor,currency,end.isoformat(),allowance_minor,allowance_minor,company_id))
        elif event_type in ("refund", "chargeback"):
            cursor.execute("UPDATE subscriptions SET status=status WHERE company_id=?", (company_id,))
        if cursor.rowcount != 1: raise ValueError("Customer subscription was not found.")
        cursor.execute(
            "UPDATE payment_webhook_events SET status='completed',processed_at=? WHERE event_id=?",
            (datetime.now(timezone.utc).isoformat(), event_id),
        )
        conn.commit()
    except Exception:
        conn.rollback(); raise
    event = get_event(event_id)
    from app.referrals import repository as referral_repository
    if event_type in ("initial_subscription", "subscription_renewal"):
        referral_repository.create_commission(event_id, company_id, amount_minor, currency)
    elif event_type in ("refund", "chargeback") and refund_of_event_id:
        referral_repository.reverse_commission(event_id, refund_of_event_id)
    return event, get_subscription_by_company(company_id), False

"""Billing data access."""

from datetime import datetime, timedelta, timezone

from app.cloud.billing.plans import TRIAL_DAYS, get_amount
from app.infrastructure.database import get_connection


def create_billing_record(
    company_id: int,
    plan: str,
    cycle: str = "monthly",
    status: str = "active",
) -> dict:
    amount = get_amount(plan, cycle)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO billing (company_id, plan, amount, status, billing_cycle)
        VALUES (?, ?, ?, ?, ?)
        """,
        (company_id, plan, amount, status, cycle),
    )
    conn.commit()
    return get_billing_record(cursor.lastrowid)


def get_billing_record(billing_id: int) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute("SELECT * FROM billing WHERE id = ?", (billing_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def list_billing(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM billing WHERE company_id = ? ORDER BY created_at DESC",
        (company_id,),
    )
    return [dict(r) for r in cursor.fetchall()]


def record_payment(
    company_id: int,
    billing_id: int | None,
    amount: float,
    method: str = "card",
    status: str = "completed",
) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO payment_history (company_id, billing_id, amount, method, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        (company_id, billing_id, amount, method, status),
    )
    conn.commit()
    cursor.execute("SELECT * FROM payment_history WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_payment_history(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT * FROM payment_history
        WHERE company_id = ? ORDER BY created_at DESC
        """,
        (company_id,),
    )
    return [dict(r) for r in cursor.fetchall()]


def start_trial(company_id: int) -> dict:
    expires = datetime.now(timezone.utc) + timedelta(days=TRIAL_DAYS)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM trial_accounts WHERE company_id = ?",
        (company_id,),
    )
    if cursor.fetchone():
        cursor.execute(
            "SELECT * FROM trial_accounts WHERE company_id = ?",
            (company_id,),
        )
        return dict(cursor.fetchone())
    cursor.execute(
        """
        INSERT INTO trial_accounts (company_id, expires_at, status)
        VALUES (?, ?, 'active')
        """,
        (company_id, expires.isoformat()),
    )
    conn.commit()
    billing = create_billing_record(company_id, "pro", cycle="trial", status="trial")
    record_payment(company_id, billing["id"], 0.0, method="trial", status="completed")
    cursor.execute(
        "SELECT * FROM trial_accounts WHERE company_id = ?",
        (company_id,),
    )
    return dict(cursor.fetchone())


def get_trial(company_id: int) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM trial_accounts WHERE company_id = ?",
        (company_id,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None

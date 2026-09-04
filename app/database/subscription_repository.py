"""Subscription data access."""

from datetime import datetime, timedelta, timezone

from app.database.connection import get_connection


def create_subscription(company_id: int, plan: str = "free") -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO subscriptions (company_id, plan, status)
        VALUES (?, ?, 'active')
        """,
        (company_id, plan),
    )
    conn.commit()
    return get_subscription_by_company(company_id)


def get_subscription_by_company(company_id: int) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT id, company_id, plan, status, expires_at, created_at
        FROM subscriptions WHERE company_id = ?
        """,
        (company_id,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "company_id": row["company_id"],
        "plan": row["plan"],
        "status": row["status"],
        "expires_at": row["expires_at"],
        "created_at": row["created_at"],
    }


def get_user_plan(user_id: int) -> str:
    """Return the highest plan among a user's companies (for company limit checks)."""
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT s.plan FROM subscriptions s
        JOIN companies c ON c.id = s.company_id
        WHERE c.owner_id = ?
        """,
        (user_id,),
    )
    plans = [row["plan"] for row in cursor.fetchall()]
    if "enterprise" in plans:
        return "enterprise"
    if "pro" in plans:
        return "pro"
    return "free"


def update_subscription_plan(
    company_id: int,
    plan: str,
    duration_days: int = 30,
) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    expires_at = None
    if plan != "free":
        current = get_subscription_by_company(company_id)
        start = datetime.now(timezone.utc)
        if current and current.get("expires_at"):
            try:
                current_expiry = datetime.fromisoformat(current["expires_at"])
                if current_expiry.tzinfo is None:
                    current_expiry = current_expiry.replace(tzinfo=timezone.utc)
                if current_expiry > start:
                    start = current_expiry
            except ValueError:
                pass
        expires_at = (start + timedelta(days=duration_days)).isoformat()
    cursor.execute(
        """
        UPDATE subscriptions
        SET plan = ?, status = 'active', expires_at = ?
        WHERE company_id = ?
        """,
        (plan, expires_at, company_id),
    )
    conn.commit()
    if cursor.rowcount == 0:
        return None
    return get_subscription_by_company(company_id)


def mark_expired(company_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE subscriptions SET status = 'expired' WHERE company_id = ?",
        (company_id,),
    )
    conn.commit()
    return get_subscription_by_company(company_id)

"""Subscription data access."""

from datetime import datetime, timedelta, timezone

from app.database.connection import get_connection


def create_subscription(company_id: int, plan: str = "test") -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO subscriptions (company_id, plan, status)
        VALUES (?, ?, 'inactive')
        """,
        (company_id, plan),
    )
    conn.commit()
    return get_subscription_by_company(company_id)


def get_subscription_by_company(company_id: int) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT id, company_id, plan, status, expires_at, created_at,
               billing_cycle_start, billing_cycle_end, plan_price_minor,
               monthly_ai_allowance_minor, ai_usage_consumed_minor,
               allowance_currency, allowance_reset_at
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
        "billing_cycle_start": row["billing_cycle_start"],
        "billing_cycle_end": row["billing_cycle_end"],
        "plan_price_minor": row["plan_price_minor"],
        "monthly_ai_allowance_minor": row["monthly_ai_allowance_minor"],
        "ai_usage_consumed_minor": row["ai_usage_consumed_minor"],
        "remaining_allowance_minor": max(
            0, row["monthly_ai_allowance_minor"] - row["ai_usage_consumed_minor"]
        ),
        "allowance_currency": row["allowance_currency"],
        "allowance_reset_at": row["allowance_reset_at"],
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
    if "test" in plans:
        return "test"
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


def activate_subscription(
    company_id: int,
    plan: str,
    plan_price_minor: int,
    monthly_ai_allowance_minor: int,
    allowance_currency: str,
    cycle_start: datetime | None = None,
    cycle_end: datetime | None = None,
) -> dict | None:
    """Activate a paid billing cycle. Future payment webhooks call this function."""
    start = cycle_start or datetime.now(timezone.utc)
    end = cycle_end or (start + timedelta(days=30))
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE subscriptions
        SET plan = ?, status = 'active', expires_at = ?,
            billing_cycle_start = ?, billing_cycle_end = ?,
            plan_price_minor = ?, monthly_ai_allowance_minor = ?,
            ai_usage_consumed_minor = 0, allowance_currency = ?, allowance_reset_at = ?
        WHERE company_id = ?
        """,
        (
            plan,
            end.isoformat(),
            start.isoformat(),
            end.isoformat(),
            max(0, int(plan_price_minor)),
            max(0, int(monthly_ai_allowance_minor)),
            allowance_currency,
            end.isoformat(),
            company_id,
        ),
    )
    conn.commit()
    return get_subscription_by_company(company_id) if cursor.rowcount else None


def reset_allowance_if_due(
    company_id: int, monthly_ai_allowance_minor: int
) -> dict | None:
    current = get_subscription_by_company(company_id)
    if not current or not current.get("billing_cycle_end"):
        return current
    try:
        cycle_end = datetime.fromisoformat(current["billing_cycle_end"])
        if cycle_end.tzinfo is None:
            cycle_end = cycle_end.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return current
    now = datetime.now(timezone.utc)
    if cycle_end > now:
        return current
    # Advance complete 30-day cycles so delayed jobs do not reset repeatedly.
    next_end = cycle_end
    while next_end <= now:
        next_end += timedelta(days=30)
    conn = get_connection()
    conn.cursor().execute(
        """
        UPDATE subscriptions
        SET status = 'active', billing_cycle_start = ?, billing_cycle_end = ?,
            expires_at = ?, monthly_ai_allowance_minor = ?,
            ai_usage_consumed_minor = 0,
            allowance_reset_at = ?
        WHERE company_id = ? AND status != 'suspended'
        """,
        (
            (next_end - timedelta(days=30)).isoformat(),
            next_end.isoformat(),
            next_end.isoformat(),
            max(0, int(monthly_ai_allowance_minor)),
            next_end.isoformat(),
            company_id,
        ),
    )
    conn.commit()
    return get_subscription_by_company(company_id)


def deduct_allowance(company_id: int, amount_minor: int) -> bool:
    """Atomically deduct allowance minor units without allowing a negative balance."""
    amount_minor = max(0, int(amount_minor))
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE subscriptions
        SET ai_usage_consumed_minor = ai_usage_consumed_minor + ?,
            status = CASE
                WHEN ai_usage_consumed_minor + ? >= monthly_ai_allowance_minor THEN 'exhausted'
                ELSE status
            END
        WHERE company_id = ? AND status = 'active'
          AND ai_usage_consumed_minor + ? <= monthly_ai_allowance_minor
        """,
        (amount_minor, amount_minor, company_id, amount_minor),
    )
    conn.commit()
    return cursor.rowcount == 1


def mark_expired(company_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE subscriptions SET status = 'expired' WHERE company_id = ?",
        (company_id,),
    )
    conn.commit()
    return get_subscription_by_company(company_id)

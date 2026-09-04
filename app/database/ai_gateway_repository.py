"""Persistent, company-scoped request ledger for the managed AI Gateway."""

from app.database.connection import get_connection


def get_request(request_id: str) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM ai_gateway_requests WHERE request_id = ?", (request_id,)
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def begin_request(request_id: str, company_id: int, user_id: int | None) -> tuple[dict, bool]:
    """Create an idempotency record; return (record, created)."""
    existing = get_request(request_id)
    if existing:
        return existing, False
    conn = get_connection()
    try:
        conn.cursor().execute(
            """
            INSERT INTO ai_gateway_requests (request_id, company_id, user_id, status)
            VALUES (?, ?, ?, 'pending')
            """,
            (request_id, company_id, user_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        existing = get_request(request_id)
        if existing:
            return existing, False
        raise
    return get_request(request_id), True


def complete_request(
    request_id: str,
    provider: str,
    model: str,
    response_text: str,
    input_tokens: int,
    output_tokens: int,
    provider_cost_usd: float | None,
    allowance_deducted_minor: int,
    attempt_count: int,
) -> dict:
    conn = get_connection()
    conn.cursor().execute(
        """
        UPDATE ai_gateway_requests
        SET provider = ?, model = ?, response_text = ?, input_tokens = ?,
            output_tokens = ?, provider_cost_usd = ?, allowance_deducted_minor = ?,
            attempt_count = ?, status = 'success', completed_at = datetime('now')
        WHERE request_id = ? AND status = 'pending'
        """,
        (
            provider,
            model,
            response_text,
            input_tokens,
            output_tokens,
            provider_cost_usd,
            allowance_deducted_minor,
            attempt_count,
            request_id,
        ),
    )
    conn.commit()
    return get_request(request_id)


def finalize_metered_success(
    request_id: str,
    company_id: int,
    provider: str,
    model: str,
    response_text: str,
    input_tokens: int,
    output_tokens: int,
    provider_cost_usd: float,
    allowance_deducted_minor: int,
    attempt_count: int,
) -> dict | None:
    """Atomically deduct allowance, log usage, and complete one request."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute(
            """UPDATE subscriptions
               SET ai_usage_consumed_minor = ai_usage_consumed_minor + ?,
                   status = CASE WHEN ai_usage_consumed_minor + ? >= monthly_ai_allowance_minor
                                 THEN 'exhausted' ELSE status END
               WHERE company_id = ? AND status = 'active'
                 AND ai_usage_consumed_minor + ? <= monthly_ai_allowance_minor
                 AND EXISTS (SELECT 1 FROM ai_gateway_requests
                             WHERE request_id = ? AND company_id = ? AND status = 'pending')""",
            (allowance_deducted_minor, allowance_deducted_minor, company_id,
             allowance_deducted_minor, request_id, company_id),
        )
        if cursor.rowcount != 1:
            conn.rollback()
            return None
        cursor.execute(
            """INSERT INTO ai_provider_usage
               (company_id, provider, model, input_tokens, output_tokens,
                estimated_cost, status, request_id, allowance_deducted_minor)
               VALUES (?, ?, ?, ?, ?, ?, 'success', ?, ?)""",
            (company_id, provider, model, input_tokens, output_tokens,
             provider_cost_usd, request_id, allowance_deducted_minor),
        )
        cursor.execute(
            """UPDATE ai_gateway_requests
               SET provider=?, model=?, response_text=?, input_tokens=?, output_tokens=?,
                   provider_cost_usd=?, allowance_deducted_minor=?, attempt_count=?,
                   status='success', completed_at=datetime('now')
               WHERE request_id=? AND company_id=? AND status='pending'""",
            (provider, model, response_text, input_tokens, output_tokens,
             provider_cost_usd, allowance_deducted_minor, attempt_count,
             request_id, company_id),
        )
        if cursor.rowcount != 1:
            conn.rollback()
            return None
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return get_request(request_id)


def fail_request(
    request_id: str,
    error_code: str,
    attempt_count: int,
    provider: str = "",
    model: str = "",
) -> dict:
    conn = get_connection()
    conn.cursor().execute(
        """
        UPDATE ai_gateway_requests
        SET provider = ?, model = ?, status = 'failed', error_code = ?,
            attempt_count = ?, completed_at = datetime('now')
        WHERE request_id = ? AND status = 'pending'
        """,
        (provider, model, error_code[:120], attempt_count, request_id),
    )
    conn.commit()
    return get_request(request_id)


def list_recent(company_id: int, limit: int = 50) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT request_id, provider, model, input_tokens, output_tokens,
               provider_cost_usd, allowance_deducted_minor, status, error_code,
               attempt_count, created_at, completed_at
        FROM ai_gateway_requests
        WHERE company_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (company_id, limit),
    )
    return [dict(row) for row in cursor.fetchall()]

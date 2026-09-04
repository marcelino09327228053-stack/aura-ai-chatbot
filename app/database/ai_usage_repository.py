"""AI provider usage tracking for customer billing visibility."""

from app.database.connection import get_connection


def record_usage(
    company_id: int,
    provider: str,
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    estimated_cost: float | None = None,
    status: str = "success",
    request_id: str | None = None,
    allowance_deducted: int = 0,
) -> None:
    conn = get_connection()
    conn.cursor().execute(
        """
        INSERT INTO ai_provider_usage
        (company_id, provider, model, input_tokens, output_tokens, estimated_cost,
         status, request_id, allowance_deducted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            company_id,
            provider,
            model,
            input_tokens,
            output_tokens,
            estimated_cost,
            status,
            request_id,
            allowance_deducted,
        ),
    )
    conn.commit()


def get_summary(company_id: int) -> dict:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT provider, COUNT(*) requests,
               COALESCE(SUM(input_tokens), 0) input_tokens,
               COALESCE(SUM(output_tokens), 0) output_tokens,
               SUM(estimated_cost) estimated_cost
        FROM ai_provider_usage
        WHERE company_id = ?
        GROUP BY provider
        ORDER BY provider
        """,
        (company_id,),
    )
    providers = [dict(row) for row in cursor.fetchall()]
    return {
        "providers": providers,
        "total_requests": sum(item["requests"] for item in providers),
        "total_input_tokens": sum(item["input_tokens"] for item in providers),
        "total_output_tokens": sum(item["output_tokens"] for item in providers),
        "estimated_cost": (
            sum(item["estimated_cost"] or 0 for item in providers)
            if any(item["estimated_cost"] is not None for item in providers)
            else None
        ),
    }


def list_recent(company_id: int, limit: int = 50) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT request_id, provider, model, input_tokens, output_tokens,
               estimated_cost, allowance_deducted, status, created_at
        FROM ai_provider_usage
        WHERE company_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (company_id, limit),
    )
    return [dict(row) for row in cursor.fetchall()]

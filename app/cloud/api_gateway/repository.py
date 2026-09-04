"""API Gateway data access."""

import json
import secrets

from app.core.security import hash_token
from app.infrastructure.database import get_connection


def generate_key() -> tuple[str, str, str]:
    raw = f"aura_ck_{secrets.token_urlsafe(32)}"
    return raw, hash_token(raw), raw[:12]


def create_api_key(
    company_id: int,
    name: str,
    scopes: str = "read,write",
    rate_limit: int = 60,
) -> dict:
    raw, key_hash, prefix = generate_key()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO cloud_api_keys (company_id, name, key_hash, key_prefix, scopes, rate_limit)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (company_id, name, key_hash, prefix, scopes, rate_limit),
    )
    conn.commit()
    cursor.execute("SELECT * FROM cloud_api_keys WHERE id = ?", (cursor.lastrowid,))
    row = dict(cursor.fetchone())
    row["key"] = raw
    return row


def get_key_by_hash(key_hash: str) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM cloud_api_keys WHERE key_hash = ? AND revoked_at IS NULL",
        (key_hash,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def list_api_keys(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT id, company_id, name, key_prefix, scopes, rate_limit,
               created_at, last_used_at, revoked_at
        FROM cloud_api_keys WHERE company_id = ?
        ORDER BY created_at DESC
        """,
        (company_id,),
    )
    return [dict(r) for r in cursor.fetchall()]


def revoke_api_key(company_id: int, key_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE cloud_api_keys SET revoked_at = datetime('now')
        WHERE company_id = ? AND id = ? AND revoked_at IS NULL
        """,
        (company_id, key_id),
    )
    conn.commit()
    return True


def touch_api_key(key_id: int) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE cloud_api_keys SET last_used_at = datetime('now') WHERE id = ?",
        (key_id,),
    )
    conn.commit()


def log_usage(company_id: int, api_key_id: int | None, endpoint: str, method: str) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO api_gateway_usage (company_id, api_key_id, endpoint, method)
        VALUES (?, ?, ?, ?)
        """,
        (company_id, api_key_id, endpoint, method),
    )
    conn.commit()


def count_usage_since(company_id: int, api_key_id: int, since_minutes: int = 1) -> int:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT COUNT(*) FROM api_gateway_usage
        WHERE company_id = ? AND api_key_id = ?
        AND created_at >= datetime('now', ?)
        """,
        (company_id, api_key_id, f"-{since_minutes} minutes"),
    )
    return cursor.fetchone()[0]


def usage_summary(company_id: int, limit: int = 100) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT endpoint, method, COUNT(*) as count
        FROM api_gateway_usage
        WHERE company_id = ?
        GROUP BY endpoint, method
        ORDER BY count DESC LIMIT ?
        """,
        (company_id, limit),
    )
    return [dict(r) for r in cursor.fetchall()]

"""Encrypted customer-owned AI provider credentials."""

from app.cloud.security import decrypt_value, encrypt_value
from app.database.connection import get_connection


def save_key(company_id: int, provider: str, api_key: str) -> dict:
    conn = get_connection()
    conn.cursor().execute(
        """
        INSERT INTO ai_provider_credentials
        (company_id, provider, encrypted_key, key_suffix)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(company_id, provider) DO UPDATE SET
            encrypted_key = excluded.encrypted_key,
            key_suffix = excluded.key_suffix,
            updated_at = datetime('now')
        """,
        (company_id, provider, encrypt_value(api_key), api_key[-4:]),
    )
    conn.commit()
    return get_status(company_id, provider)


def get_key(company_id: int, provider: str) -> str | None:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT encrypted_key FROM ai_provider_credentials
        WHERE company_id = ? AND provider = ?
        """,
        (company_id, provider),
    )
    row = cursor.fetchone()
    return decrypt_value(row["encrypted_key"]) if row else None


def get_status(company_id: int, provider: str) -> dict:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT provider, key_suffix, connected_at, updated_at
        FROM ai_provider_credentials
        WHERE company_id = ? AND provider = ?
        """,
        (company_id, provider),
    )
    row = cursor.fetchone()
    return dict(row) if row else {}


def list_status(company_id: int) -> dict[str, dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT provider, key_suffix, connected_at, updated_at
        FROM ai_provider_credentials WHERE company_id = ?
        """,
        (company_id,),
    )
    return {row["provider"]: dict(row) for row in cursor.fetchall()}


def delete_key(company_id: int, provider: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        DELETE FROM ai_provider_credentials
        WHERE company_id = ? AND provider = ?
        """,
        (company_id, provider),
    )
    conn.commit()
    return cursor.rowcount > 0

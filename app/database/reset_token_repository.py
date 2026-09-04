"""Password reset token storage."""

import sqlite3
from datetime import datetime, timedelta, timezone

from app.database.connection import get_connection


def create_reset_token(user_id: int, token_hash: str, hours: int) -> None:
    expires = datetime.now(timezone.utc) + timedelta(hours=hours)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM password_reset_tokens WHERE user_id = ?",
        (user_id,),
    )
    cursor.execute(
        """
        INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
        VALUES (?, ?, ?)
        """,
        (user_id, token_hash, expires.isoformat()),
    )
    conn.commit()


def consume_reset_token(token_hash: str) -> int | None:
    """Validate token and return user_id if valid. Marks token as used."""
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT id, user_id, expires_at, used_at
        FROM password_reset_tokens
        WHERE token_hash = ?
        """,
        (token_hash,),
    )
    row = cursor.fetchone()
    if not row or row["used_at"]:
        return None

    expires_at = datetime.fromisoformat(row["expires_at"])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expires_at:
        return None

    conn = get_connection()
    conn.cursor().execute(
        "UPDATE password_reset_tokens SET used_at = datetime('now') WHERE id = ?",
        (row["id"],),
    )
    conn.commit()
    return row["user_id"]

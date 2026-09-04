"""External sign-in identity mappings."""

import sqlite3

from app.database.connection import get_connection


def _row(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row else None


def get_identity(provider: str, subject: str) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM oauth_identities WHERE provider = ? AND subject = ?",
        (provider, subject),
    )
    return _row(cursor.fetchone())


def save_identity(user_id: int, provider: str, subject: str, email: str) -> dict:
    conn = get_connection()
    conn.cursor().execute(
        """
        INSERT INTO oauth_identities (user_id, provider, subject, email)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(provider, subject) DO UPDATE SET
            email = excluded.email,
            updated_at = datetime('now')
        """,
        (user_id, provider, subject, email.lower().strip()),
    )
    conn.commit()
    identity = get_identity(provider, subject)
    if identity is None:
        raise RuntimeError("OAuth identity was not saved.")
    return identity

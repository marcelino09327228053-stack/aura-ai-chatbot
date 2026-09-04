"""One-time email login code persistence."""

from datetime import datetime, timezone

from app.database.connection import get_connection


def create_code(email: str, code_hash: str, expires_at: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    normalized_email = email.lower().strip()
    cursor.execute(
        """
        UPDATE email_login_codes
        SET used_at = ?
        WHERE email = ? AND used_at IS NULL
        """,
        (datetime.now(timezone.utc).isoformat(), normalized_email),
    )
    cursor.execute(
        """
        INSERT INTO email_login_codes (email, code_hash, expires_at)
        VALUES (?, ?, ?)
        """,
        (normalized_email, code_hash, expires_at),
    )
    conn.commit()
    return get_latest_code(normalized_email)


def get_latest_code(email: str) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT id, email, code_hash, expires_at, attempts, used_at, created_at
        FROM email_login_codes
        WHERE email = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (email.lower().strip(),),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def record_failed_attempt(code_id: int) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE email_login_codes SET attempts = attempts + 1 WHERE id = ?",
        (code_id,),
    )
    conn.commit()


def consume_code(code_id: int) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE email_login_codes SET used_at = ? WHERE id = ?",
        (datetime.now(timezone.utc).isoformat(), code_id),
    )
    conn.commit()

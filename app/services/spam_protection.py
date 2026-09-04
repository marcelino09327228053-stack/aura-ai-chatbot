"""Small persistent spam gate shared by external messaging channels."""

import hashlib
import re
import time

from app.database.connection import get_connection

WINDOW_SECONDS = 60
MAX_MESSAGES_PER_WINDOW = 10
MAX_IDENTICAL_MESSAGES = 4
BLOCK_SECONDS = 15 * 60


def _message_hash(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.casefold()).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def check_message(company_id: int, channel: str, sender_id: str, text: str, now: int | None = None) -> dict:
    """Record one message and return whether the sender is temporarily blocked."""
    current = int(now if now is not None else time.time())
    message_hash = _message_hash(text)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT * FROM channel_spam_state
           WHERE company_id = ? AND channel = ? AND sender_id = ?""",
        (company_id, channel, sender_id),
    )
    row = cursor.fetchone()

    if row and int(row["blocked_until"]) > current:
        return {"blocked": True, "new_block": False, "blocked_until": int(row["blocked_until"])}

    if not row or current - int(row["window_started_at"]) >= WINDOW_SECONDS:
        window_started_at = current
        message_count = 1
        repeated_count = 1
    else:
        window_started_at = int(row["window_started_at"])
        message_count = int(row["message_count"]) + 1
        repeated_count = int(row["repeated_count"]) + 1 if row["last_message_hash"] == message_hash else 1

    should_block = (
        message_count > MAX_MESSAGES_PER_WINDOW
        or repeated_count >= MAX_IDENTICAL_MESSAGES
    )
    blocked_until = current + BLOCK_SECONDS if should_block else 0
    cursor.execute(
        """
        INSERT INTO channel_spam_state
        (company_id, channel, sender_id, window_started_at, message_count,
         last_message_hash, repeated_count, blocked_until)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(company_id, channel, sender_id) DO UPDATE SET
          window_started_at = excluded.window_started_at,
          message_count = excluded.message_count,
          last_message_hash = excluded.last_message_hash,
          repeated_count = excluded.repeated_count,
          blocked_until = excluded.blocked_until,
          updated_at = datetime('now')
        """,
        (company_id, channel, sender_id, window_started_at, message_count,
         message_hash, repeated_count, blocked_until),
    )
    conn.commit()
    return {"blocked": should_block, "new_block": should_block, "blocked_until": blocked_until}


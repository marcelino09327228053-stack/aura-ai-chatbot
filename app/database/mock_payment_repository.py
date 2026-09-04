"""Idempotent storage for local test payment events."""

from datetime import datetime, timezone
import sqlite3

from app.database.connection import get_connection


def get_event(event_id: str) -> dict | None:
    row = get_connection().cursor().execute(
        """SELECT event_id, company_id, plan, amount_minor, currency, status,
                  created_at, processed_at
           FROM mock_payment_events WHERE event_id = ?""",
        (event_id,),
    ).fetchone()
    return dict(row) if row else None


def begin_event(event_id: str, company_id: int, plan: str,
                amount_minor: int, currency: str) -> tuple[dict, bool]:
    conn = get_connection()
    try:
        conn.cursor().execute(
            """INSERT INTO mock_payment_events
               (event_id, company_id, plan, amount_minor, currency, status)
               VALUES (?, ?, ?, ?, ?, 'processing')""",
            (event_id, company_id, plan, amount_minor, currency),
        )
        conn.commit()
        return get_event(event_id), True
    except sqlite3.IntegrityError:
        conn.rollback()
        return get_event(event_id), False


def set_status(event_id: str, status: str) -> dict | None:
    conn = get_connection()
    processed_at = datetime.now(timezone.utc).isoformat() if status == "completed" else None
    conn.cursor().execute(
        "UPDATE mock_payment_events SET status = ?, processed_at = ? WHERE event_id = ?",
        (status, processed_at, event_id),
    )
    conn.commit()
    return get_event(event_id)

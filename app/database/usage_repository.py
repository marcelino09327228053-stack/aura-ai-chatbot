"""Daily usage tracking for plan limits."""

import sqlite3

from app.database.connection import get_connection


def count_messages_today(company_id: int) -> int:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT COUNT(*) FROM usage_logs
        WHERE company_id = ?
          AND event_type = 'message'
          AND date(created_at) = CURRENT_DATE
        """,
        (company_id,),
    )
    return cursor.fetchone()[0]


def record_message(company_id: int) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO usage_logs (company_id, event_type) VALUES (?, 'message')",
        (company_id,),
    )
    conn.commit()


def get_usage_summary(company_id: int) -> dict:
    return {
        "messages_today": count_messages_today(company_id),
    }

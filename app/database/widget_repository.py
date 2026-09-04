"""Company-scoped settings for the public website chat widget."""

import json
import secrets
import sqlite3

from app.database.connection import get_connection


def _to_dict(row: sqlite3.Row, include_company_id: bool = True) -> dict:
    result = {
        "public_token": row["public_token"],
        "enabled": bool(row["enabled"]),
        "title": row["title"],
        "welcome_message": row["welcome_message"],
        "primary_color": row["primary_color"],
        "position": row["position"],
        "allowed_domains": json.loads(row["allowed_domains"] or "[]"),
        "updated_at": row["updated_at"],
    }
    if include_company_id:
        result["company_id"] = row["company_id"]
    return result


def get_or_create(company_id: int) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM widget_settings WHERE company_id = ?", (company_id,))
    row = cursor.fetchone()
    if row is None:
        cursor.execute(
            "INSERT INTO widget_settings (company_id, public_token) VALUES (?, ?)",
            (company_id, secrets.token_urlsafe(24)),
        )
        conn.commit()
        cursor.execute("SELECT * FROM widget_settings WHERE company_id = ?", (company_id,))
        row = cursor.fetchone()
    return _to_dict(row)


def get_by_token(public_token: str) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute("SELECT * FROM widget_settings WHERE public_token = ?", (public_token,))
    row = cursor.fetchone()
    return _to_dict(row) if row else None


def update(company_id: int, values: dict) -> dict:
    current = get_or_create(company_id)
    conn = get_connection()
    conn.cursor().execute(
        """
        UPDATE widget_settings
        SET enabled = ?, title = ?, welcome_message = ?,
            primary_color = ?, position = ?, allowed_domains = ?,
            updated_at = datetime('now')
        WHERE company_id = ?
        """,
        (
            int(values.get("enabled", current["enabled"])),
            values.get("title", current["title"]).strip(),
            values.get("welcome_message", current["welcome_message"]).strip(),
            values.get("primary_color", current["primary_color"]),
            values.get("position", current["position"]),
            json.dumps(values.get("allowed_domains", current["allowed_domains"])),
            company_id,
        ),
    )
    conn.commit()
    return get_or_create(company_id)


def record_event(
    company_id: int,
    event_type: str,
    session_id: str = "",
    question: str = "",
    answer_source: str = "",
    origin: str = "",
) -> None:
    conn = get_connection()
    conn.cursor().execute(
        """
        INSERT INTO widget_events
            (company_id, session_id, event_type, question, answer_source, origin)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            company_id,
            session_id[:100],
            event_type[:40],
            question[:1000],
            answer_source[:40],
            origin[:300],
        ),
    )
    conn.commit()


def get_analytics(company_id: int, days: int = 30) -> dict:
    cursor = get_connection().cursor()
    window = f"-{max(1, min(days, 365))} days"
    cursor.execute(
        """
        SELECT event_type, COUNT(*) AS total
        FROM widget_events
        WHERE company_id = ? AND created_at >= datetime('now', ?)
        GROUP BY event_type
        """,
        (company_id, window),
    )
    counts = {row["event_type"]: row["total"] for row in cursor.fetchall()}
    cursor.execute(
        """
        SELECT question, COUNT(*) AS total
        FROM widget_events
        WHERE company_id = ? AND event_type = 'question'
          AND created_at >= datetime('now', ?)
        GROUP BY LOWER(question)
        ORDER BY total DESC, MAX(created_at) DESC
        LIMIT 10
        """,
        (company_id, window),
    )
    top_questions = [
        {"question": row["question"], "count": row["total"]} for row in cursor.fetchall()
    ]
    cursor.execute(
        """
        SELECT question, COUNT(*) AS total, MAX(created_at) AS last_seen
        FROM widget_events
        WHERE company_id = ? AND event_type = 'unanswered'
          AND created_at >= datetime('now', ?)
        GROUP BY LOWER(question)
        ORDER BY total DESC, last_seen DESC
        LIMIT 25
        """,
        (company_id, window),
    )
    unanswered = [
        {"question": row["question"], "count": row["total"], "last_seen": row["last_seen"]}
        for row in cursor.fetchall()
    ]
    conversations = counts.get("conversation_started", 0)
    messages = counts.get("question", 0)
    return {
        "period_days": max(1, min(days, 365)),
        "widget_loads": counts.get("widget_loaded", 0),
        "conversations": conversations,
        "messages": messages,
        "unanswered_count": counts.get("unanswered", 0),
        "messages_per_conversation": round(messages / conversations, 2)
        if conversations
        else 0,
        "top_questions": top_questions,
        "unanswered_questions": unanswered,
    }


def rotate_token(company_id: int) -> dict:
    get_or_create(company_id)
    conn = get_connection()
    conn.cursor().execute(
        """
        UPDATE widget_settings
        SET public_token = ?, updated_at = datetime('now')
        WHERE company_id = ?
        """,
        (secrets.token_urlsafe(24), company_id),
    )
    conn.commit()
    return get_or_create(company_id)

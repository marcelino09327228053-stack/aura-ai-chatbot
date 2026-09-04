"""Per-company conversation history."""

import sqlite3
import uuid

from app.database.connection import get_connection


def add_message(company_id: int, session_id: str, role: str, content: str) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO conversations (company_id, session_id, role, content)
        VALUES (?, ?, ?, ?)
        """,
        (company_id, session_id, role, content),
    )
    conn.commit()


def list_messages(company_id: int, session_id: str, limit: int = 50) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT id, session_id, role, content, created_at
        FROM conversations
        WHERE company_id = ? AND session_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (company_id, session_id, limit),
    )
    rows = cursor.fetchall()
    return [
        {
            "id": row["id"],
            "session_id": row["session_id"],
            "role": row["role"],
            "content": row["content"],
            "created_at": row["created_at"],
        }
        for row in reversed(rows)
    ]


def count_messages(company_id: int, session_id: str) -> int:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT COUNT(*) AS total FROM conversations WHERE company_id = ? AND session_id = ?",
        (company_id, session_id),
    )
    return int(cursor.fetchone()["total"])


def list_sessions(company_id: int, limit: int = 30) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT
            c.session_id,
            MIN(c.created_at) AS created_at,
            MAX(c.created_at) AS updated_at,
            COUNT(*) AS message_count,
            (
                SELECT content
                FROM conversations AS first_message
                WHERE first_message.company_id = c.company_id
                  AND first_message.session_id = c.session_id
                  AND first_message.role = 'user'
                ORDER BY first_message.created_at ASC, first_message.id ASC
                LIMIT 1
            ) AS title
        FROM conversations AS c
        WHERE c.company_id = ?
        GROUP BY c.session_id
        ORDER BY MAX(c.created_at) DESC
        LIMIT ?
        """,
        (company_id, limit),
    )
    return [
        {
            "session_id": row["session_id"],
            "title": (row["title"] or "New conversation")[:80],
            "message_count": row["message_count"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in cursor.fetchall()
    ]


def delete_session(company_id: int, session_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM conversations WHERE company_id = ? AND session_id = ?",
        (company_id, session_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def new_session_id() -> str:
    return str(uuid.uuid4())


def ensure_support_conversation(company_id: int, session_id: str) -> dict:
    conn = get_connection()
    conn.cursor().execute(
        """
        INSERT INTO support_conversations (company_id, session_id)
        VALUES (?, ?)
        ON CONFLICT(company_id, session_id) DO UPDATE SET
            last_activity_at = datetime('now')
        """,
        (company_id, session_id),
    )
    conn.commit()
    return get_support_conversation(company_id, session_id)


def get_support_conversation(company_id: int, session_id: str) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM support_conversations WHERE company_id = ? AND session_id = ?",
        (company_id, session_id),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def update_support_conversation(company_id: int, session_id: str, values: dict) -> dict:
    current = ensure_support_conversation(company_id, session_id)
    conn = get_connection()
    conn.cursor().execute(
        """
        UPDATE support_conversations
        SET status = ?, mode = ?, assigned_user_id = ?,
            customer_name = ?, customer_email = ?,
            last_activity_at = datetime('now')
        WHERE company_id = ? AND session_id = ?
        """,
        (
            values.get("status", current["status"]),
            values.get("mode", current["mode"]),
            values.get("assigned_user_id", current["assigned_user_id"]),
            values.get("customer_name", current["customer_name"]).strip(),
            values.get("customer_email", current["customer_email"]).strip(),
            company_id,
            session_id,
        ),
    )
    conn.commit()
    return get_support_conversation(company_id, session_id)


def list_support_inbox(company_id: int, status: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    params: list = [company_id]
    where = "WHERE s.company_id = ?"
    if status:
        where += " AND s.status = ?"
        params.append(status)
    cursor.execute(
        f"""
        SELECT s.*,
            (SELECT content FROM conversations c
             WHERE c.company_id = s.company_id AND c.session_id = s.session_id
             ORDER BY c.id DESC LIMIT 1) AS last_message,
            (SELECT COUNT(*) FROM conversations c
             WHERE c.company_id = s.company_id AND c.session_id = s.session_id) AS message_count
        FROM support_conversations s
        {where}
        ORDER BY s.last_activity_at DESC
        LIMIT 100
        """,
        tuple(params),
    )
    return [dict(row) for row in cursor.fetchall()]

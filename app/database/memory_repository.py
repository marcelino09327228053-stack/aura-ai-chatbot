"""Per-company AI memory storage."""

import sqlite3

from app.database.connection import get_connection


def list_memory(company_id: int, contact_key: str = "default") -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT id, company_id, contact_key, memory_type, content, created_at
        FROM ai_memory
        WHERE company_id = ? AND contact_key = ?
        ORDER BY created_at DESC
        """,
        (company_id, contact_key),
    )
    return [
        {
            "id": row["id"],
            "company_id": row["company_id"],
            "contact_key": row["contact_key"],
            "memory_type": row["memory_type"],
            "content": row["content"],
            "created_at": row["created_at"],
        }
        for row in cursor.fetchall()
    ]


def add_memory(
    company_id: int,
    content: str,
    memory_type: str = "general",
    contact_key: str = "default",
) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO ai_memory (company_id, contact_key, memory_type, content)
        VALUES (?, ?, ?, ?)
        """,
        (company_id, contact_key, memory_type, content),
    )
    conn.commit()
    row_id = cursor.lastrowid
    cursor.execute(
        """
        SELECT id, company_id, contact_key, memory_type, content, created_at
        FROM ai_memory WHERE id = ?
        """,
        (row_id,),
    )
    row = cursor.fetchone()
    return {
        "id": row["id"],
        "company_id": row["company_id"],
        "contact_key": row["contact_key"],
        "memory_type": row["memory_type"],
        "content": row["content"],
        "created_at": row["created_at"],
    }


def get_memory(company_id: int, contact_key: str, memory_type: str) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT id, company_id, contact_key, memory_type, content, created_at
        FROM ai_memory
        WHERE company_id = ? AND contact_key = ? AND memory_type = ?
        ORDER BY id DESC LIMIT 1
        """,
        (company_id, contact_key, memory_type),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def upsert_memory(company_id: int, contact_key: str, memory_type: str, content: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM ai_memory WHERE company_id = ? AND contact_key = ? AND memory_type = ?",
        (company_id, contact_key, memory_type),
    )
    cursor.execute(
        """
        INSERT INTO ai_memory (company_id, contact_key, memory_type, content)
        VALUES (?, ?, ?, ?)
        """,
        (company_id, contact_key, memory_type, content.strip()),
    )
    row_id = cursor.lastrowid
    conn.commit()
    cursor.execute(
        """SELECT id, company_id, contact_key, memory_type, content, created_at
           FROM ai_memory WHERE id = ?""",
        (row_id,),
    )
    return dict(cursor.fetchone())


def delete_memory(company_id: int, contact_key: str, memory_type: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM ai_memory WHERE company_id = ? AND contact_key = ? AND memory_type = ?",
        (company_id, contact_key, memory_type),
    )
    conn.commit()
    return cursor.rowcount > 0

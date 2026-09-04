"""FAQ data access (scoped per company)."""

import sqlite3

from app.database.connection import get_connection


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "company_id": row["company_id"],
        "question": row["question"],
        "answer": row["answer"],
        "created_at": row["created_at"],
    }


def find_faq_answer(question: str, company_id: int) -> str | None:
    """Return FAQ answer for an exact case-insensitive question match, or None."""
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT answer FROM faq
        WHERE company_id = ? AND LOWER(question) = LOWER(?)
        """,
        (company_id, question),
    )
    row = cursor.fetchone()
    return row["answer"] if row else None


def list_faqs(company_id: int, search: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if search:
        term = f"%{search.strip()}%"
        cursor.execute(
            """
            SELECT id, company_id, question, answer, created_at
            FROM faq
            WHERE company_id = ? AND (question LIKE ? OR answer LIKE ?)
            ORDER BY created_at DESC, id DESC
            """,
            (company_id, term, term),
        )
    else:
        cursor.execute(
            """
            SELECT id, company_id, question, answer, created_at
            FROM faq
            WHERE company_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (company_id,),
        )
    return [_row_to_dict(row) for row in cursor.fetchall()]


def get_faq(faq_id: int, company_id: int) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT id, company_id, question, answer, created_at
        FROM faq WHERE id = ? AND company_id = ?
        """,
        (faq_id, company_id),
    )
    row = cursor.fetchone()
    return _row_to_dict(row) if row else None


def create_faq(company_id: int, question: str, answer: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO faq (company_id, question, answer)
            VALUES (?, ?, ?)
            """,
            (company_id, question.strip(), answer.strip()),
        )
        conn.commit()
        return get_faq(cursor.lastrowid, company_id)
    except sqlite3.IntegrityError:
        return None


def update_faq(faq_id: int, company_id: int, question: str, answer: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE faq
            SET question = ?, answer = ?
            WHERE id = ? AND company_id = ?
            """,
            (question.strip(), answer.strip(), faq_id, company_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None
        return get_faq(faq_id, company_id)
    except sqlite3.IntegrityError:
        return None


def delete_faq(faq_id: int, company_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM faq WHERE id = ? AND company_id = ?",
        (faq_id, company_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def bulk_create_faqs(company_id: int, items: list[dict]) -> list[dict]:
    created = []
    for item in items:
        question = item.get("question", "").strip()
        answer = item.get("answer", "").strip()
        if not question or not answer:
            continue
        row = create_faq(company_id, question, answer)
        if row:
            created.append(row)
    return created

"""Storage and lightweight retrieval for company knowledge documents."""

import re
import sqlite3

from app.database.connection import get_connection

_WORD_RE = re.compile(r"[a-zA-Z0-9À-ÿ]{2,}")


def create_document(
    company_id: int, name: str, content_type: str, size_bytes: int, chunks: list[str]
) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO knowledge_documents (company_id, name, content_type, size_bytes)
        VALUES (?, ?, ?, ?)
        """,
        (company_id, name[:200], content_type[:100], size_bytes),
    )
    document_id = cursor.lastrowid
    cursor.executemany(
        """
        INSERT INTO knowledge_chunks (company_id, document_id, chunk_index, content)
        VALUES (?, ?, ?, ?)
        """,
        [(company_id, document_id, index, chunk) for index, chunk in enumerate(chunks)],
    )
    conn.commit()
    return get_document(company_id, document_id)


def get_document(company_id: int, document_id: int) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT d.*, COUNT(c.id) AS chunk_count
        FROM knowledge_documents d
        LEFT JOIN knowledge_chunks c ON c.document_id = d.id AND c.company_id = d.company_id
        WHERE d.company_id = ? AND d.id = ?
        GROUP BY d.id
        """,
        (company_id, document_id),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def list_documents(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT d.*, COUNT(c.id) AS chunk_count
        FROM knowledge_documents d
        LEFT JOIN knowledge_chunks c ON c.document_id = d.id AND c.company_id = d.company_id
        WHERE d.company_id = ?
        GROUP BY d.id
        ORDER BY d.created_at DESC, d.id DESC
        """,
        (company_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def delete_document(company_id: int, document_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM knowledge_chunks WHERE company_id = ? AND document_id = ?",
        (company_id, document_id),
    )
    cursor.execute(
        "DELETE FROM knowledge_documents WHERE company_id = ? AND id = ?",
        (company_id, document_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def search(company_id: int, query: str, limit: int = 4) -> list[dict]:
    terms = {word.lower() for word in _WORD_RE.findall(query)}
    if not terms:
        return []
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT c.id, c.document_id, c.content, d.name
        FROM knowledge_chunks c
        JOIN knowledge_documents d ON d.id = c.document_id AND d.company_id = c.company_id
        WHERE c.company_id = ?
        ORDER BY c.id DESC
        LIMIT 1000
        """,
        (company_id,),
    )
    ranked = []
    for row in cursor.fetchall():
        words = {word.lower() for word in _WORD_RE.findall(row["content"])}
        overlap = terms & words
        if overlap:
            score = len(overlap) / max(len(terms), 1)
            ranked.append(
                {
                    "chunk_id": row["id"],
                    "document_id": row["document_id"],
                    "document_name": row["name"],
                    "content": row["content"],
                    "score": round(score, 3),
                }
            )
    ranked.sort(key=lambda item: (item["score"], item["chunk_id"]), reverse=True)
    return ranked[: max(1, min(limit, 10))]

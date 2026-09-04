"""Enterprise audit logging."""

from app.infrastructure.database import get_connection


def init_audit_schema(cursor, conn) -> None:
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        user_id INTEGER,
        action TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)
    conn.commit()


def log_action(
    action: str,
    company_id: int | None = None,
    user_id: int | None = None,
) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO audit_logs (company_id, user_id, action)
        VALUES (?, ?, ?)
        """,
        (company_id, user_id, action),
    )
    conn.commit()


def list_audit_logs(company_id: int | None = None, limit: int = 50) -> list[dict]:
    cursor = get_connection().cursor()
    if company_id is not None:
        cursor.execute(
            """
            SELECT * FROM audit_logs WHERE company_id = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (company_id, limit),
        )
    else:
        cursor.execute(
            "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
    return [dict(r) for r in cursor.fetchall()]

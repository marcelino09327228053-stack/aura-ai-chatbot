"""Team collaboration data access."""

from app.infrastructure.database import get_connection


def init_team_schema(cursor, conn) -> None:
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS team_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        role TEXT NOT NULL DEFAULT 'member',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE (company_id, user_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        details TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)
    conn.commit()


def add_member(company_id: int, user_id: int, role: str = "member") -> dict:
    existing = get_member(company_id, user_id)
    if existing:
        return existing
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO team_members (company_id, user_id, role)
        VALUES (?, ?, ?)
        """,
        (company_id, user_id, role),
    )
    conn.commit()
    return get_member(company_id, user_id)


def get_member(company_id: int, user_id: int) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM team_members WHERE company_id = ? AND user_id = ?",
        (company_id, user_id),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def list_members(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM team_members WHERE company_id = ? ORDER BY created_at ASC",
        (company_id,),
    )
    return [dict(r) for r in cursor.fetchall()]


def set_role(company_id: int, user_id: int, role: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE team_members SET role = ? WHERE company_id = ? AND user_id = ?",
        (role, company_id, user_id),
    )
    conn.commit()
    return get_member(company_id, user_id)


def remove_member(company_id: int, user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM team_members WHERE company_id = ? AND user_id = ?",
        (company_id, user_id),
    )
    if not cursor.fetchone():
        return False
    cursor.execute(
        "DELETE FROM team_members WHERE company_id = ? AND user_id = ?",
        (company_id, user_id),
    )
    conn.commit()
    return True


def get_user_role(company_id: int, user_id: int, owner_id: int | None) -> str:
    if owner_id == user_id:
        return "owner"
    member = get_member(company_id, user_id)
    return member["role"] if member else "viewer"


def log_activity(company_id: int, user_id: int, action: str, details: str = "") -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO activity_history (company_id, user_id, action, details)
        VALUES (?, ?, ?, ?)
        """,
        (company_id, user_id, action, details[:500]),
    )
    conn.commit()


def list_activity(company_id: int, limit: int = 50) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT * FROM activity_history
        WHERE company_id = ?
        ORDER BY created_at DESC LIMIT ?
        """,
        (company_id, limit),
    )
    return [dict(r) for r in cursor.fetchall()]

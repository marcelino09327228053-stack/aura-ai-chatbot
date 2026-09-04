"""Agent and memory data access."""

import json

from app.database.connection import get_connection

AGENT_TYPES = ("support", "sales", "hr", "accounting", "marketing")
AGENT_DEFAULTS = {
    "support": "Support Agent",
    "sales": "Sales Agent",
    "hr": "HR Agent",
    "accounting": "Accounting Agent",
    "marketing": "Marketing Agent",
}


def ensure_company_agents(company_id: int) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    for agent_type, name in AGENT_DEFAULTS.items():
        cursor.execute(
            """
            INSERT OR IGNORE INTO agents (company_id, name, type, enabled)
            VALUES (?, ?, ?, 1)
            """,
            (company_id, name, agent_type),
        )
    conn.commit()


def list_agents(company_id: int) -> list[dict]:
    ensure_company_agents(company_id)
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT id, company_id, name, type, enabled, created_at FROM agents WHERE company_id = ?",
        (company_id,),
    )
    return [
        {
            "id": r["id"],
            "company_id": r["company_id"],
            "name": r["name"],
            "type": r["type"],
            "enabled": bool(r["enabled"]),
            "created_at": r["created_at"],
        }
        for r in cursor.fetchall()
    ]


def get_agent(company_id: int, agent_type: str) -> dict | None:
    ensure_company_agents(company_id)
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT id, company_id, name, type, enabled, created_at FROM agents WHERE company_id = ? AND type = ?",
        (company_id, agent_type),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "company_id": row["company_id"],
        "name": row["name"],
        "type": row["type"],
        "enabled": bool(row["enabled"]),
        "created_at": row["created_at"],
    }


def is_agent_enabled(company_id: int, agent_type: str) -> bool:
    agent = get_agent(company_id, agent_type)
    return bool(agent and agent["enabled"])


def set_agent_enabled(company_id: int, agent_type: str, enabled: bool) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE agents SET enabled = ? WHERE company_id = ? AND type = ?",
        (1 if enabled else 0, company_id, agent_type),
    )
    conn.commit()
    return get_agent(company_id, agent_type)


def add_memory(company_id: int, user_id: str, summary: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO memories (company_id, user_id, summary) VALUES (?, ?, ?)",
        (company_id, user_id, summary.strip()),
    )
    conn.commit()
    cursor.execute("SELECT * FROM memories WHERE id = ?", (cursor.lastrowid,))
    row = cursor.fetchone()
    return dict(row)


def list_memories(company_id: int, user_id: str | None = None, limit: int = 10) -> list[dict]:
    cursor = get_connection().cursor()
    if user_id:
        cursor.execute(
            """
            SELECT * FROM memories
            WHERE company_id = ? AND user_id = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (company_id, user_id, limit),
        )
    else:
        cursor.execute(
            """
            SELECT * FROM memories
            WHERE company_id = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (company_id, limit),
        )
    return [dict(r) for r in cursor.fetchall()]


def count_memories(company_id: int) -> int:
    cursor = get_connection().cursor()
    cursor.execute("SELECT COUNT(*) FROM memories WHERE company_id = ?", (company_id,))
    return cursor.fetchone()[0]


def log_agent_run(
    company_id: int,
    agent_type: str,
    user_message: str,
    reply_source: str,
    response_preview: str,
) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO agent_logs (company_id, agent_type, user_message, reply_source, response_preview)
        VALUES (?, ?, ?, ?, ?)
        """,
        (company_id, agent_type, user_message[:500], reply_source, response_preview[:500]),
    )
    conn.commit()


def list_agent_logs(company_id: int, limit: int = 50) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT * FROM agent_logs
        WHERE company_id = ?
        ORDER BY created_at DESC LIMIT ?
        """,
        (company_id, limit),
    )
    return [dict(r) for r in cursor.fetchall()]


def list_scheduler_tasks(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM scheduler_tasks WHERE company_id = ? ORDER BY created_at DESC",
        (company_id,),
    )
    return [dict(r) for r in cursor.fetchall()]


def create_scheduler_task(company_id: int, task_type: str, schedule: str, payload: dict | None = None) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO scheduler_tasks (company_id, task_type, schedule, payload)
        VALUES (?, ?, ?, ?)
        """,
        (company_id, task_type, schedule, json.dumps(payload or {})),
    )
    conn.commit()
    cursor.execute("SELECT * FROM scheduler_tasks WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_reminders(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM scheduler_reminders WHERE company_id = ? ORDER BY remind_at ASC",
        (company_id,),
    )
    return [dict(r) for r in cursor.fetchall()]


def create_reminder(company_id: int, title: str, message: str, remind_at: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO scheduler_reminders (company_id, title, message, remind_at)
        VALUES (?, ?, ?, ?)
        """,
        (company_id, title, message, remind_at),
    )
    conn.commit()
    cursor.execute("SELECT * FROM scheduler_reminders WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())

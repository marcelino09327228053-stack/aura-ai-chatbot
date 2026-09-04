"""Aura OS data access."""

import json
from datetime import datetime, timezone

from app.infrastructure.database import get_connection


def create_job(
    company_id: int,
    task_type: str,
    assigned_agent: str | None = None,
    payload: dict | None = None,
) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO os_jobs (company_id, task_type, assigned_agent, payload, status)
        VALUES (?, ?, ?, ?, 'pending')
        """,
        (company_id, task_type, assigned_agent, json.dumps(payload or {})),
    )
    conn.commit()
    return get_job(company_id, cursor.lastrowid)


def get_job(company_id: int, job_id: int) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM os_jobs WHERE company_id = ? AND id = ?",
        (company_id, job_id),
    )
    row = cursor.fetchone()
    if not row:
        return None
    data = dict(row)
    data["payload"] = json.loads(data.get("payload") or "{}")
    return data


def update_job_status(
    company_id: int,
    job_id: int,
    status: str,
    result: str | None = None,
    assigned_agent: str | None = None,
) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    completed = datetime.now(timezone.utc).isoformat() if status in ("completed", "failed") else None
    cursor.execute(
        """
        UPDATE os_jobs
        SET status = ?, result = ?, assigned_agent = COALESCE(?, assigned_agent),
            completed_at = COALESCE(?, completed_at)
        WHERE company_id = ? AND id = ?
        """,
        (status, result, assigned_agent, completed, company_id, job_id),
    )
    conn.commit()
    return get_job(company_id, job_id)


def list_jobs(company_id: int, status: str | None = None, limit: int = 50) -> list[dict]:
    cursor = get_connection().cursor()
    if status:
        cursor.execute(
            """
            SELECT * FROM os_jobs WHERE company_id = ? AND status = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (company_id, status, limit),
        )
    else:
        cursor.execute(
            "SELECT * FROM os_jobs WHERE company_id = ? ORDER BY created_at DESC LIMIT ?",
            (company_id, limit),
        )
    rows = []
    for r in cursor.fetchall():
        data = dict(r)
        data["payload"] = json.loads(data.get("payload") or "{}")
        rows.append(data)
    return rows


def create_workflow(company_id: int, workflow_key: str, name: str, payload: dict | None = None) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO os_workflows (company_id, workflow_key, name, status, payload)
        VALUES (?, ?, ?, 'running', ?)
        """,
        (company_id, workflow_key, name, json.dumps(payload or {})),
    )
    conn.commit()
    return get_workflow(company_id, cursor.lastrowid)


def get_workflow(company_id: int, workflow_id: int) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM os_workflows WHERE company_id = ? AND id = ?",
        (company_id, workflow_id),
    )
    row = cursor.fetchone()
    if not row:
        return None
    data = dict(row)
    data["payload"] = json.loads(data.get("payload") or "{}")
    return data


def update_workflow(company_id: int, workflow_id: int, **fields) -> dict | None:
    wf = get_workflow(company_id, workflow_id)
    if not wf:
        return None
    status = fields.get("status", wf["status"])
    current_step = fields.get("current_step", wf["current_step"])
    payload = fields.get("payload", wf["payload"])
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE os_workflows
        SET status = ?, current_step = ?, payload = ?, updated_at = datetime('now')
        WHERE company_id = ? AND id = ?
        """,
        (status, current_step, json.dumps(payload), company_id, workflow_id),
    )
    conn.commit()
    return get_workflow(company_id, workflow_id)


def list_workflows(company_id: int, status: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if status:
        cursor.execute(
            "SELECT * FROM os_workflows WHERE company_id = ? AND status = ? ORDER BY updated_at DESC",
            (company_id, status),
        )
    else:
        cursor.execute(
            "SELECT * FROM os_workflows WHERE company_id = ? ORDER BY updated_at DESC",
            (company_id,),
        )
    rows = []
    for r in cursor.fetchall():
        data = dict(r)
        data["payload"] = json.loads(data.get("payload") or "{}")
        rows.append(data)
    return rows


def send_agent_message(company_id: int, from_agent: str, to_agent: str, message: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO os_agent_messages (company_id, from_agent, to_agent, message)
        VALUES (?, ?, ?, ?)
        """,
        (company_id, from_agent, to_agent, message[:2000]),
    )
    conn.commit()
    cursor.execute("SELECT * FROM os_agent_messages WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_agent_messages(company_id: int, limit: int = 50) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT * FROM os_agent_messages WHERE company_id = ?
        ORDER BY created_at DESC LIMIT ?
        """,
        (company_id, limit),
    )
    return [dict(r) for r in cursor.fetchall()]


def add_long_term_memory(
    company_id: int,
    memory_type: str,
    subject_key: str,
    summary: str,
) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO os_long_term_memory (company_id, memory_type, subject_key, summary)
        VALUES (?, ?, ?, ?)
        """,
        (company_id, memory_type, subject_key, summary[:2000]),
    )
    conn.commit()
    cursor.execute("SELECT * FROM os_long_term_memory WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_long_term_memory(
    company_id: int,
    memory_type: str | None = None,
    limit: int = 50,
) -> list[dict]:
    cursor = get_connection().cursor()
    if memory_type:
        cursor.execute(
            """
            SELECT * FROM os_long_term_memory
            WHERE company_id = ? AND memory_type = ?
            ORDER BY updated_at DESC LIMIT ?
            """,
            (company_id, memory_type, limit),
        )
    else:
        cursor.execute(
            """
            SELECT * FROM os_long_term_memory WHERE company_id = ?
            ORDER BY updated_at DESC LIMIT ?
            """,
            (company_id, limit),
        )
    return [dict(r) for r in cursor.fetchall()]


def count_long_term_memory(company_id: int) -> dict:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT memory_type, COUNT(*) as cnt
        FROM os_long_term_memory WHERE company_id = ?
        GROUP BY memory_type
        """,
        (company_id,),
    )
    return {r["memory_type"]: r["cnt"] for r in cursor.fetchall()}


def add_knowledge(company_id: int, source_type: str, content: str, source_ref: str = "") -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO os_knowledge (company_id, source_type, source_ref, content)
        VALUES (?, ?, ?, ?)
        """,
        (company_id, source_type, source_ref, content[:5000]),
    )
    conn.commit()
    cursor.execute("SELECT * FROM os_knowledge WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_knowledge(company_id: int, source_type: str | None = None, limit: int = 50) -> list[dict]:
    cursor = get_connection().cursor()
    if source_type:
        cursor.execute(
            """
            SELECT * FROM os_knowledge WHERE company_id = ? AND source_type = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (company_id, source_type, limit),
        )
    else:
        cursor.execute(
            "SELECT * FROM os_knowledge WHERE company_id = ? ORDER BY created_at DESC LIMIT ?",
            (company_id, limit),
        )
    return [dict(r) for r in cursor.fetchall()]


def ensure_automation_task(company_id: int, task_key: str, schedule: str) -> dict:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM os_automation_tasks WHERE company_id = ? AND task_key = ?",
        (company_id, task_key),
    )
    row = cursor.fetchone()
    if row:
        return dict(row)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO os_automation_tasks (company_id, task_key, schedule)
        VALUES (?, ?, ?)
        """,
        (company_id, task_key, schedule),
    )
    conn.commit()
    cursor.execute("SELECT * FROM os_automation_tasks WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_automation_tasks(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM os_automation_tasks WHERE company_id = ? ORDER BY created_at ASC",
        (company_id,),
    )
    return [dict(r) for r in cursor.fetchall()]


def touch_automation_task(company_id: int, task_key: str) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE os_automation_tasks SET last_run_at = datetime('now')
        WHERE company_id = ? AND task_key = ?
        """,
        (company_id, task_key),
    )
    conn.commit()


def add_notification(company_id: int, title: str, message: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO os_notifications (company_id, title, message) VALUES (?, ?, ?)",
        (company_id, title, message[:500]),
    )
    conn.commit()
    cursor.execute("SELECT * FROM os_notifications WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_notifications(company_id: int, limit: int = 20) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT * FROM os_notifications WHERE company_id = ?
        ORDER BY created_at DESC LIMIT ?
        """,
        (company_id, limit),
    )
    return [dict(r) for r in cursor.fetchall()]

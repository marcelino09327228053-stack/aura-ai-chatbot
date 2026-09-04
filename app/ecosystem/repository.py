"""Ecosystem data access layer."""

import json

from app.cloud.security import encrypt_value
from app.infrastructure.database import get_connection


def log_ecosystem_action(company_id: int, action: str, user_id: int | None = None, details: str = "") -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO ecosystem_audit (company_id, user_id, action, details) VALUES (?,?,?,?)",
        (company_id, user_id, action, details[:500]),
    )
    conn.commit()


def list_audit(company_id: int, limit: int = 50) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM ecosystem_audit WHERE company_id = ? ORDER BY created_at DESC LIMIT ?",
        (company_id, limit),
    )
    return [dict(r) for r in cursor.fetchall()]


# ── Research ──────────────────────────────────────────────────────────────────

def save_research(company_id: int, research_type: str, title: str, findings: dict, summary: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO ecosystem_research (company_id, research_type, title, findings, summary)
        VALUES (?,?,?,?,?)
        """,
        (company_id, research_type, title, json.dumps(findings), summary[:1000]),
    )
    conn.commit()
    cursor.execute("SELECT * FROM ecosystem_research WHERE id = ?", (cursor.lastrowid,))
    row = dict(cursor.fetchone())
    row["findings"] = findings
    return row


def list_research(company_id: int, research_type: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if research_type:
        cursor.execute(
            "SELECT * FROM ecosystem_research WHERE company_id = ? AND research_type = ? ORDER BY created_at DESC LIMIT 30",
            (company_id, research_type),
        )
    else:
        cursor.execute(
            "SELECT * FROM ecosystem_research WHERE company_id = ? ORDER BY created_at DESC LIMIT 50",
            (company_id,),
        )
    rows = []
    for r in cursor.fetchall():
        data = dict(r)
        try:
            data["findings"] = json.loads(data.get("findings") or "{}")
        except Exception:
            data["findings"] = {}
        rows.append(data)
    return rows


# ── Innovations ───────────────────────────────────────────────────────────────

def save_innovation(company_id: int, data: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO ecosystem_innovations
            (company_id, category, title, description, impact_score, effort_score, status)
        VALUES (?,?,?,?,?,?,?)
        """,
        (
            company_id,
            data.get("category", "product"),
            data.get("title", ""),
            data.get("description", ""),
            data.get("impact_score", 0),
            data.get("effort_score", 0),
            data.get("status", "suggested"),
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM ecosystem_innovations WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_innovations(company_id: int, category: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if category:
        cursor.execute(
            "SELECT * FROM ecosystem_innovations WHERE company_id = ? AND category = ? ORDER BY impact_score DESC",
            (company_id, category),
        )
    else:
        cursor.execute(
            "SELECT * FROM ecosystem_innovations WHERE company_id = ? ORDER BY impact_score DESC",
            (company_id,),
        )
    return [dict(r) for r in cursor.fetchall()]


# ── Simulations ───────────────────────────────────────────────────────────────

def save_simulation(company_id: int, scenario_type: str, parameters: dict, result: dict, confidence: float = 0.7) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    params_enc = encrypt_value(json.dumps(parameters))
    cursor.execute(
        """
        INSERT INTO ecosystem_simulations
            (company_id, scenario_type, parameters, result, confidence)
        VALUES (?,?,?,?,?)
        """,
        (company_id, scenario_type, params_enc, json.dumps(result), confidence),
    )
    conn.commit()
    cursor.execute("SELECT * FROM ecosystem_simulations WHERE id = ?", (cursor.lastrowid,))
    row = dict(cursor.fetchone())
    row["parameters"] = parameters
    row["result"] = result
    return row


def list_simulations(company_id: int, limit: int = 20) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT id, company_id, scenario_type, result, confidence, created_at
        FROM ecosystem_simulations WHERE company_id = ?
        ORDER BY created_at DESC LIMIT ?
        """,
        (company_id, limit),
    )
    rows = []
    for r in cursor.fetchall():
        data = dict(r)
        try:
            data["result"] = json.loads(data.get("result") or "{}")
        except Exception:
            data["result"] = {}
        rows.append(data)
    return rows


# ── Automation ────────────────────────────────────────────────────────────────

def create_automation_job(company_id: int, job_type: str, title: str, payload: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO ecosystem_automation_jobs (company_id, job_type, title, payload, status)
        VALUES (?,?,?,?, 'pending')
        """,
        (company_id, job_type, title, json.dumps(payload)),
    )
    conn.commit()
    cursor.execute("SELECT * FROM ecosystem_automation_jobs WHERE id = ?", (cursor.lastrowid,))
    row = dict(cursor.fetchone())
    try:
        row["payload"] = json.loads(row.get("payload") or "{}")
    except Exception:
        row["payload"] = {}
    return row


def complete_automation_job(job_id: int, company_id: int, result: str, status: str = "completed") -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE ecosystem_automation_jobs
        SET status = ?, result = ?, completed_at = datetime('now')
        WHERE id = ? AND company_id = ?
        """,
        (status, result[:2000], job_id, company_id),
    )
    conn.commit()
    cursor.execute(
        "SELECT * FROM ecosystem_automation_jobs WHERE id = ? AND company_id = ?",
        (job_id, company_id),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def list_automation_jobs(company_id: int, limit: int = 30) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM ecosystem_automation_jobs WHERE company_id = ? ORDER BY created_at DESC LIMIT ?",
        (company_id, limit),
    )
    rows = []
    for r in cursor.fetchall():
        data = dict(r)
        try:
            data["payload"] = json.loads(data.get("payload") or "{}")
        except Exception:
            data["payload"] = {}
        rows.append(data)
    return rows


# ── Notifications ─────────────────────────────────────────────────────────────

def create_notification(company_id: int, title: str, message: str, priority: str = "medium", source: str = "system") -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO ecosystem_notifications (company_id, priority, title, message, source)
        VALUES (?,?,?,?,?)
        """,
        (company_id, priority, title, message[:500], source),
    )
    conn.commit()
    cursor.execute("SELECT * FROM ecosystem_notifications WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_notifications(company_id: int, unread_only: bool = False) -> list[dict]:
    cursor = get_connection().cursor()
    if unread_only:
        cursor.execute(
            "SELECT * FROM ecosystem_notifications WHERE company_id = ? AND read_flag = 0 ORDER BY created_at DESC LIMIT 50",
            (company_id,),
        )
    else:
        cursor.execute(
            "SELECT * FROM ecosystem_notifications WHERE company_id = ? ORDER BY created_at DESC LIMIT 50",
            (company_id,),
        )
    return [dict(r) for r in cursor.fetchall()]


def mark_notification_read(company_id: int, notification_id: int) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE ecosystem_notifications SET read_flag = 1 WHERE id = ? AND company_id = ?",
        (notification_id, company_id),
    )
    conn.commit()


# ── Agent links & knowledge ───────────────────────────────────────────────────

def upsert_agent_link(company_id: int, agent_id: str, agent_name: str, domain: str, performance_score: float = 0.7) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM ecosystem_agent_links WHERE company_id = ? AND agent_id = ?",
        (company_id, agent_id),
    )
    existing = cursor.fetchone()
    if existing:
        cursor.execute(
            """
            UPDATE ecosystem_agent_links
            SET agent_name = ?, domain = ?, status = 'active', last_seen = datetime('now'), performance_score = ?
            WHERE id = ?
            """,
            (agent_name, domain, performance_score, existing["id"]),
        )
        conn.commit()
        cursor.execute("SELECT * FROM ecosystem_agent_links WHERE id = ?", (existing["id"],))
    else:
        cursor.execute(
            """
            INSERT INTO ecosystem_agent_links
                (company_id, agent_id, agent_name, domain, performance_score)
            VALUES (?,?,?,?,?)
            """,
            (company_id, agent_id, agent_name, domain, performance_score),
        )
        conn.commit()
        cursor.execute("SELECT * FROM ecosystem_agent_links WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_agent_links(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM ecosystem_agent_links WHERE company_id = ? ORDER BY performance_score DESC",
        (company_id,),
    )
    return [dict(r) for r in cursor.fetchall()]


def save_knowledge(company_id: int, source_agent: str, topic: str, content: str, shared: bool = True) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO ecosystem_knowledge (company_id, source_agent, topic, content, shared)
        VALUES (?,?,?,?,?)
        """,
        (company_id, source_agent, topic, content[:2000], int(shared)),
    )
    conn.commit()
    cursor.execute("SELECT * FROM ecosystem_knowledge WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_knowledge(company_id: int, limit: int = 30) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM ecosystem_knowledge WHERE company_id = ? AND shared = 1 ORDER BY created_at DESC LIMIT ?",
        (company_id, limit),
    )
    return [dict(r) for r in cursor.fetchall()]

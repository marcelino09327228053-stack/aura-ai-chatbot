"""Universal platform data access layer."""

import json

from app.cloud.security import encrypt_value, decrypt_value
from app.infrastructure.database import get_connection


def log_universe_action(company_id: int, action: str, user_id: int | None = None, details: str = "") -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO universe_audit (company_id, user_id, action, details) VALUES (?,?,?,?)",
        (company_id, user_id, action, details[:500]),
    )
    conn.commit()


def list_audit(company_id: int, limit: int = 50) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM universe_audit WHERE company_id = ? ORDER BY created_at DESC LIMIT ?",
        (company_id, limit),
    )
    return [dict(r) for r in cursor.fetchall()]


# ── AI Core Memory ────────────────────────────────────────────────────────────

def save_brain_memory(company_id: int, memory_key: str, content: str, memory_type: str = "shared") -> dict:
    encrypted = encrypt_value(content)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM universe_brain_memory WHERE company_id = ? AND memory_key = ?",
        (company_id, memory_key),
    )
    existing = cursor.fetchone()
    if existing:
        cursor.execute(
            """
            UPDATE universe_brain_memory
            SET content = ?, memory_type = ?, updated_at = datetime('now')
            WHERE company_id = ? AND memory_key = ?
            """,
            (encrypted, memory_type, company_id, memory_key),
        )
    else:
        cursor.execute(
            """
            INSERT INTO universe_brain_memory (company_id, memory_key, memory_type, content)
            VALUES (?,?,?,?)
            """,
            (company_id, memory_key, memory_type, encrypted),
        )
    conn.commit()
    return {"memory_key": memory_key, "memory_type": memory_type, "content": content}


def get_brain_memory(company_id: int, memory_key: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if memory_key:
        cursor.execute(
            "SELECT * FROM universe_brain_memory WHERE company_id = ? AND memory_key = ?",
            (company_id, memory_key),
        )
    else:
        cursor.execute(
            "SELECT * FROM universe_brain_memory WHERE company_id = ? ORDER BY updated_at DESC LIMIT 50",
            (company_id,),
        )
    rows = []
    for r in cursor.fetchall():
        data = dict(r)
        try:
            data["content"] = decrypt_value(data.get("content") or "")
        except Exception:
            data["content"] = data.get("content", "")
        rows.append(data)
    return rows


def save_decision(company_id: int, data: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO universe_decisions
            (company_id, decision_type, title, rationale, agents_involved, status, confidence)
        VALUES (?,?,?,?,?,?,?)
        """,
        (
            company_id,
            data.get("decision_type", "strategic"),
            data.get("title", ""),
            data.get("rationale", ""),
            json.dumps(data.get("agents_involved", [])),
            data.get("status", "pending"),
            data.get("confidence", 0.7),
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM universe_decisions WHERE id = ?", (cursor.lastrowid,))
    row = dict(cursor.fetchone())
    row["agents_involved"] = json.loads(row.get("agents_involved") or "[]")
    return row


def list_decisions(company_id: int, limit: int = 20) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM universe_decisions WHERE company_id = ? ORDER BY created_at DESC LIMIT ?",
        (company_id, limit),
    )
    rows = []
    for r in cursor.fetchall():
        data = dict(r)
        data["agents_involved"] = json.loads(data.get("agents_involved") or "[]")
        rows.append(data)
    return rows


def upsert_coordination(company_id: int, source_agent: str, target_agent: str, task: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id FROM universe_agent_coordination
        WHERE company_id = ? AND source_agent = ? AND target_agent = ?
        """,
        (company_id, source_agent, target_agent),
    )
    existing = cursor.fetchone()
    if existing:
        cursor.execute(
            """
            UPDATE universe_agent_coordination
            SET task = ?, status = 'active', last_sync = datetime('now')
            WHERE id = ?
            """,
            (task, existing[0]),
        )
        row_id = existing[0]
    else:
        cursor.execute(
            """
            INSERT INTO universe_agent_coordination (company_id, source_agent, target_agent, task)
            VALUES (?,?,?,?)
            """,
            (company_id, source_agent, target_agent, task),
        )
        row_id = cursor.lastrowid
    conn.commit()
    cursor.execute("SELECT * FROM universe_agent_coordination WHERE id = ?", (row_id,))
    return dict(cursor.fetchone())


def list_coordination(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM universe_agent_coordination WHERE company_id = ? ORDER BY last_sync DESC",
        (company_id,),
    )
    return [dict(r) for r in cursor.fetchall()]


# ── Collaboration ─────────────────────────────────────────────────────────────

def create_project(company_id: int, data: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO universe_projects (company_id, project_type, title, description, members, status)
        VALUES (?,?,?,?,?,?)
        """,
        (
            company_id,
            data.get("project_type", "team"),
            data.get("title", ""),
            data.get("description", ""),
            json.dumps(data.get("members", [])),
            data.get("status", "active"),
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM universe_projects WHERE id = ?", (cursor.lastrowid,))
    row = dict(cursor.fetchone())
    row["members"] = json.loads(row.get("members") or "[]")
    return row


def list_projects(company_id: int, project_type: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if project_type:
        cursor.execute(
            "SELECT * FROM universe_projects WHERE company_id = ? AND project_type = ? ORDER BY created_at DESC",
            (company_id, project_type),
        )
    else:
        cursor.execute(
            "SELECT * FROM universe_projects WHERE company_id = ? ORDER BY created_at DESC LIMIT 50",
            (company_id,),
        )
    rows = []
    for r in cursor.fetchall():
        data = dict(r)
        data["members"] = json.loads(data.get("members") or "[]")
        rows.append(data)
    return rows


def save_shared_knowledge(company_id: int, topic: str, content: str, project_id: int | None = None,
                          shared_with: str = "all") -> dict:
    encrypted = encrypt_value(content)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO universe_shared_knowledge (company_id, project_id, topic, content, shared_with)
        VALUES (?,?,?,?,?)
        """,
        (company_id, project_id, topic, encrypted, shared_with),
    )
    conn.commit()
    cursor.execute("SELECT * FROM universe_shared_knowledge WHERE id = ?", (cursor.lastrowid,))
    row = dict(cursor.fetchone())
    row["content"] = content
    return row


def list_shared_knowledge(company_id: int, limit: int = 30) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM universe_shared_knowledge WHERE company_id = ? ORDER BY created_at DESC LIMIT ?",
        (company_id, limit),
    )
    rows = []
    for r in cursor.fetchall():
        data = dict(r)
        try:
            data["content"] = decrypt_value(data.get("content") or "")
        except Exception:
            pass
        rows.append(data)
    return rows


# ── Knowledge ─────────────────────────────────────────────────────────────────

def save_knowledge_entry(company_id: int, source_type: str, title: str, content: str,
                         source_id: str = "", summary: str = "") -> dict:
    encrypted = encrypt_value(content)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO universe_knowledge_entries
            (company_id, source_type, source_id, title, content, summary)
        VALUES (?,?,?,?,?,?)
        """,
        (company_id, source_type, source_id, title, encrypted, summary[:1000]),
    )
    conn.commit()
    cursor.execute("SELECT * FROM universe_knowledge_entries WHERE id = ?", (cursor.lastrowid,))
    row = dict(cursor.fetchone())
    row["content"] = content
    return row


def list_knowledge_entries(company_id: int, source_type: str | None = None, limit: int = 50) -> list[dict]:
    cursor = get_connection().cursor()
    if source_type:
        cursor.execute(
            """
            SELECT * FROM universe_knowledge_entries
            WHERE company_id = ? AND source_type = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (company_id, source_type, limit),
        )
    else:
        cursor.execute(
            "SELECT * FROM universe_knowledge_entries WHERE company_id = ? ORDER BY created_at DESC LIMIT ?",
            (company_id, limit),
        )
    rows = []
    for r in cursor.fetchall():
        data = dict(r)
        try:
            data["content"] = decrypt_value(data.get("content") or "")
        except Exception:
            pass
        rows.append(data)
    return rows


def save_summary(company_id: int, summary_type: str, title: str, content: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO universe_summaries (company_id, summary_type, title, content) VALUES (?,?,?,?)",
        (company_id, summary_type, title, content[:5000]),
    )
    conn.commit()
    cursor.execute("SELECT * FROM universe_summaries WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_summaries(company_id: int, summary_type: str | None = None, limit: int = 20) -> list[dict]:
    cursor = get_connection().cursor()
    if summary_type:
        cursor.execute(
            "SELECT * FROM universe_summaries WHERE company_id = ? AND summary_type = ? ORDER BY created_at DESC LIMIT ?",
            (company_id, summary_type, limit),
        )
    else:
        cursor.execute(
            "SELECT * FROM universe_summaries WHERE company_id = ? ORDER BY created_at DESC LIMIT ?",
            (company_id, limit),
        )
    return [dict(r) for r in cursor.fetchall()]


# ── Governance ────────────────────────────────────────────────────────────────

def create_policy(company_id: int, data: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO universe_policies (company_id, title, category, content, version, active)
        VALUES (?,?,?,?,?,?)
        """,
        (
            company_id,
            data.get("title", ""),
            data.get("category", "general"),
            data.get("content", ""),
            data.get("version", "1.0"),
            1 if data.get("active", True) else 0,
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM universe_policies WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_policies(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM universe_policies WHERE company_id = ? AND active = 1 ORDER BY created_at DESC",
        (company_id,),
    )
    return [dict(r) for r in cursor.fetchall()]


def create_approval(company_id: int, data: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO universe_approvals
            (company_id, requester_id, approval_type, title, details, status)
        VALUES (?,?,?,?,?,?)
        """,
        (
            company_id,
            data.get("requester_id"),
            data.get("approval_type", "general"),
            data.get("title", ""),
            data.get("details", ""),
            "pending",
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM universe_approvals WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_approvals(company_id: int, status: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if status:
        cursor.execute(
            "SELECT * FROM universe_approvals WHERE company_id = ? AND status = ? ORDER BY created_at DESC",
            (company_id, status),
        )
    else:
        cursor.execute(
            "SELECT * FROM universe_approvals WHERE company_id = ? ORDER BY created_at DESC LIMIT 30",
            (company_id,),
        )
    return [dict(r) for r in cursor.fetchall()]


def decide_approval(company_id: int, approval_id: int, status: str, decided_by: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE universe_approvals
        SET status = ?, decided_by = ?, decided_at = datetime('now')
        WHERE id = ? AND company_id = ?
        """,
        (status, decided_by, approval_id, company_id),
    )
    conn.commit()
    cursor.execute("SELECT * FROM universe_approvals WHERE id = ? AND company_id = ?", (approval_id, company_id))
    row = cursor.fetchone()
    return dict(row) if row else None


def save_security_rule(company_id: int, rule_name: str, rule_type: str, config: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO universe_security_rules (company_id, rule_name, rule_type, config)
        VALUES (?,?,?,?)
        """,
        (company_id, rule_name, rule_type, json.dumps(config)),
    )
    conn.commit()
    cursor.execute("SELECT * FROM universe_security_rules WHERE id = ?", (cursor.lastrowid,))
    row = dict(cursor.fetchone())
    row["config"] = config
    return row


def list_security_rules(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM universe_security_rules WHERE company_id = ? AND enforced = 1",
        (company_id,),
    )
    rows = []
    for r in cursor.fetchall():
        data = dict(r)
        try:
            data["config"] = json.loads(data.get("config") or "{}")
        except Exception:
            data["config"] = {}
        rows.append(data)
    return rows


# ── Expansion ─────────────────────────────────────────────────────────────────

def save_expansion(company_id: int, expansion_type: str, name: str, region: str = "", config: dict | None = None) -> dict:
    encrypted_config = encrypt_value(json.dumps(config or {}))
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO universe_expansions (company_id, expansion_type, name, region, config, status)
        VALUES (?,?,?,?,?,'planned')
        """,
        (company_id, expansion_type, name, region, encrypted_config),
    )
    conn.commit()
    cursor.execute("SELECT * FROM universe_expansions WHERE id = ?", (cursor.lastrowid,))
    row = dict(cursor.fetchone())
    row["config"] = config or {}
    return row


def list_expansions(company_id: int, expansion_type: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if expansion_type:
        cursor.execute(
            "SELECT * FROM universe_expansions WHERE company_id = ? AND expansion_type = ? ORDER BY created_at DESC",
            (company_id, expansion_type),
        )
    else:
        cursor.execute(
            "SELECT * FROM universe_expansions WHERE company_id = ? ORDER BY created_at DESC LIMIT 50",
            (company_id,),
        )
    rows = []
    for r in cursor.fetchall():
        data = dict(r)
        try:
            data["config"] = json.loads(decrypt_value(data.get("config") or "{}"))
        except Exception:
            data["config"] = {}
        rows.append(data)
    return rows


def update_expansion_status(company_id: int, expansion_id: int, status: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE universe_expansions SET status = ? WHERE id = ? AND company_id = ?",
        (status, expansion_id, company_id),
    )
    conn.commit()
    cursor.execute("SELECT * FROM universe_expansions WHERE id = ? AND company_id = ?", (expansion_id, company_id))
    row = cursor.fetchone()
    if not row:
        return None
    data = dict(row)
    try:
        data["config"] = json.loads(decrypt_value(data.get("config") or "{}"))
    except Exception:
        data["config"] = {}
    return data

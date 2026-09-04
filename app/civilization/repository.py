"""Civilization layer data access."""

import json

from app.cloud.security import encrypt_value, decrypt_value
from app.infrastructure.database import get_connection


def log_civ_action(company_id: int, action: str, user_id: int | None = None, details: str = "") -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO civ_audit (company_id, user_id, action, details) VALUES (?,?,?,?)",
        (company_id, user_id, action, details[:500]),
    )
    conn.commit()


def list_audit(company_id: int, limit: int = 50) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM civ_audit WHERE company_id = ? ORDER BY created_at DESC LIMIT ?",
        (company_id, limit),
    )
    return [dict(r) for r in cursor.fetchall()]


# ── Governance ────────────────────────────────────────────────────────────────

def save_constitution(company_id: int, title: str, articles: list, version: str = "1.0") -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO civ_constitutions (company_id, title, articles, version) VALUES (?,?,?,?)",
        (company_id, title, json.dumps(articles), version),
    )
    conn.commit()
    cursor.execute("SELECT * FROM civ_constitutions WHERE id = ?", (cursor.lastrowid,))
    row = dict(cursor.fetchone())
    row["articles"] = articles
    return row


def list_constitutions(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM civ_constitutions WHERE company_id = ? ORDER BY created_at DESC",
        (company_id,),
    )
    rows = []
    for r in cursor.fetchall():
        data = dict(r)
        try:
            data["articles"] = json.loads(data.get("articles") or "[]")
        except Exception:
            data["articles"] = []
        rows.append(data)
    return rows


def ratify_constitution(company_id: int, constitution_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE civ_constitutions SET ratified = 1 WHERE id = ? AND company_id = ?",
        (constitution_id, company_id),
    )
    conn.commit()
    cursor.execute("SELECT * FROM civ_constitutions WHERE id = ? AND company_id = ?", (constitution_id, company_id))
    row = cursor.fetchone()
    if not row:
        return None
    data = dict(row)
    data["articles"] = json.loads(data.get("articles") or "[]")
    return data


def create_vote(company_id: int, title: str, description: str, options: list, created_by: int | None = None) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    results = {opt: 0 for opt in options}
    cursor.execute(
        """
        INSERT INTO civ_votes (company_id, title, description, options, results, created_by)
        VALUES (?,?,?,?,?,?)
        """,
        (company_id, title, description, json.dumps(options), json.dumps(results), created_by),
    )
    conn.commit()
    cursor.execute("SELECT * FROM civ_votes WHERE id = ?", (cursor.lastrowid,))
    row = dict(cursor.fetchone())
    row["options"] = options
    row["results"] = results
    return row


def cast_vote(company_id: int, vote_id: int, option: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM civ_votes WHERE id = ? AND company_id = ? AND status = 'open'", (vote_id, company_id))
    row = cursor.fetchone()
    if not row:
        return None
    data = dict(row)
    results = json.loads(data.get("results") or "{}")
    if option not in results:
        return None
    results[option] = results.get(option, 0) + 1
    cursor.execute("UPDATE civ_votes SET results = ? WHERE id = ?", (json.dumps(results), vote_id))
    conn.commit()
    data["results"] = results
    data["options"] = json.loads(data.get("options") or "[]")
    return data


def list_votes(company_id: int, status: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if status:
        cursor.execute(
            "SELECT * FROM civ_votes WHERE company_id = ? AND status = ? ORDER BY created_at DESC",
            (company_id, status),
        )
    else:
        cursor.execute(
            "SELECT * FROM civ_votes WHERE company_id = ? ORDER BY created_at DESC LIMIT 30",
            (company_id,),
        )
    rows = []
    for r in cursor.fetchall():
        data = dict(r)
        data["options"] = json.loads(data.get("options") or "[]")
        data["results"] = json.loads(data.get("results") or "{}")
        rows.append(data)
    return rows


def close_vote(company_id: int, vote_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE civ_votes SET status = 'closed', closed_at = datetime('now') WHERE id = ? AND company_id = ?",
        (vote_id, company_id),
    )
    conn.commit()
    cursor.execute("SELECT * FROM civ_votes WHERE id = ? AND company_id = ?", (vote_id, company_id))
    row = cursor.fetchone()
    if not row:
        return None
    data = dict(row)
    data["options"] = json.loads(data.get("options") or "[]")
    data["results"] = json.loads(data.get("results") or "{}")
    return data


def create_policy(company_id: int, title: str, category: str, content: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO civ_policies (company_id, title, category, content) VALUES (?,?,?,?)",
        (company_id, title, category, content),
    )
    conn.commit()
    cursor.execute("SELECT * FROM civ_policies WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_policies(company_id: int, category: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if category:
        cursor.execute(
            "SELECT * FROM civ_policies WHERE company_id = ? AND category = ? AND status = 'active' ORDER BY created_at DESC",
            (company_id, category),
        )
    else:
        cursor.execute(
            "SELECT * FROM civ_policies WHERE company_id = ? AND status = 'active' ORDER BY created_at DESC",
            (company_id,),
        )
    return [dict(r) for r in cursor.fetchall()]


def record_decision(company_id: int, title: str, decision_type: str, outcome: str, vote_id: int | None = None) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO civ_decisions (company_id, title, decision_type, outcome, vote_id) VALUES (?,?,?,?,?)",
        (company_id, title, decision_type, outcome, vote_id),
    )
    conn.commit()
    cursor.execute("SELECT * FROM civ_decisions WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_decisions(company_id: int, limit: int = 30) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM civ_decisions WHERE company_id = ? ORDER BY created_at DESC LIMIT ?",
        (company_id, limit),
    )
    return [dict(r) for r in cursor.fetchall()]


# ── Education ─────────────────────────────────────────────────────────────────

def create_training(company_id: int, employee_key: str, course_title: str, course_type: str = "training") -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO civ_training (company_id, employee_key, course_title, course_type)
        VALUES (?,?,?,?)
        """,
        (company_id, employee_key, course_title, course_type),
    )
    conn.commit()
    cursor.execute("SELECT * FROM civ_training WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def update_training_progress(company_id: int, training_id: int, progress: float) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    progress = min(max(progress, 0), 100)
    if progress >= 100:
        cursor.execute(
            """
            UPDATE civ_training
            SET progress = 100, status = 'completed', certified = 1, completed_at = datetime('now')
            WHERE id = ? AND company_id = ?
            """,
            (training_id, company_id),
        )
    else:
        cursor.execute(
            "UPDATE civ_training SET progress = ?, status = 'in_progress' WHERE id = ? AND company_id = ?",
            (progress, training_id, company_id),
        )
    conn.commit()
    cursor.execute("SELECT * FROM civ_training WHERE id = ? AND company_id = ?", (training_id, company_id))
    row = cursor.fetchone()
    return dict(row) if row else None


def list_training(company_id: int, employee_key: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if employee_key:
        cursor.execute(
            "SELECT * FROM civ_training WHERE company_id = ? AND employee_key = ? ORDER BY created_at DESC",
            (company_id, employee_key),
        )
    else:
        cursor.execute(
            "SELECT * FROM civ_training WHERE company_id = ? ORDER BY created_at DESC LIMIT 50",
            (company_id,),
        )
    return [dict(r) for r in cursor.fetchall()]


def upsert_skill(company_id: int, employee_key: str, skill_name: str, level: float, category: str = "general") -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM civ_skills WHERE company_id = ? AND employee_key = ? AND skill_name = ?",
        (company_id, employee_key, skill_name),
    )
    existing = cursor.fetchone()
    if existing:
        cursor.execute(
            "UPDATE civ_skills SET level = ?, category = ?, updated_at = datetime('now') WHERE id = ?",
            (level, category, existing[0]),
        )
        row_id = existing[0]
    else:
        cursor.execute(
            "INSERT INTO civ_skills (company_id, employee_key, skill_name, level, category) VALUES (?,?,?,?,?)",
            (company_id, employee_key, skill_name, level, category),
        )
        row_id = cursor.lastrowid
    conn.commit()
    cursor.execute("SELECT * FROM civ_skills WHERE id = ?", (row_id,))
    return dict(cursor.fetchone())


def list_skills(company_id: int, employee_key: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if employee_key:
        cursor.execute(
            "SELECT * FROM civ_skills WHERE company_id = ? AND employee_key = ? ORDER BY level DESC",
            (company_id, employee_key),
        )
    else:
        cursor.execute(
            "SELECT * FROM civ_skills WHERE company_id = ? ORDER BY updated_at DESC LIMIT 50",
            (company_id,),
        )
    return [dict(r) for r in cursor.fetchall()]


def create_certification(company_id: int, employee_key: str, cert_name: str, issuer: str = "Aura Academy") -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO civ_certifications (company_id, employee_key, cert_name, issuer) VALUES (?,?,?,?)",
        (company_id, employee_key, cert_name, issuer),
    )
    conn.commit()
    cursor.execute("SELECT * FROM civ_certifications WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_certifications(company_id: int, employee_key: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if employee_key:
        cursor.execute(
            "SELECT * FROM civ_certifications WHERE company_id = ? AND employee_key = ? ORDER BY created_at DESC",
            (company_id, employee_key),
        )
    else:
        cursor.execute(
            "SELECT * FROM civ_certifications WHERE company_id = ? ORDER BY created_at DESC LIMIT 50",
            (company_id,),
        )
    return [dict(r) for r in cursor.fetchall()]


# ── Economy ───────────────────────────────────────────────────────────────────

def get_or_create_account(company_id: int, account_key: str, account_type: str = "employee") -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM civ_economy_accounts WHERE company_id = ? AND account_key = ?",
        (company_id, account_key),
    )
    row = cursor.fetchone()
    if row:
        return dict(row)
    cursor.execute(
        "INSERT INTO civ_economy_accounts (company_id, account_key, balance, account_type) VALUES (?,?,0,?)",
        (company_id, account_key, account_type),
    )
    conn.commit()
    cursor.execute("SELECT * FROM civ_economy_accounts WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_accounts(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM civ_economy_accounts WHERE company_id = ? ORDER BY balance DESC",
        (company_id,),
    )
    return [dict(r) for r in cursor.fetchall()]


def grant_reward(company_id: int, account_key: str, amount: float, reason: str, reward_type: str = "incentive") -> dict:
    account = get_or_create_account(company_id, account_key)
    conn = get_connection()
    cursor = conn.cursor()
    new_balance = account["balance"] + amount
    cursor.execute(
        "UPDATE civ_economy_accounts SET balance = ? WHERE company_id = ? AND account_key = ?",
        (new_balance, company_id, account_key),
    )
    cursor.execute(
        "INSERT INTO civ_rewards (company_id, account_key, amount, reason, reward_type) VALUES (?,?,?,?,?)",
        (company_id, account_key, amount, reason, reward_type),
    )
    conn.commit()
    cursor.execute("SELECT * FROM civ_rewards WHERE id = ?", (cursor.lastrowid,))
    reward = dict(cursor.fetchone())
    reward["new_balance"] = new_balance
    return reward


def list_rewards(company_id: int, limit: int = 30) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM civ_rewards WHERE company_id = ? ORDER BY created_at DESC LIMIT ?",
        (company_id, limit),
    )
    return [dict(r) for r in cursor.fetchall()]


def record_performance(company_id: int, account_key: str, metric_name: str, metric_value: float, period: str = "monthly") -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO civ_performance (company_id, account_key, metric_name, metric_value, period)
        VALUES (?,?,?,?,?)
        """,
        (company_id, account_key, metric_name, metric_value, period),
    )
    conn.commit()
    cursor.execute("SELECT * FROM civ_performance WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_performance(company_id: int, account_key: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if account_key:
        cursor.execute(
            "SELECT * FROM civ_performance WHERE company_id = ? AND account_key = ? ORDER BY created_at DESC LIMIT 30",
            (company_id, account_key),
        )
    else:
        cursor.execute(
            "SELECT * FROM civ_performance WHERE company_id = ? ORDER BY created_at DESC LIMIT 50",
            (company_id,),
        )
    return [dict(r) for r in cursor.fetchall()]


# ── Infrastructure ────────────────────────────────────────────────────────────

def upsert_infra_node(company_id: int, node_type: str, name: str, status: str = "healthy",
                      metrics: dict | None = None, config: dict | None = None) -> dict:
    encrypted_config = encrypt_value(json.dumps(config or {}))
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM civ_infra_nodes WHERE company_id = ? AND node_type = ? AND name = ?",
        (company_id, node_type, name),
    )
    existing = cursor.fetchone()
    if existing:
        cursor.execute(
            """
            UPDATE civ_infra_nodes
            SET status = ?, metrics = ?, config = ?, last_check = datetime('now')
            WHERE id = ?
            """,
            (status, json.dumps(metrics or {}), encrypted_config, existing[0]),
        )
        row_id = existing[0]
    else:
        cursor.execute(
            """
            INSERT INTO civ_infra_nodes (company_id, node_type, name, status, metrics, config)
            VALUES (?,?,?,?,?,?)
            """,
            (company_id, node_type, name, status, json.dumps(metrics or {}), encrypted_config),
        )
        row_id = cursor.lastrowid
    conn.commit()
    cursor.execute("SELECT * FROM civ_infra_nodes WHERE id = ?", (row_id,))
    row = dict(cursor.fetchone())
    row["metrics"] = metrics or {}
    row["config"] = config or {}
    return row


def list_infra_nodes(company_id: int, node_type: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if node_type:
        cursor.execute(
            "SELECT * FROM civ_infra_nodes WHERE company_id = ? AND node_type = ?",
            (company_id, node_type),
        )
    else:
        cursor.execute("SELECT * FROM civ_infra_nodes WHERE company_id = ?", (company_id,))
    rows = []
    for r in cursor.fetchall():
        data = dict(r)
        try:
            data["metrics"] = json.loads(data.get("metrics") or "{}")
        except Exception:
            data["metrics"] = {}
        try:
            data["config"] = json.loads(decrypt_value(data.get("config") or "{}"))
        except Exception:
            data["config"] = {}
        rows.append(data)
    return rows


def create_backup(company_id: int, backup_type: str = "full", location: str = "", size_mb: float = 0) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO civ_backups (company_id, backup_type, location, size_mb, encrypted)
        VALUES (?,?,?,?,1)
        """,
        (company_id, backup_type, location or f"s3://aura-backups/{company_id}/latest", size_mb),
    )
    conn.commit()
    cursor.execute("SELECT * FROM civ_backups WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_backups(company_id: int, limit: int = 20) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM civ_backups WHERE company_id = ? ORDER BY created_at DESC LIMIT ?",
        (company_id, limit),
    )
    return [dict(r) for r in cursor.fetchall()]


# ── Research ──────────────────────────────────────────────────────────────────

def save_research(company_id: int, research_type: str, title: str, findings: dict, summary: str) -> dict:
    encrypted = encrypt_value(json.dumps(findings))
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO civ_research (company_id, research_type, title, findings, summary)
        VALUES (?,?,?,?,?)
        """,
        (company_id, research_type, title, encrypted, summary[:1000]),
    )
    conn.commit()
    cursor.execute("SELECT * FROM civ_research WHERE id = ?", (cursor.lastrowid,))
    row = dict(cursor.fetchone())
    row["findings"] = findings
    return row


def list_research(company_id: int, research_type: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if research_type:
        cursor.execute(
            "SELECT * FROM civ_research WHERE company_id = ? AND research_type = ? ORDER BY created_at DESC LIMIT 30",
            (company_id, research_type),
        )
    else:
        cursor.execute(
            "SELECT * FROM civ_research WHERE company_id = ? ORDER BY created_at DESC LIMIT 50",
            (company_id,),
        )
    rows = []
    for r in cursor.fetchall():
        data = dict(r)
        try:
            data["findings"] = json.loads(decrypt_value(data.get("findings") or "{}"))
        except Exception:
            try:
                data["findings"] = json.loads(data.get("findings") or "{}")
            except Exception:
                data["findings"] = {}
        rows.append(data)
    return rows

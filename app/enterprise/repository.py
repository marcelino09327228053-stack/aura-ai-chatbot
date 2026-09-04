"""Enterprise platform data access layer."""

import json

from app.cloud.security import encrypt_value
from app.infrastructure.database import get_connection


# ── Goals ─────────────────────────────────────────────────────────────────────

def create_goal(company_id: int, data: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO enterprise_goals
            (company_id, title, description, category, target_value,
             current_value, unit, deadline, priority)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (
            company_id,
            data.get("title", ""),
            data.get("description", ""),
            data.get("category", "growth"),
            data.get("target_value", 0),
            data.get("current_value", 0),
            data.get("unit", ""),
            data.get("deadline", ""),
            data.get("priority", "medium"),
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM enterprise_goals WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_goals(company_id: int, status: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if status:
        cursor.execute(
            "SELECT * FROM enterprise_goals WHERE company_id = ? AND status = ? ORDER BY priority DESC, created_at DESC",
            (company_id, status),
        )
    else:
        cursor.execute(
            "SELECT * FROM enterprise_goals WHERE company_id = ? ORDER BY priority DESC, created_at DESC",
            (company_id,),
        )
    return [dict(r) for r in cursor.fetchall()]


def update_goal_progress(goal_id: int, company_id: int, current_value: float, status: str | None = None) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    if status:
        cursor.execute(
            "UPDATE enterprise_goals SET current_value = ?, status = ?, updated_at = datetime('now') WHERE id = ? AND company_id = ?",
            (current_value, status, goal_id, company_id),
        )
    else:
        cursor.execute(
            "UPDATE enterprise_goals SET current_value = ?, updated_at = datetime('now') WHERE id = ? AND company_id = ?",
            (current_value, goal_id, company_id),
        )
    conn.commit()
    cursor.execute("SELECT * FROM enterprise_goals WHERE id = ?", (goal_id,))
    row = cursor.fetchone()
    return dict(row) if row else {}


# ── KPIs ──────────────────────────────────────────────────────────────────────

def record_kpi(company_id: int, data: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO enterprise_kpis
            (company_id, name, category, value, target, unit, period, trend)
        VALUES (?,?,?,?,?,?,?,?)
        """,
        (
            company_id,
            data.get("name", ""),
            data.get("category", "financial"),
            data.get("value", 0),
            data.get("target", 0),
            data.get("unit", ""),
            data.get("period", "monthly"),
            data.get("trend", "stable"),
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM enterprise_kpis WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_kpis(company_id: int, category: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if category:
        cursor.execute(
            "SELECT * FROM enterprise_kpis WHERE company_id = ? AND category = ? ORDER BY recorded_at DESC",
            (company_id, category),
        )
    else:
        cursor.execute(
            "SELECT * FROM enterprise_kpis WHERE company_id = ? ORDER BY recorded_at DESC",
            (company_id,),
        )
    return [dict(r) for r in cursor.fetchall()]


# ── Plans ─────────────────────────────────────────────────────────────────────

def create_plan(company_id: int, data: dict, user_id: int | None = None) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    milestones = json.dumps(data.get("milestones", []))
    cursor.execute(
        """
        INSERT INTO enterprise_plans
            (company_id, title, plan_type, description, start_date, end_date, budget, milestones, created_by)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (
            company_id,
            data.get("title", ""),
            data.get("plan_type", "annual"),
            data.get("description", ""),
            data.get("start_date", ""),
            data.get("end_date", ""),
            data.get("budget", 0),
            milestones,
            user_id,
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM enterprise_plans WHERE id = ?", (cursor.lastrowid,))
    row = dict(cursor.fetchone())
    row["milestones"] = data.get("milestones", [])
    return row


def list_plans(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM enterprise_plans WHERE company_id = ? ORDER BY created_at DESC",
        (company_id,),
    )
    rows = []
    for r in cursor.fetchall():
        data = dict(r)
        try:
            data["milestones"] = json.loads(data.get("milestones") or "[]")
        except Exception:
            data["milestones"] = []
        rows.append(data)
    return rows


# ── Forecasts ─────────────────────────────────────────────────────────────────

def save_forecast(company_id: int, forecast_type: str, period: str, periods_ahead: int,
                  value: float, confidence: float, assumptions: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    assumptions_enc = encrypt_value(json.dumps(assumptions))
    cursor.execute(
        """
        INSERT INTO enterprise_forecasts
            (company_id, forecast_type, period, periods_ahead, value, confidence, assumptions)
        VALUES (?,?,?,?,?,?,?)
        """,
        (company_id, forecast_type, period, periods_ahead, value, confidence, assumptions_enc),
    )
    conn.commit()
    cursor.execute("SELECT * FROM enterprise_forecasts WHERE id = ?", (cursor.lastrowid,))
    row = dict(cursor.fetchone())
    row["assumptions"] = assumptions
    return row


def list_forecasts(company_id: int, forecast_type: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if forecast_type:
        cursor.execute(
            "SELECT id, company_id, forecast_type, period, periods_ahead, value, confidence, created_at FROM enterprise_forecasts WHERE company_id = ? AND forecast_type = ? ORDER BY created_at DESC LIMIT 20",
            (company_id, forecast_type),
        )
    else:
        cursor.execute(
            "SELECT id, company_id, forecast_type, period, periods_ahead, value, confidence, created_at FROM enterprise_forecasts WHERE company_id = ? ORDER BY created_at DESC LIMIT 30",
            (company_id,),
        )
    return [dict(r) for r in cursor.fetchall()]


# ── Policies ──────────────────────────────────────────────────────────────────

def create_policy(company_id: int, data: dict, user_id: int | None = None) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO enterprise_policies
            (company_id, title, category, content, version, effective_date, approved_by)
        VALUES (?,?,?,?,?,?,?)
        """,
        (
            company_id,
            data.get("title", ""),
            data.get("category", "general"),
            data.get("content", ""),
            data.get("version", "1.0"),
            data.get("effective_date", ""),
            user_id,
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM enterprise_policies WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_policies(company_id: int, category: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if category:
        cursor.execute(
            "SELECT * FROM enterprise_policies WHERE company_id = ? AND category = ? AND status = 'active' ORDER BY created_at DESC",
            (company_id, category),
        )
    else:
        cursor.execute(
            "SELECT * FROM enterprise_policies WHERE company_id = ? AND status = 'active' ORDER BY created_at DESC",
            (company_id,),
        )
    return [dict(r) for r in cursor.fetchall()]


# ── Approvals ─────────────────────────────────────────────────────────────────

def create_approval_request(company_id: int, data: dict, user_id: int) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO enterprise_approvals
            (company_id, request_type, title, description, requested_by, assigned_to, amount)
        VALUES (?,?,?,?,?,?,?)
        """,
        (
            company_id,
            data.get("request_type", "general"),
            data.get("title", ""),
            data.get("description", ""),
            user_id,
            data.get("assigned_to"),
            data.get("amount", 0),
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM enterprise_approvals WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_approvals(company_id: int, status: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if status:
        cursor.execute(
            "SELECT * FROM enterprise_approvals WHERE company_id = ? AND status = ? ORDER BY created_at DESC",
            (company_id, status),
        )
    else:
        cursor.execute(
            "SELECT * FROM enterprise_approvals WHERE company_id = ? ORDER BY created_at DESC",
            (company_id,),
        )
    return [dict(r) for r in cursor.fetchall()]


def decide_approval(approval_id: int, company_id: int, status: str, note: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE enterprise_approvals
        SET status = ?, decision_note = ?, decided_at = datetime('now')
        WHERE id = ? AND company_id = ?
        """,
        (status, note[:500], approval_id, company_id),
    )
    conn.commit()
    cursor.execute("SELECT * FROM enterprise_approvals WHERE id = ?", (approval_id,))
    row = cursor.fetchone()
    return dict(row) if row else {}


# ── Compliance ────────────────────────────────────────────────────────────────

def save_compliance_check(company_id: int, check_type: str, result: dict, passed: bool, notes: str = "") -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO enterprise_compliance_checks
            (company_id, check_type, status, result, passed, notes)
        VALUES (?,?,?,?,?,?)
        """,
        (company_id, check_type, "completed", json.dumps(result), int(passed), notes[:500]),
    )
    conn.commit()
    cursor.execute("SELECT * FROM enterprise_compliance_checks WHERE id = ?", (cursor.lastrowid,))
    row = dict(cursor.fetchone())
    try:
        row["result"] = json.loads(row.get("result") or "{}")
    except Exception:
        row["result"] = {}
    return row


def list_compliance_checks(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM enterprise_compliance_checks WHERE company_id = ? ORDER BY checked_at DESC LIMIT 30",
        (company_id,),
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


# ── Audit ─────────────────────────────────────────────────────────────────────

def log_enterprise_action(
    company_id: int,
    action: str,
    user_id: int | None = None,
    resource_type: str = "",
    resource_id: int | None = None,
    details: str = "",
) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO enterprise_audit
            (company_id, user_id, action, resource_type, resource_id, details)
        VALUES (?,?,?,?,?,?)
        """,
        (company_id, user_id, action, resource_type, resource_id, details[:500]),
    )
    conn.commit()


def list_audit_log(company_id: int, limit: int = 50) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM enterprise_audit WHERE company_id = ? ORDER BY created_at DESC LIMIT ?",
        (company_id, limit),
    )
    return [dict(r) for r in cursor.fetchall()]

"""Economic Network data access."""

import json

from app.cloud.security import encrypt_value
from app.infrastructure.database import get_connection


def log_economy_action(company_id: int, action: str, user_id: int | None = None, details: str = "") -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO economy_audit (company_id, user_id, action, details) VALUES (?,?,?,?)",
        (company_id, user_id, action, details[:500]),
    )
    conn.commit()


def save_market(company_id: int, data: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO economy_markets
            (company_id, market_name, sector, region, size_estimate, growth_rate, competition_level, notes)
        VALUES (?,?,?,?,?,?,?,?)
        """,
        (
            company_id,
            data.get("market_name", ""),
            data.get("sector", "general"),
            data.get("region", "local"),
            data.get("size_estimate", 0),
            data.get("growth_rate", 0),
            data.get("competition_level", "medium"),
            data.get("notes", ""),
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM economy_markets WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_markets(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM economy_markets WHERE company_id = ? ORDER BY created_at DESC",
        (company_id,),
    )
    return [dict(r) for r in cursor.fetchall()]


def save_partner(company_id: int, data: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO economy_partners
            (company_id, partner_type, name, contact, status, rating, notes)
        VALUES (?,?,?,?,?,?,?)
        """,
        (
            company_id,
            data.get("partner_type", "supplier"),
            data.get("name", ""),
            data.get("contact", ""),
            data.get("status", "active"),
            data.get("rating", 0),
            data.get("notes", ""),
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM economy_partners WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_partners(company_id: int, partner_type: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if partner_type:
        cursor.execute(
            "SELECT * FROM economy_partners WHERE company_id = ? AND partner_type = ? ORDER BY rating DESC",
            (company_id, partner_type),
        )
    else:
        cursor.execute(
            "SELECT * FROM economy_partners WHERE company_id = ? ORDER BY created_at DESC",
            (company_id,),
        )
    return [dict(r) for r in cursor.fetchall()]


def save_joint_project(company_id: int, data: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO economy_joint_projects
            (company_id, partner_id, title, description, budget, status, start_date, end_date)
        VALUES (?,?,?,?,?,?,?,?)
        """,
        (
            company_id,
            data.get("partner_id"),
            data.get("title", ""),
            data.get("description", ""),
            data.get("budget", 0),
            data.get("status", "planning"),
            data.get("start_date", ""),
            data.get("end_date", ""),
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM economy_joint_projects WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_joint_projects(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM economy_joint_projects WHERE company_id = ? ORDER BY created_at DESC",
        (company_id,),
    )
    return [dict(r) for r in cursor.fetchall()]


def save_forecast(company_id: int, forecast_type: str, period: str, periods_ahead: int,
                  value: float, confidence: float, assumptions: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    assumptions_enc = encrypt_value(json.dumps(assumptions))
    cursor.execute(
        """
        INSERT INTO economy_forecasts
            (company_id, forecast_type, period, periods_ahead, value, confidence, assumptions)
        VALUES (?,?,?,?,?,?,?)
        """,
        (company_id, forecast_type, period, periods_ahead, value, confidence, assumptions_enc),
    )
    conn.commit()
    cursor.execute("SELECT * FROM economy_forecasts WHERE id = ?", (cursor.lastrowid,))
    row = dict(cursor.fetchone())
    row["assumptions"] = assumptions
    return row


def list_forecasts(company_id: int, forecast_type: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if forecast_type:
        cursor.execute(
            """
            SELECT id, company_id, forecast_type, period, periods_ahead, value, confidence, created_at
            FROM economy_forecasts WHERE company_id = ? AND forecast_type = ?
            ORDER BY created_at DESC LIMIT 30
            """,
            (company_id, forecast_type),
        )
    else:
        cursor.execute(
            """
            SELECT id, company_id, forecast_type, period, periods_ahead, value, confidence, created_at
            FROM economy_forecasts WHERE company_id = ? ORDER BY created_at DESC LIMIT 50
            """,
            (company_id,),
        )
    return [dict(r) for r in cursor.fetchall()]


def save_report(company_id: int, report_type: str, title: str, content: dict, summary: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO economy_reports (company_id, report_type, title, content, summary)
        VALUES (?,?,?,?,?)
        """,
        (company_id, report_type, title, json.dumps(content), summary[:1000]),
    )
    conn.commit()
    cursor.execute("SELECT * FROM economy_reports WHERE id = ?", (cursor.lastrowid,))
    row = dict(cursor.fetchone())
    try:
        row["content"] = json.loads(row.get("content") or "{}")
    except Exception:
        row["content"] = {}
    return row


def list_reports(company_id: int, report_type: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if report_type:
        cursor.execute(
            "SELECT * FROM economy_reports WHERE company_id = ? AND report_type = ? ORDER BY created_at DESC LIMIT 20",
            (company_id, report_type),
        )
    else:
        cursor.execute(
            "SELECT * FROM economy_reports WHERE company_id = ? ORDER BY created_at DESC LIMIT 30",
            (company_id,),
        )
    rows = []
    for r in cursor.fetchall():
        data = dict(r)
        try:
            data["content"] = json.loads(data.get("content") or "{}")
        except Exception:
            data["content"] = {}
        rows.append(data)
    return rows


def save_opportunity(company_id: int, data: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO economy_opportunities
            (company_id, opportunity_type, title, description, estimated_value, priority)
        VALUES (?,?,?,?,?,?)
        """,
        (
            company_id,
            data.get("opportunity_type", "market"),
            data.get("title", ""),
            data.get("description", ""),
            data.get("estimated_value", 0),
            data.get("priority", "medium"),
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM economy_opportunities WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_opportunities(company_id: int, status: str = "open") -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM economy_opportunities WHERE company_id = ? AND status = ? ORDER BY estimated_value DESC",
        (company_id, status),
    )
    return [dict(r) for r in cursor.fetchall()]


def list_audit(company_id: int, limit: int = 50) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM economy_audit WHERE company_id = ? ORDER BY created_at DESC LIMIT ?",
        (company_id, limit),
    )
    return [dict(r) for r in cursor.fetchall()]

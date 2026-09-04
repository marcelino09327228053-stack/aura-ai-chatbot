"""Corporation platform data access."""

import json

from app.cloud.security import encrypt_value
from app.infrastructure.database import get_connection


# ── Decisions ─────────────────────────────────────────────────────────────────

def save_decision(company_id: int, agent_role: str, decision_type: str, title: str,
                  analysis: str, recommendation: str, confidence: float = 0.7) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO corp_decisions
            (company_id, agent_role, decision_type, title, analysis, recommendation, confidence)
        VALUES (?,?,?,?,?,?,?)
        """,
        (company_id, agent_role, decision_type, title, analysis[:2000], recommendation[:2000], confidence),
    )
    conn.commit()
    cursor.execute("SELECT * FROM corp_decisions WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_decisions(company_id: int, agent_role: str | None = None, limit: int = 30) -> list[dict]:
    cursor = get_connection().cursor()
    if agent_role:
        cursor.execute(
            "SELECT * FROM corp_decisions WHERE company_id = ? AND agent_role = ? ORDER BY created_at DESC LIMIT ?",
            (company_id, agent_role, limit),
        )
    else:
        cursor.execute(
            "SELECT * FROM corp_decisions WHERE company_id = ? ORDER BY created_at DESC LIMIT ?",
            (company_id, limit),
        )
    return [dict(r) for r in cursor.fetchall()]


def approve_decision(decision_id: int, company_id: int, user_id: int) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE corp_decisions SET status = 'approved', approved_by = ? WHERE id = ? AND company_id = ?",
        (user_id, decision_id, company_id),
    )
    conn.commit()
    cursor.execute("SELECT * FROM corp_decisions WHERE id = ?", (decision_id,))
    row = cursor.fetchone()
    return dict(row) if row else {}


# ── Negotiations ──────────────────────────────────────────────────────────────

def save_negotiation(company_id: int, data: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    our_enc = encrypt_value(json.dumps(data.get("our_position", {})))
    cursor.execute(
        """
        INSERT INTO corp_negotiations
            (company_id, negotiation_type, counterparty, subject, our_position, their_position, proposed_terms)
        VALUES (?,?,?,?,?,?,?)
        """,
        (
            company_id,
            data.get("negotiation_type", "supplier"),
            data.get("counterparty", ""),
            data.get("subject", ""),
            our_enc,
            json.dumps(data.get("their_position", {})),
            json.dumps(data.get("proposed_terms", {})),
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM corp_negotiations WHERE id = ?", (cursor.lastrowid,))
    row = dict(cursor.fetchone())
    row["our_position"] = data.get("our_position", {})
    row["their_position"] = data.get("their_position", {})
    row["proposed_terms"] = data.get("proposed_terms", {})
    return row


def list_negotiations(company_id: int, status: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if status:
        cursor.execute(
            "SELECT id, company_id, negotiation_type, counterparty, subject, proposed_terms, status, outcome, created_at FROM corp_negotiations WHERE company_id = ? AND status = ? ORDER BY created_at DESC",
            (company_id, status),
        )
    else:
        cursor.execute(
            "SELECT id, company_id, negotiation_type, counterparty, subject, proposed_terms, status, outcome, created_at FROM corp_negotiations WHERE company_id = ? ORDER BY created_at DESC",
            (company_id,),
        )
    rows = []
    for r in cursor.fetchall():
        data = dict(r)
        try:
            data["proposed_terms"] = json.loads(data.get("proposed_terms") or "{}")
        except Exception:
            data["proposed_terms"] = {}
        rows.append(data)
    return rows


# ── Investments ───────────────────────────────────────────────────────────────

def save_investment(company_id: int, data: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO corp_investments
            (company_id, investment_type, name, amount, expected_return,
             roi_pct, payback_months, risk_level, notes)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (
            company_id,
            data.get("investment_type", "capex"),
            data.get("name", ""),
            data.get("amount", 0),
            data.get("expected_return", 0),
            data.get("roi_pct", 0),
            data.get("payback_months", 0),
            data.get("risk_level", "medium"),
            data.get("notes", ""),
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM corp_investments WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_investments(company_id: int, status: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if status:
        cursor.execute(
            "SELECT * FROM corp_investments WHERE company_id = ? AND status = ? ORDER BY created_at DESC",
            (company_id, status),
        )
    else:
        cursor.execute(
            "SELECT * FROM corp_investments WHERE company_id = ? ORDER BY created_at DESC",
            (company_id,),
        )
    return [dict(r) for r in cursor.fetchall()]


# ── Risks ─────────────────────────────────────────────────────────────────────

def save_risk(company_id: int, data: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    likelihood_score = {"low": 1, "medium": 2, "high": 3}.get(data.get("likelihood", "medium"), 2)
    impact_score = {"low": 1, "medium": 2, "high": 3}.get(data.get("impact", "medium"), 2)
    risk_score = likelihood_score * impact_score
    cursor.execute(
        """
        INSERT INTO corp_risks
            (company_id, risk_type, title, description, likelihood, impact, risk_score, mitigation)
        VALUES (?,?,?,?,?,?,?,?)
        """,
        (
            company_id,
            data.get("risk_type", "operational"),
            data.get("title", ""),
            data.get("description", ""),
            data.get("likelihood", "medium"),
            data.get("impact", "medium"),
            risk_score,
            data.get("mitigation", ""),
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM corp_risks WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_risks(company_id: int, risk_type: str | None = None, status: str = "open") -> list[dict]:
    cursor = get_connection().cursor()
    if risk_type:
        cursor.execute(
            "SELECT * FROM corp_risks WHERE company_id = ? AND risk_type = ? AND status = ? ORDER BY risk_score DESC",
            (company_id, risk_type, status),
        )
    else:
        cursor.execute(
            "SELECT * FROM corp_risks WHERE company_id = ? AND status = ? ORDER BY risk_score DESC",
            (company_id, status),
        )
    return [dict(r) for r in cursor.fetchall()]


# ── Audit ─────────────────────────────────────────────────────────────────────

def log_corp_action(company_id: int, action: str, agent_role: str = "system", details: str = "") -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO corp_audit (company_id, agent_role, action, details) VALUES (?,?,?,?)",
        (company_id, agent_role, action, details[:500]),
    )
    conn.commit()


def list_audit(company_id: int, limit: int = 50) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM corp_audit WHERE company_id = ? ORDER BY created_at DESC LIMIT ?",
        (company_id, limit),
    )
    return [dict(r) for r in cursor.fetchall()]

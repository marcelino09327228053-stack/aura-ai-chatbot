"""Persistence operations for human referral agents and commissions."""
import secrets
from datetime import datetime, timezone

from app.infrastructure.database import get_connection

# Kept available to the service without opening a second persistence abstraction.


def current_pricing() -> dict:
    row = get_connection().cursor().execute(
        "SELECT * FROM platform_pricing_rules ORDER BY effective_at DESC, id DESC LIMIT 1"
    ).fetchone()
    return dict(row)


def create_pricing_rule(values: dict, created_by: str = "owner") -> dict:
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("""INSERT INTO platform_pricing_rules
        (monthly_platform_price_minor,initial_ai_credit_minor,minimum_ai_topup_minor,
         referral_commission_minor,ai_usage_markup_bps,currency,effective_at,created_by)
        VALUES (?,?,?,?,?,?,?,?)""", (
        values["monthly_platform_price_minor"], values["initial_ai_credit_minor"],
        values["minimum_ai_topup_minor"], values["referral_commission_minor"],
        values["ai_usage_markup_bps"], values.get("currency", "PHP"),
        datetime.now(timezone.utc).isoformat(), created_by,
    )); conn.commit(); return current_pricing()


def get_agent_by_user(user_id: int) -> dict | None:
    row = get_connection().cursor().execute(
        "SELECT * FROM referral_agents WHERE user_id=?", (user_id,)
    ).fetchone()
    return dict(row) if row else None


def get_agent_by_code(code: str, active_only: bool = False) -> dict | None:
    sql = "SELECT * FROM referral_agents WHERE referral_code=?"
    params = [code.upper().strip()]
    if active_only: sql += " AND status='approved'"
    row = get_connection().cursor().execute(sql, params).fetchone()
    return dict(row) if row else None


def get_agent(agent_id: int, active_only: bool = False) -> dict | None:
    sql = "SELECT * FROM referral_agents WHERE id=?"
    if active_only: sql += " AND status='approved'"
    row = get_connection().cursor().execute(sql, (agent_id,)).fetchone()
    return dict(row) if row else None


def apply_for_agent(user_id: int) -> tuple[dict, bool]:
    existing = get_agent_by_user(user_id)
    if existing: return existing, False
    conn = get_connection(); cursor = conn.cursor()
    for _ in range(8):
        code = secrets.token_hex(5).upper()
        try:
            cursor.execute("INSERT INTO referral_agents(user_id,referral_code) VALUES(?,?)", (user_id, code))
            conn.commit(); return get_agent_by_user(user_id), True
        except Exception:
            conn.rollback()
    raise RuntimeError("Unable to generate a unique referral code.")


def set_agent_status(agent_id: int, status: str, notes: str = "") -> dict | None:
    conn = get_connection(); now = datetime.now(timezone.utc).isoformat()
    conn.cursor().execute("""UPDATE referral_agents SET status=?, payout_eligible=?, admin_notes=?,
        approved_at=CASE WHEN ?='approved' THEN COALESCE(approved_at,?) ELSE approved_at END,
        suspended_at=CASE WHEN ?='suspended' THEN ? ELSE NULL END WHERE id=?""",
        (status, 1 if status == "approved" else 0, notes[:1000], status, now, status, now, agent_id))
    conn.commit()
    row = conn.cursor().execute("SELECT * FROM referral_agents WHERE id=?", (agent_id,)).fetchone()
    return dict(row) if row else None


def list_agents() -> list[dict]:
    rows = get_connection().cursor().execute("""SELECT a.*,u.email,u.full_name,
        (SELECT COUNT(*) FROM customer_referral_attributions x WHERE x.referral_agent_id=a.id) referred_count
        FROM referral_agents a JOIN users u ON u.id=a.user_id ORDER BY a.created_at DESC""").fetchall()
    return [dict(row) for row in rows]


def record_click(agent_id: int, click_token: str) -> None:
    conn = get_connection(); conn.cursor().execute(
        "INSERT INTO referral_clicks(referral_agent_id,click_token) VALUES(?,?)", (agent_id, click_token)
    ); conn.commit()


def create_attribution(company_id: int, customer_user_id: int, agent_id: int) -> tuple[dict | None, bool]:
    agent = get_connection().cursor().execute("SELECT * FROM referral_agents WHERE id=?", (agent_id,)).fetchone()
    if not agent or agent["status"] != "approved" or agent["user_id"] == customer_user_id:
        return None, False
    conn = get_connection(); cursor = conn.cursor()
    try:
        cursor.execute("""INSERT INTO customer_referral_attributions
            (company_id,customer_user_id,referral_agent_id,referral_code_snapshot)
            VALUES(?,?,?,?)""", (company_id, customer_user_id, agent_id, agent["referral_code"]))
        conn.commit(); created = True
    except Exception:
        conn.rollback(); created = False
    row = get_connection().cursor().execute(
        "SELECT * FROM customer_referral_attributions WHERE company_id=?", (company_id,)
    ).fetchone()
    return (dict(row) if row else None), created


def dashboard_for_user(user_id: int) -> dict | None:
    agent = get_agent_by_user(user_id)
    if not agent: return None
    c = get_connection().cursor(); aid = agent["id"]
    counts = c.execute("""SELECT COUNT(*) clients,
      COALESCE(SUM(CASE WHEN s.status='active' AND s.plan!='free' THEN 1 ELSE 0 END),0) active_clients
      FROM customer_referral_attributions a JOIN subscriptions s ON s.company_id=a.company_id
      WHERE a.referral_agent_id=?""", (aid,)).fetchone()
    totals = c.execute("""SELECT
      COALESCE(SUM(CASE WHEN status='pending' THEN commission_amount_minor ELSE 0 END),0) pending,
      COALESCE(SUM(CASE WHEN status='available' THEN commission_amount_minor ELSE 0 END),0) available,
      COALESCE(SUM(CASE WHEN status='paid' THEN commission_amount_minor ELSE 0 END),0) paid
      FROM referral_commission_ledger WHERE referral_agent_id=?""", (aid,)).fetchone()
    history = [dict(r) for r in c.execute("""SELECT id,entry_type,payment_amount_minor,
      commission_amount_minor,currency,status,created_at FROM referral_commission_ledger
      WHERE referral_agent_id=? ORDER BY created_at DESC LIMIT 100""", (aid,)).fetchall()]
    payouts = [dict(r) for r in c.execute("""SELECT id,amount_minor,currency,status,
      payment_reference,created_at,paid_at FROM referral_payouts WHERE referral_agent_id=?
      ORDER BY created_at DESC LIMIT 100""", (aid,)).fetchall()]
    referred = [dict(r) for r in c.execute("""SELECT c.company_name,s.plan,s.status,x.attributed_at
      FROM customer_referral_attributions x JOIN companies c ON c.id=x.company_id
      JOIN subscriptions s ON s.company_id=x.company_id WHERE x.referral_agent_id=?
      ORDER BY x.attributed_at DESC LIMIT 100""", (aid,)).fetchall()]
    return {"agent": agent, "clients": int(counts["clients"]),
            "active_clients": int(counts["active_clients"]), "pending_minor": int(totals["pending"]),
            "available_minor": int(totals["available"]), "paid_minor": int(totals["paid"]),
            "referred_customers": referred, "commissions": history, "payouts": payouts}


def create_commission(payment_event_id: str, company_id: int, payment_amount_minor: int, currency: str) -> dict | None:
    conn = get_connection(); cursor = conn.cursor()
    attribution = cursor.execute("""SELECT a.*,r.status agent_status FROM customer_referral_attributions a
        JOIN referral_agents r ON r.id=a.referral_agent_id WHERE a.company_id=?""", (company_id,)).fetchone()
    if not attribution or attribution["agent_status"] != "approved": return None
    pricing = current_pricing()
    try:
        cursor.execute("""INSERT INTO referral_commission_ledger
          (referral_agent_id,company_id,payment_event_id,payment_amount_minor,
           commission_amount_minor,currency,pricing_rule_id,status,available_at)
          VALUES(?,?,?,?,?,?,?,'available',?)""", (
          attribution["referral_agent_id"], company_id, payment_event_id, payment_amount_minor,
          pricing["referral_commission_minor"], currency, pricing["id"],
          datetime.now(timezone.utc).isoformat()))
        conn.commit()
    except Exception:
        conn.rollback()
    row = get_connection().cursor().execute(
        "SELECT * FROM referral_commission_ledger WHERE payment_event_id=? AND entry_type='commission'",
        (payment_event_id,)).fetchone()
    return dict(row) if row else None


def reverse_commission(refund_event_id: str, original_event_id: str) -> dict | None:
    conn = get_connection(); cursor = conn.cursor()
    original = cursor.execute("""SELECT * FROM referral_commission_ledger
        WHERE payment_event_id=? AND entry_type='commission'""", (original_event_id,)).fetchone()
    if not original: return None
    try:
        cursor.execute("""INSERT INTO referral_commission_ledger
          (referral_agent_id,company_id,payment_event_id,entry_type,related_entry_id,
           payment_amount_minor,commission_amount_minor,currency,pricing_rule_id,status,available_at)
          VALUES(?,?,?,'reversal',?,?,?,?,?,'available',?)""", (
          original["referral_agent_id"], original["company_id"], refund_event_id, original["id"],
          -abs(original["payment_amount_minor"]), -abs(original["commission_amount_minor"]),
          original["currency"], original["pricing_rule_id"], datetime.now(timezone.utc).isoformat()))
        conn.commit()
    except Exception:
        conn.rollback()
    row = get_connection().cursor().execute(
        "SELECT * FROM referral_commission_ledger WHERE payment_event_id=? AND entry_type='reversal'",
        (refund_event_id,)).fetchone()
    return dict(row) if row else None


def list_attributions() -> list[dict]:
    rows = get_connection().cursor().execute("""SELECT x.*,c.company_name,u.email agent_email
      FROM customer_referral_attributions x JOIN companies c ON c.id=x.company_id
      JOIN referral_agents a ON a.id=x.referral_agent_id JOIN users u ON u.id=a.user_id
      ORDER BY x.attributed_at DESC""").fetchall()
    return [dict(r) for r in rows]


def correct_attribution(company_id: int, agent_id: int, reason: str) -> dict | None:
    conn = get_connection(); cursor = conn.cursor(); agent = cursor.execute(
        "SELECT * FROM referral_agents WHERE id=? AND status='approved'", (agent_id,)).fetchone()
    if not agent: return None
    cursor.execute("""UPDATE customer_referral_attributions SET referral_agent_id=?,
      referral_code_snapshot=?,corrected_at=?,correction_reason=? WHERE company_id=?""",
      (agent_id, agent["referral_code"], datetime.now(timezone.utc).isoformat(), reason[:1000], company_id))
    conn.commit()
    row = cursor.execute("SELECT * FROM customer_referral_attributions WHERE company_id=?", (company_id,)).fetchone()
    return dict(row) if row else None


def list_commissions() -> list[dict]:
    return [dict(r) for r in get_connection().cursor().execute("""SELECT l.*,u.email agent_email,c.company_name
      FROM referral_commission_ledger l JOIN referral_agents a ON a.id=l.referral_agent_id
      JOIN users u ON u.id=a.user_id JOIN companies c ON c.id=l.company_id
      ORDER BY l.created_at DESC LIMIT 500""").fetchall()]


def list_payouts() -> list[dict]:
    return [dict(r) for r in get_connection().cursor().execute("""SELECT p.*,u.email agent_email
      FROM referral_payouts p JOIN referral_agents a ON a.id=p.referral_agent_id
      JOIN users u ON u.id=a.user_id ORDER BY p.created_at DESC""").fetchall()]


def create_payout(agent_id: int, commission_ids: list[int]) -> dict:
    if not commission_ids: raise ValueError("Select at least one available commission.")
    conn = get_connection(); cursor = conn.cursor(); placeholders = ",".join("?" for _ in commission_ids)
    rows = cursor.execute(f"SELECT * FROM referral_commission_ledger WHERE referral_agent_id=? AND status='available' AND id IN ({placeholders})", [agent_id, *commission_ids]).fetchall()
    if len(rows) != len(set(commission_ids)): raise ValueError("One or more commissions are unavailable.")
    currencies = {r["currency"] for r in rows}
    if len(currencies) != 1: raise ValueError("A payout cannot mix currencies.")
    amount = sum(int(r["commission_amount_minor"]) for r in rows)
    if amount <= 0: raise ValueError("Payout amount must be positive.")
    try:
        cursor.execute("INSERT INTO referral_payouts(referral_agent_id,amount_minor,currency) VALUES(?,?,?)", (agent_id, amount, rows[0]["currency"]))
        payout_id = cursor.lastrowid
        for row in rows:
            cursor.execute("INSERT INTO referral_payout_items(payout_id,commission_entry_id) VALUES(?,?)", (payout_id,row["id"]))
            cursor.execute("UPDATE referral_commission_ledger SET status='pending_payout' WHERE id=?", (row["id"],))
        conn.commit()
    except Exception: conn.rollback(); raise
    return dict(cursor.execute("SELECT * FROM referral_payouts WHERE id=?", (payout_id,)).fetchone())


def update_payout(payout_id: int, status: str, reference: str = "") -> dict | None:
    conn=get_connection(); cursor=conn.cursor(); now=datetime.now(timezone.utc).isoformat()
    cursor.execute("""UPDATE referral_payouts SET status=?,payment_reference=?,
      approved_at=CASE WHEN ? IN ('approved','paid') THEN COALESCE(approved_at,?) ELSE approved_at END,
      paid_at=CASE WHEN ?='paid' THEN ? ELSE paid_at END WHERE id=?""",
      (status,reference[:200],status,now,status,now,payout_id))
    if cursor.rowcount:
        commission_status = "paid" if status == "paid" else ("available" if status == "cancelled" else "pending_payout")
        cursor.execute("""UPDATE referral_commission_ledger SET status=?,paid_at=CASE WHEN ?='paid' THEN ? ELSE paid_at END
          WHERE id IN (SELECT commission_entry_id FROM referral_payout_items WHERE payout_id=?)""",
          (commission_status,status,now,payout_id))
    conn.commit(); row=cursor.execute("SELECT * FROM referral_payouts WHERE id=?",(payout_id,)).fetchone()
    return dict(row) if row else None

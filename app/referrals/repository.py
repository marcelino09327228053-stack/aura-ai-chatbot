"""Persistence operations for human referral agents and commissions."""
import secrets
from datetime import datetime, timedelta, timezone

from app.infrastructure.database import get_connection
from app.cloud.security import decrypt_value, encrypt_value

# Kept available to the service without opening a second persistence abstraction.


def current_pricing() -> dict:
    row = get_connection().cursor().execute(
        "SELECT * FROM platform_pricing_rules ORDER BY effective_at DESC, id DESC LIMIT 1"
    ).fetchone()
    return dict(row)


def create_pricing_rule(values: dict, created_by: str = "owner") -> dict:
    conn = get_connection(); cursor = conn.cursor(); previous=current_pricing()
    cursor.execute("""INSERT INTO platform_pricing_rules
        (monthly_platform_price_minor,initial_ai_credit_minor,minimum_ai_topup_minor,
         referral_commission_minor,ai_usage_markup_bps,currency,effective_at,created_by,
         commission_hold_days,minimum_payout_minor,payout_schedule)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (
        values["monthly_platform_price_minor"], values["initial_ai_credit_minor"],
        values["minimum_ai_topup_minor"], values["referral_commission_minor"],
        values["ai_usage_markup_bps"], values.get("currency", "PHP"),
        datetime.now(timezone.utc).isoformat(), created_by,
        values.get("commission_hold_days",previous.get("commission_hold_days",7)),
        values.get("minimum_payout_minor",previous.get("minimum_payout_minor",100000)),
        values.get("payout_schedule",previous.get("payout_schedule","on_request")),
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
            cursor.execute("INSERT INTO referral_agents(user_id,referral_code,status) VALUES(?,?,'draft')", (user_id, code))
            conn.commit(); return get_agent_by_user(user_id), True
        except Exception:
            conn.rollback()
    raise RuntimeError("Unable to generate a unique referral code.")


def save_application(user_id: int, values: dict, document: dict) -> dict:
    agent, _ = apply_for_agent(user_id)
    if agent["status"] == "approved": raise ValueError("Active agents cannot replace an approved application.")
    conn=get_connection(); cursor=conn.cursor(); now=datetime.now(timezone.utc).isoformat()
    cursor.execute("""UPDATE referral_agents SET status='pending_verification',full_name=?,
      application_email=?,mobile_number=?,address_location=?,id_type=?,id_reference=?,
      id_storage_name=?,id_original_name=?,id_content_type=?,id_sha256=?,payout_method=?,
      encrypted_account_holder=?,encrypted_account_number=?,encrypted_bank_name=?,
      submitted_at=?,reviewed_at=NULL,admin_notes='' WHERE user_id=?""", (
      values["full_name"],values["email"],values["mobile_number"],values["address_location"],
      values["id_type"],values.get("id_reference","")[:120],document["storage_name"],
      document["original_name"],document["content_type"],document["sha256"],values["payout_method"],
      encrypt_value(values["account_holder_name"]),encrypt_value(values["account_number"]),
      encrypt_value(values.get("bank_name", "")),now,user_id))
    conn.commit(); notify(user_id,"Application submitted","Your Marketing Agent application is pending verification.")
    return get_agent_by_user(user_id)


def application_for_owner(agent_id: int) -> dict | None:
    agent=get_agent(agent_id)
    if not agent:return None
    result=dict(agent)
    result["account_holder_name"]=decrypt_value(agent["encrypted_account_holder"]) if agent["encrypted_account_holder"] else ""
    result["account_number"]=decrypt_value(agent["encrypted_account_number"]) if agent["encrypted_account_number"] else ""
    result["bank_name"]=decrypt_value(agent["encrypted_bank_name"]) if agent["encrypted_bank_name"] else ""
    result.pop("encrypted_account_holder",None);result.pop("encrypted_account_number",None);result.pop("encrypted_bank_name",None)
    return result


def update_profile(user_id: int, full_name: str, mobile_number: str, address_location: str,
                   profile_bio: str, photo: dict | None = None) -> dict | None:
    agent = get_agent_by_user(user_id)
    if not agent:
        return None
    conn = get_connection()
    if photo:
        conn.cursor().execute("""UPDATE referral_agents SET full_name=?,mobile_number=?,address_location=?,
            profile_bio=?,profile_storage_name=?,profile_content_type=? WHERE user_id=?""",
            (full_name, mobile_number, address_location, profile_bio,
             photo["storage_name"], photo["content_type"], user_id))
    else:
        conn.cursor().execute("""UPDATE referral_agents SET full_name=?,mobile_number=?,address_location=?,
            profile_bio=? WHERE user_id=?""",
            (full_name, mobile_number, address_location, profile_bio, user_id))
    conn.commit()
    return get_agent_by_user(user_id)


def set_agent_status(agent_id: int, status: str, notes: str = "") -> dict | None:
    conn = get_connection(); now = datetime.now(timezone.utc).isoformat()
    conn.cursor().execute("""UPDATE referral_agents SET status=?, payout_eligible=?, admin_notes=?,
        approved_at=CASE WHEN ?='approved' THEN COALESCE(approved_at,?) ELSE approved_at END,
        suspended_at=CASE WHEN ?='suspended' THEN ? ELSE NULL END, reviewed_at=? WHERE id=?""",
        (status, 1 if status == "approved" else 0, notes[:1000], status, now, status, now, now, agent_id))
    conn.commit()
    row = conn.cursor().execute("SELECT * FROM referral_agents WHERE id=?", (agent_id,)).fetchone()
    result=dict(row) if row else None
    if result:
        titles={"approved":"Application approved","rejected":"Application rejected","suspended":"Account suspended"}
        if status in titles: notify(result["user_id"],titles[status],"Your Marketing Agent account status has been updated.")
    return result


def notify(user_id: int, title: str, message: str) -> None:
    conn=get_connection();conn.cursor().execute("INSERT INTO referral_notifications(user_id,title,message) VALUES(?,?,?)",(user_id,title[:120],message[:500]));conn.commit()


def notifications(user_id: int) -> list[dict]:
    return [dict(r) for r in get_connection().cursor().execute("SELECT * FROM referral_notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 50",(user_id,)).fetchall()]


def refresh_available_commissions(agent_id: int | None = None) -> int:
    conn=get_connection();cursor=conn.cursor();now=datetime.now(timezone.utc).isoformat()
    sql="UPDATE referral_commission_ledger SET status='available' WHERE status='pending' AND available_at<=?"
    params=[now]
    if agent_id is not None:sql+=" AND referral_agent_id=?";params.append(agent_id)
    cursor.execute(sql,params);changed=cursor.rowcount;conn.commit()
    if changed and agent_id is not None:
        agent=get_agent(agent_id)
        if agent:notify(agent["user_id"],"Commission available","One or more commissions are now available for payout.")
    return changed


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
    created=False
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
    result=dict(row) if row else None
    if created:
        owner=get_agent(agent_id)
        if owner:notify(owner["user_id"],"New referred client","A new customer was successfully attributed to your referral link.")
    return result, created


def dashboard_for_user(user_id: int) -> dict | None:
    agent = get_agent_by_user(user_id)
    if not agent: return None
    refresh_available_commissions(agent["id"])
    c = get_connection().cursor(); aid = agent["id"]
    counts = c.execute("""SELECT COUNT(*) clients,
      COALESCE(SUM(CASE WHEN s.status='active' AND s.plan!='free' THEN 1 ELSE 0 END),0) active_clients
      FROM customer_referral_attributions a JOIN subscriptions s ON s.company_id=a.company_id
      WHERE a.referral_agent_id=?""", (aid,)).fetchone()
    totals = c.execute("""SELECT
      COALESCE(SUM(CASE WHEN status='pending' THEN commission_amount_minor ELSE 0 END),0) pending,
      COALESCE(SUM(CASE WHEN status='available' THEN commission_amount_minor ELSE 0 END),0) available,
      COALESCE(SUM(CASE WHEN status='payout_requested' THEN commission_amount_minor ELSE 0 END),0) requested,
      COALESCE(SUM(CASE WHEN status='paid' THEN commission_amount_minor ELSE 0 END),0) paid
      FROM referral_commission_ledger WHERE referral_agent_id=?""", (aid,)).fetchone()
    history = [dict(r) for r in c.execute("""SELECT id,entry_type,payment_amount_minor,
      commission_amount_minor,currency,status,created_at FROM referral_commission_ledger
      WHERE referral_agent_id=? ORDER BY created_at DESC LIMIT 100""", (aid,)).fetchall()]
    payouts = [dict(r) for r in c.execute("""SELECT id,amount_minor,currency,status,
      payment_reference,created_at,paid_at FROM referral_payouts WHERE referral_agent_id=?
      ORDER BY created_at DESC LIMIT 100""", (aid,)).fetchall()]
    referred = [dict(r) for r in c.execute("""SELECT c.company_name,s.plan,s.status,x.attributed_at,
      (SELECT MAX(p.processed_at) FROM payment_webhook_events p WHERE p.company_id=x.company_id
       AND p.status='completed' AND p.event_type IN ('initial_subscription','subscription_renewal')) last_qualifying_payment,
      (SELECT l.status FROM referral_commission_ledger l WHERE l.company_id=x.company_id
       AND l.referral_agent_id=x.referral_agent_id ORDER BY l.created_at DESC,l.id DESC LIMIT 1) latest_commission_status,
      COALESCE((SELECT SUM(l.commission_amount_minor) FROM referral_commission_ledger l
       WHERE l.company_id=x.company_id AND l.referral_agent_id=x.referral_agent_id),0) total_commission_minor
      FROM customer_referral_attributions x JOIN companies c ON c.id=x.company_id
      JOIN subscriptions s ON s.company_id=x.company_id WHERE x.referral_agent_id=?
      ORDER BY x.attributed_at DESC LIMIT 100""", (aid,)).fetchall()]
    return {"agent": agent, "clients": int(counts["clients"]),
            "active_clients": int(counts["active_clients"]), "pending_minor": int(totals["pending"]),
            "available_minor": int(totals["available"]), "payout_requested_minor": int(totals["requested"]),
            "paid_minor": int(totals["paid"]),
            "referred_customers": referred, "commissions": history, "payouts": payouts,
            "notifications": notifications(user_id), "pricing": current_pricing()}


def create_commission(payment_event_id: str, company_id: int, payment_amount_minor: int, currency: str) -> dict | None:
    conn = get_connection(); cursor = conn.cursor()
    attribution = cursor.execute("""SELECT a.*,r.status agent_status FROM customer_referral_attributions a
        JOIN referral_agents r ON r.id=a.referral_agent_id WHERE a.company_id=?""", (company_id,)).fetchone()
    if not attribution or attribution["agent_status"] != "approved": return None
    pricing = current_pricing()
    available_at=(datetime.now(timezone.utc)+timedelta(days=max(0,int(pricing["commission_hold_days"])))).isoformat()
    created=False
    try:
        cursor.execute("""INSERT INTO referral_commission_ledger
          (referral_agent_id,company_id,payment_event_id,payment_amount_minor,
           commission_amount_minor,currency,pricing_rule_id,status,available_at)
          VALUES(?,?,?,?,?,?,?,'pending',?)""", (
          attribution["referral_agent_id"], company_id, payment_event_id, payment_amount_minor,
          pricing["referral_commission_minor"], currency, pricing["id"],
          available_at))
        conn.commit();created=True
    except Exception:
        conn.rollback()
    row = get_connection().cursor().execute(
        "SELECT * FROM referral_commission_ledger WHERE payment_event_id=? AND entry_type='commission'",
        (payment_event_id,)).fetchone()
    result=dict(row) if row else None
    if result and created:
        agent=get_agent(result["referral_agent_id"])
        if agent:notify(agent["user_id"],"New commission pending","A referred customer made a qualifying subscription payment.")
    return result


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
    result=dict(row) if row else None
    if result:
        conn=get_connection();cursor=conn.cursor()
        cursor.execute("UPDATE referral_commission_ledger SET status='reversed' WHERE id IN (?,?)",(result["id"],original["id"]));conn.commit()
        result=dict(conn.cursor().execute("SELECT * FROM referral_commission_ledger WHERE id=?",(result["id"],)).fetchone())
    return result


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
    rows=[dict(r) for r in get_connection().cursor().execute("""SELECT p.*,u.email agent_email
      FROM referral_payouts p JOIN referral_agents a ON a.id=p.referral_agent_id
      JOIN users u ON u.id=a.user_id ORDER BY p.created_at DESC""").fetchall()]
    for row in rows:
        row["destination_account"]=decrypt_value(row.pop("encrypted_destination_account")) if row.get("encrypted_destination_account") else ""
        row["account_holder_name"]=decrypt_value(row.pop("encrypted_account_holder_snapshot")) if row.get("encrypted_account_holder_snapshot") else ""
        row["bank_name"]=decrypt_value(row.pop("encrypted_bank_name_snapshot")) if row.get("encrypted_bank_name_snapshot") else ""
    return rows


def marketing_analytics() -> dict:
    refresh_available_commissions();c=get_connection().cursor()
    scalar=lambda sql: int(c.execute(sql).fetchone()[0] or 0)
    return {
      "total_agents":scalar("SELECT COUNT(*) FROM referral_agents"),
      "active_agents":scalar("SELECT COUNT(*) FROM referral_agents WHERE status='approved'"),
      "pending_applications":scalar("SELECT COUNT(*) FROM referral_agents WHERE status='pending_verification'"),
      "customers_acquired":scalar("SELECT COUNT(*) FROM customer_referral_attributions"),
      "active_referred_customers":scalar("""SELECT COUNT(*) FROM customer_referral_attributions a JOIN subscriptions s ON s.company_id=a.company_id WHERE s.status='active' AND s.plan!='free'"""),
      "agent_subscription_revenue_minor":scalar("""SELECT COALESCE(SUM(amount_minor),0) FROM payment_webhook_events p WHERE p.status='completed' AND p.event_type IN ('initial_subscription','subscription_renewal') AND EXISTS(SELECT 1 FROM customer_referral_attributions a WHERE a.company_id=p.company_id)"""),
      "pending_commissions_minor":scalar("SELECT COALESCE(SUM(commission_amount_minor),0) FROM referral_commission_ledger WHERE status='pending'"),
      "available_commissions_minor":scalar("SELECT COALESCE(SUM(commission_amount_minor),0) FROM referral_commission_ledger WHERE status='available'"),
      "requested_payouts_minor":scalar("SELECT COALESCE(SUM(amount_minor),0) FROM referral_payouts WHERE status IN ('requested','approved')"),
      "commissions_paid_minor":scalar("SELECT COALESCE(SUM(amount_minor),0) FROM referral_payouts WHERE status='paid'"),
    }


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


def request_payout(user_id: int) -> dict:
    agent=get_agent_by_user(user_id)
    if not agent or agent["status"]!="approved" or not agent["payout_eligible"]:raise ValueError("An approved payout-eligible agent account is required.")
    if not agent.get("payout_method") or not agent.get("encrypted_account_number") or not agent.get("encrypted_account_holder"):
        raise ValueError("Complete payout information is required.")
    refresh_available_commissions(agent["id"]);pricing=current_pricing();conn=get_connection();cursor=conn.cursor()
    rows=cursor.execute("SELECT id,commission_amount_minor,currency FROM referral_commission_ledger WHERE referral_agent_id=? AND status='available' ORDER BY created_at",(agent["id"],)).fetchall()
    amount=sum(int(r["commission_amount_minor"]) for r in rows)
    if amount<int(pricing["minimum_payout_minor"]):raise ValueError("Available earnings have not reached the minimum payout.")
    if not rows:raise ValueError("No available commissions.")
    account=decrypt_value(agent["encrypted_account_number"]) if agent["encrypted_account_number"] else ""
    masked=("•"*max(0,len(account)-4)+account[-4:]) if account else ""
    now=datetime.now(timezone.utc).isoformat()
    try:
        cursor.execute("""INSERT INTO referral_payouts(referral_agent_id,amount_minor,currency,status,
          payout_method_snapshot,destination_masked,encrypted_destination_account,
          encrypted_account_holder_snapshot,encrypted_bank_name_snapshot,requested_at,requested_by_user_id)
          VALUES(?,?,?,'requested',?,?,?,?,?,?,?)""",(agent["id"],amount,rows[0]["currency"],agent["payout_method"],masked,
          encrypt_value(account),agent["encrypted_account_holder"],agent["encrypted_bank_name"],now,user_id))
        payout_id=cursor.lastrowid
        for row in rows:
            cursor.execute("INSERT INTO referral_payout_items(payout_id,commission_entry_id) VALUES(?,?)",(payout_id,row["id"]))
            cursor.execute("UPDATE referral_commission_ledger SET status='payout_requested' WHERE id=? AND status='available'",(row["id"],))
            if cursor.rowcount!=1:raise ValueError("A commission was already included in another payout.")
        conn.commit()
    except Exception:conn.rollback();raise
    notify(user_id,"Payout requested","Your manual payout request was submitted for Owner review.")
    return dict(cursor.execute("SELECT * FROM referral_payouts WHERE id=?",(payout_id,)).fetchone())


def update_payout(payout_id: int, status: str, reference: str = "") -> dict | None:
    conn=get_connection(); cursor=conn.cursor(); now=datetime.now(timezone.utc).isoformat()
    if status=="paid":
        invalid=cursor.execute("""SELECT COUNT(*) FROM referral_payout_items i
          JOIN referral_commission_ledger l ON l.id=i.commission_entry_id
          WHERE i.payout_id=? AND l.status!='payout_requested'""",(payout_id,)).fetchone()[0]
        if invalid:raise ValueError("Payout contains a reversed or unavailable commission.")
    if status=="paid":
        invalid=cursor.execute("""SELECT COUNT(*) FROM referral_payout_items i JOIN referral_commission_ledger l ON l.id=i.commission_entry_id WHERE i.payout_id=? AND l.status!='payout_requested'""",(payout_id,)).fetchone()[0]
        if invalid:raise ValueError("Payout contains a reversed or unavailable commission.")
    cursor.execute("""UPDATE referral_payouts SET status=?,payment_reference=?,
      approved_at=CASE WHEN ? IN ('approved','paid') THEN COALESCE(approved_at,?) ELSE approved_at END,
      paid_at=CASE WHEN ?='paid' THEN ? ELSE paid_at END WHERE id=?""",
      (status,reference[:200],status,now,status,now,payout_id))
    if cursor.rowcount:
        commission_status = "paid" if status == "paid" else ("available" if status == "cancelled" else "payout_requested")
        cursor.execute("""UPDATE referral_commission_ledger SET status=?,paid_at=CASE WHEN ?='paid' THEN ? ELSE paid_at END
          WHERE id IN (SELECT commission_entry_id FROM referral_payout_items WHERE payout_id=?)""",
          (commission_status,status,now,payout_id))
    conn.commit(); row=cursor.execute("SELECT * FROM referral_payouts WHERE id=?",(payout_id,)).fetchone()
    result=dict(row) if row else None
    if result:
        agent=get_agent(result["referral_agent_id"])
        if agent and status in {"approved","paid"}:notify(agent["user_id"],f"Payout {status}","Your payout status has been updated.")
    return result

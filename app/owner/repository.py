"""Owner-only operational data and encrypted provider credential storage."""
from app.cloud.security import decrypt_value, encrypt_value
from app.infrastructure.database import get_connection

def init_owner_schema():
    conn=get_connection(); c=conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS owner_provider_credentials (
      provider TEXT PRIMARY KEY, encrypted_key TEXT NOT NULL, key_suffix TEXT NOT NULL,
      updated_at TEXT NOT NULL DEFAULT (datetime('now')))""")
    c.execute("""CREATE TABLE IF NOT EXISTS owner_agent_controls (
      agent_type TEXT PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 1,
      updated_at TEXT NOT NULL DEFAULT (datetime('now')))"""); conn.commit()

def save_provider_key(provider: str,key: str):
    conn=get_connection(); conn.cursor().execute("""INSERT INTO owner_provider_credentials(provider,encrypted_key,key_suffix)
      VALUES(?,?,?) ON CONFLICT(provider) DO UPDATE SET encrypted_key=excluded.encrypted_key,key_suffix=excluded.key_suffix,updated_at=datetime('now')""",
      (provider,encrypt_value(key),key[-4:])); conn.commit()

def get_provider_key(provider: str) -> str | None:
    row=get_connection().cursor().execute("SELECT encrypted_key FROM owner_provider_credentials WHERE provider=?",(provider,)).fetchone()
    return decrypt_value(row["encrypted_key"]) if row else None

def list_providers():
    return [dict(row) for row in get_connection().cursor().execute("SELECT provider,key_suffix,updated_at FROM owner_provider_credentials ORDER BY provider").fetchall()]

def delete_provider_key(provider:str):
    conn=get_connection(); conn.cursor().execute("DELETE FROM owner_provider_credentials WHERE provider=?",(provider,)); conn.commit()

def overview():
    c=get_connection().cursor()
    scalar=lambda sql: c.execute(sql).fetchone()[0]
    return {"customers":scalar("SELECT COUNT(*) FROM companies"),"users":scalar("SELECT COUNT(*) FROM users"),
      "active_subscribers":scalar("SELECT COUNT(*) FROM subscriptions WHERE status='active' AND plan!='free'"),
      "free_accounts":scalar("SELECT COUNT(*) FROM subscriptions WHERE plan='free'"),
      "ai_requests":scalar("SELECT COUNT(*) FROM ai_gateway_requests"),
      "ai_cost_usd":float(scalar("SELECT COALESCE(SUM(provider_cost_usd),0) FROM ai_gateway_requests WHERE status='success'") or 0)}

def subscribers():
    rows=get_connection().cursor().execute("""SELECT c.id,c.company_name,s.plan,s.status,s.billing_cycle_end,
      s.monthly_ai_allowance_minor,s.ai_usage_consumed_minor FROM companies c JOIN subscriptions s ON s.company_id=c.id ORDER BY c.id DESC LIMIT 500""").fetchall()
    return [dict(row) for row in rows]

def set_agent(agent_type:str,enabled:bool):
    conn=get_connection(); conn.cursor().execute("""INSERT INTO owner_agent_controls(agent_type,enabled) VALUES(?,?)
      ON CONFLICT(agent_type) DO UPDATE SET enabled=excluded.enabled,updated_at=datetime('now')""",(agent_type,1 if enabled else 0)); conn.commit()

def agent_enabled(agent_type:str):
    row=get_connection().cursor().execute("SELECT enabled FROM owner_agent_controls WHERE agent_type=?",(agent_type,)).fetchone()
    return None if not row else bool(row["enabled"])

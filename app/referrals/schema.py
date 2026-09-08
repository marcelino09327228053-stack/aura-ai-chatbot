"""Database schema for referral agents, attribution, pricing and payouts."""


def init_referral_schema(cursor, conn) -> None:
    from app.core.config import REFERRAL_PRICING_DEFAULTS
    cursor.execute("""CREATE TABLE IF NOT EXISTS platform_pricing_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        monthly_platform_price_minor INTEGER NOT NULL,
        initial_ai_credit_minor INTEGER NOT NULL,
        minimum_ai_topup_minor INTEGER NOT NULL,
        referral_commission_minor INTEGER NOT NULL,
        ai_usage_markup_bps INTEGER NOT NULL DEFAULT 0,
        currency TEXT NOT NULL DEFAULT 'PHP',
        effective_at TEXT NOT NULL DEFAULT (datetime('now')),
        created_by TEXT NOT NULL DEFAULT 'system'
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS referral_agents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        referral_code TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL DEFAULT 'pending',
        payout_eligible INTEGER NOT NULL DEFAULT 0,
        admin_notes TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        approved_at TEXT,
        suspended_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS referral_clicks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referral_agent_id INTEGER NOT NULL,
        click_token TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (referral_agent_id) REFERENCES referral_agents(id)
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS customer_referral_attributions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL UNIQUE,
        customer_user_id INTEGER NOT NULL,
        referral_agent_id INTEGER NOT NULL,
        referral_code_snapshot TEXT NOT NULL,
        attributed_at TEXT NOT NULL DEFAULT (datetime('now')),
        corrected_at TEXT,
        correction_reason TEXT NOT NULL DEFAULT '',
        FOREIGN KEY (company_id) REFERENCES companies(id),
        FOREIGN KEY (customer_user_id) REFERENCES users(id),
        FOREIGN KEY (referral_agent_id) REFERENCES referral_agents(id)
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS referral_commission_ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referral_agent_id INTEGER NOT NULL,
        company_id INTEGER NOT NULL,
        payment_event_id TEXT NOT NULL,
        entry_type TEXT NOT NULL DEFAULT 'commission',
        related_entry_id INTEGER,
        payment_amount_minor INTEGER NOT NULL,
        commission_amount_minor INTEGER NOT NULL,
        currency TEXT NOT NULL DEFAULT 'PHP',
        pricing_rule_id INTEGER,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        available_at TEXT,
        paid_at TEXT,
        UNIQUE(payment_event_id, entry_type),
        FOREIGN KEY (referral_agent_id) REFERENCES referral_agents(id),
        FOREIGN KEY (company_id) REFERENCES companies(id),
        FOREIGN KEY (pricing_rule_id) REFERENCES platform_pricing_rules(id)
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS referral_payouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referral_agent_id INTEGER NOT NULL,
        amount_minor INTEGER NOT NULL,
        currency TEXT NOT NULL DEFAULT 'PHP',
        status TEXT NOT NULL DEFAULT 'pending',
        payment_reference TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        approved_at TEXT,
        paid_at TEXT,
        FOREIGN KEY (referral_agent_id) REFERENCES referral_agents(id)
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS referral_payout_items (
        payout_id INTEGER NOT NULL,
        commission_entry_id INTEGER NOT NULL UNIQUE,
        PRIMARY KEY (payout_id, commission_entry_id),
        FOREIGN KEY (payout_id) REFERENCES referral_payouts(id),
        FOREIGN KEY (commission_entry_id) REFERENCES referral_commission_ledger(id)
    )""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_referral_commission_agent_created
        ON referral_commission_ledger(referral_agent_id, created_at)""")
    cursor.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_referral_attribution_customer
        ON customer_referral_attributions(customer_user_id)""")
    cursor.execute("SELECT id FROM platform_pricing_rules ORDER BY effective_at DESC, id DESC LIMIT 1")
    if cursor.fetchone() is None:
        defaults = REFERRAL_PRICING_DEFAULTS
        cursor.execute("""INSERT INTO platform_pricing_rules
            (monthly_platform_price_minor, initial_ai_credit_minor,
             minimum_ai_topup_minor, referral_commission_minor,
             ai_usage_markup_bps, currency, created_by)
            VALUES (?,?,?,?,?,?,?)""", (
            int(defaults["monthly_platform_price_minor"]), int(defaults["initial_ai_credit_minor"]),
            int(defaults["minimum_ai_topup_minor"]), int(defaults["referral_commission_minor"]),
            int(defaults.get("ai_usage_markup_bps", 0)), str(defaults.get("currency", "PHP")).upper(),
            "system-default",
        ))
    conn.commit()

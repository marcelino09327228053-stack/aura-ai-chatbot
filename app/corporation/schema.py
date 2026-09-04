"""Corporation platform database schema."""


def init_corporation_schema(cursor, conn) -> None:
    # ── Executive decisions ───────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS corp_decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        agent_role TEXT NOT NULL,
        decision_type TEXT NOT NULL,
        title TEXT NOT NULL,
        analysis TEXT NOT NULL DEFAULT '',
        recommendation TEXT NOT NULL DEFAULT '',
        confidence REAL NOT NULL DEFAULT 0.7,
        status TEXT NOT NULL DEFAULT 'pending',
        approved_by INTEGER,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    # ── Negotiations ──────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS corp_negotiations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        negotiation_type TEXT NOT NULL,
        counterparty TEXT NOT NULL DEFAULT '',
        subject TEXT NOT NULL DEFAULT '',
        our_position TEXT NOT NULL DEFAULT '{}',
        their_position TEXT NOT NULL DEFAULT '{}',
        proposed_terms TEXT NOT NULL DEFAULT '{}',
        status TEXT NOT NULL DEFAULT 'open',
        outcome TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    # ── Investments ───────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS corp_investments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        investment_type TEXT NOT NULL,
        name TEXT NOT NULL,
        amount REAL NOT NULL DEFAULT 0,
        expected_return REAL NOT NULL DEFAULT 0,
        roi_pct REAL NOT NULL DEFAULT 0,
        payback_months REAL NOT NULL DEFAULT 0,
        risk_level TEXT NOT NULL DEFAULT 'medium',
        status TEXT NOT NULL DEFAULT 'proposed',
        notes TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    # ── Risk register ─────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS corp_risks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        risk_type TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        likelihood TEXT NOT NULL DEFAULT 'medium',
        impact TEXT NOT NULL DEFAULT 'medium',
        risk_score INTEGER NOT NULL DEFAULT 0,
        mitigation TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'open',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    # ── Corporation audit ─────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS corp_audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        agent_role TEXT NOT NULL DEFAULT 'system',
        action TEXT NOT NULL,
        details TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    conn.commit()

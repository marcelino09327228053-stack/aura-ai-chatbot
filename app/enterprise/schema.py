"""Enterprise platform database schema."""


def init_enterprise_schema(cursor, conn) -> None:
    # ── Strategy & Goals ──────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS enterprise_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        category TEXT NOT NULL DEFAULT 'growth',
        target_value REAL NOT NULL DEFAULT 0,
        current_value REAL NOT NULL DEFAULT 0,
        unit TEXT NOT NULL DEFAULT '',
        deadline TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'active',
        priority TEXT NOT NULL DEFAULT 'medium',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS enterprise_kpis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'financial',
        value REAL NOT NULL DEFAULT 0,
        target REAL NOT NULL DEFAULT 0,
        unit TEXT NOT NULL DEFAULT '',
        period TEXT NOT NULL DEFAULT 'monthly',
        trend TEXT NOT NULL DEFAULT 'stable',
        recorded_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS enterprise_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        plan_type TEXT NOT NULL DEFAULT 'annual',
        description TEXT NOT NULL DEFAULT '',
        start_date TEXT NOT NULL DEFAULT '',
        end_date TEXT NOT NULL DEFAULT '',
        budget REAL NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'draft',
        milestones TEXT NOT NULL DEFAULT '[]',
        created_by INTEGER,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    # ── Forecasting ───────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS enterprise_forecasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        forecast_type TEXT NOT NULL,
        period TEXT NOT NULL DEFAULT 'monthly',
        periods_ahead INTEGER NOT NULL DEFAULT 3,
        value REAL NOT NULL DEFAULT 0,
        confidence REAL NOT NULL DEFAULT 0.7,
        assumptions TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    # ── Governance ────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS enterprise_policies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'general',
        content TEXT NOT NULL DEFAULT '',
        version TEXT NOT NULL DEFAULT '1.0',
        status TEXT NOT NULL DEFAULT 'active',
        approved_by INTEGER,
        effective_date TEXT NOT NULL DEFAULT (date('now')),
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS enterprise_approvals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        request_type TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        requested_by INTEGER NOT NULL,
        assigned_to INTEGER,
        status TEXT NOT NULL DEFAULT 'pending',
        decision_note TEXT NOT NULL DEFAULT '',
        amount REAL NOT NULL DEFAULT 0,
        decided_at TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    # ── Compliance ────────────────────────────────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS enterprise_compliance_checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        check_type TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        result TEXT NOT NULL DEFAULT '{}',
        passed INTEGER NOT NULL DEFAULT 0,
        notes TEXT NOT NULL DEFAULT '',
        checked_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS enterprise_audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        user_id INTEGER,
        action TEXT NOT NULL,
        resource_type TEXT NOT NULL DEFAULT '',
        resource_id INTEGER,
        details TEXT NOT NULL DEFAULT '',
        ip_address TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    conn.commit()

"""Civilization layer database schema."""


def init_civilization_schema(cursor, conn) -> None:
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS civ_constitutions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        articles TEXT NOT NULL DEFAULT '[]',
        version TEXT NOT NULL DEFAULT '1.0',
        ratified INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS civ_votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        options TEXT NOT NULL DEFAULT '[]',
        results TEXT NOT NULL DEFAULT '{}',
        status TEXT NOT NULL DEFAULT 'open',
        created_by INTEGER,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        closed_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS civ_policies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'general',
        content TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS civ_decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        decision_type TEXT NOT NULL DEFAULT 'policy',
        outcome TEXT NOT NULL DEFAULT '',
        vote_id INTEGER,
        status TEXT NOT NULL DEFAULT 'recorded',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS civ_training (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        employee_key TEXT NOT NULL,
        course_title TEXT NOT NULL,
        course_type TEXT NOT NULL DEFAULT 'training',
        progress REAL NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'in_progress',
        certified INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        completed_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS civ_skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        employee_key TEXT NOT NULL,
        skill_name TEXT NOT NULL,
        level REAL NOT NULL DEFAULT 1,
        category TEXT NOT NULL DEFAULT 'general',
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS civ_certifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        employee_key TEXT NOT NULL,
        cert_name TEXT NOT NULL,
        issuer TEXT NOT NULL DEFAULT 'Aura Academy',
        expires_at TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS civ_economy_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        account_key TEXT NOT NULL,
        balance REAL NOT NULL DEFAULT 0,
        account_type TEXT NOT NULL DEFAULT 'employee',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS civ_rewards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        account_key TEXT NOT NULL,
        amount REAL NOT NULL,
        reason TEXT NOT NULL DEFAULT '',
        reward_type TEXT NOT NULL DEFAULT 'incentive',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS civ_performance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        account_key TEXT NOT NULL,
        metric_name TEXT NOT NULL,
        metric_value REAL NOT NULL DEFAULT 0,
        period TEXT NOT NULL DEFAULT 'monthly',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS civ_infra_nodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        node_type TEXT NOT NULL,
        name TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'healthy',
        metrics TEXT NOT NULL DEFAULT '{}',
        config TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        last_check TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS civ_backups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        backup_type TEXT NOT NULL DEFAULT 'full',
        location TEXT NOT NULL DEFAULT '',
        size_mb REAL NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'completed',
        encrypted INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS civ_research (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        research_type TEXT NOT NULL,
        title TEXT NOT NULL,
        findings TEXT NOT NULL DEFAULT '{}',
        summary TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'completed',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS civ_audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        user_id INTEGER,
        action TEXT NOT NULL,
        details TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    conn.commit()

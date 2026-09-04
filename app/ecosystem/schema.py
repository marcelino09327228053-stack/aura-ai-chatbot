"""Ecosystem platform database schema."""


def init_ecosystem_schema(cursor, conn) -> None:
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ecosystem_research (
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
    CREATE TABLE IF NOT EXISTS ecosystem_innovations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        impact_score REAL NOT NULL DEFAULT 0,
        effort_score REAL NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'suggested',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ecosystem_simulations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        scenario_type TEXT NOT NULL,
        parameters TEXT NOT NULL DEFAULT '{}',
        result TEXT NOT NULL DEFAULT '{}',
        confidence REAL NOT NULL DEFAULT 0.7,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ecosystem_automation_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        job_type TEXT NOT NULL,
        title TEXT NOT NULL,
        payload TEXT NOT NULL DEFAULT '{}',
        status TEXT NOT NULL DEFAULT 'pending',
        result TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        completed_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ecosystem_notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        priority TEXT NOT NULL DEFAULT 'medium',
        title TEXT NOT NULL,
        message TEXT NOT NULL DEFAULT '',
        source TEXT NOT NULL DEFAULT 'system',
        read_flag INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ecosystem_agent_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        agent_id TEXT NOT NULL,
        agent_name TEXT NOT NULL,
        domain TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'active',
        last_seen TEXT NOT NULL DEFAULT (datetime('now')),
        performance_score REAL NOT NULL DEFAULT 0.7
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ecosystem_knowledge (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        source_agent TEXT NOT NULL DEFAULT 'system',
        topic TEXT NOT NULL,
        content TEXT NOT NULL,
        shared INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ecosystem_audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        user_id INTEGER,
        action TEXT NOT NULL,
        details TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    conn.commit()

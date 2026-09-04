"""Aura Network database schema."""


def init_network_schema(cursor, conn) -> None:
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS network_nodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        node_id TEXT NOT NULL UNIQUE,
        instance_url TEXT NOT NULL DEFAULT '',
        name TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS network_memberships (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL UNIQUE,
        node_id TEXT NOT NULL,
        network_mode TEXT NOT NULL DEFAULT 'private',
        joined_at TEXT NOT NULL DEFAULT (datetime('now')),
        left_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS network_sync_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        sync_type TEXT NOT NULL,
        direction TEXT NOT NULL DEFAULT 'outbound',
        status TEXT NOT NULL DEFAULT 'pending',
        payload_hash TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS network_federated_updates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model_key TEXT NOT NULL,
        gradient_hash TEXT NOT NULL,
        contributor_count INTEGER NOT NULL DEFAULT 1,
        improvement_score REAL NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS network_agent_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        agent_type TEXT NOT NULL,
        execution_mode TEXT NOT NULL DEFAULT 'local',
        status TEXT NOT NULL DEFAULT 'pending',
        result_preview TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS network_governance (
        company_id INTEGER PRIMARY KEY,
        network_mode TEXT NOT NULL DEFAULT 'private',
        policies_json TEXT NOT NULL DEFAULT '{}',
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS network_shared_resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        resource_type TEXT NOT NULL,
        resource_key TEXT NOT NULL,
        owner_company_id INTEGER NOT NULL,
        shared INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    conn.commit()

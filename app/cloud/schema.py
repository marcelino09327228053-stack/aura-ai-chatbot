"""Aura Cloud database schema."""


def init_cloud_schema(cursor, conn) -> None:
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS billing (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        plan TEXT NOT NULL,
        amount REAL NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'pending',
        billing_cycle TEXT NOT NULL DEFAULT 'monthly',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payment_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        billing_id INTEGER,
        amount REAL NOT NULL,
        method TEXT NOT NULL DEFAULT 'card',
        status TEXT NOT NULL DEFAULT 'completed',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (billing_id) REFERENCES billing(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cloud_api_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        key_hash TEXT NOT NULL UNIQUE,
        key_prefix TEXT NOT NULL,
        scopes TEXT NOT NULL DEFAULT 'read',
        rate_limit INTEGER NOT NULL DEFAULT 60,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        last_used_at TEXT,
        revoked_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS api_gateway_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        api_key_id INTEGER,
        endpoint TEXT NOT NULL,
        method TEXT NOT NULL DEFAULT 'GET',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS white_label_settings (
        company_id INTEGER PRIMARY KEY,
        logo_url TEXT NOT NULL DEFAULT '',
        custom_domain TEXT NOT NULL DEFAULT '',
        theme_json TEXT NOT NULL DEFAULT '{}',
        brand_name TEXT NOT NULL DEFAULT '',
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS marketplace_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        extension_key TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        rating INTEGER NOT NULL DEFAULT 5,
        review_text TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS marketplace_updates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        extension_key TEXT NOT NULL,
        version TEXT NOT NULL,
        changelog TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trial_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL UNIQUE,
        started_at TEXT NOT NULL DEFAULT (datetime('now')),
        expires_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active'
    )
    """)

    conn.commit()

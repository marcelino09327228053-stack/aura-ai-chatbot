"""
Database connection — delegates to infrastructure backends.

SQLite (development, default) or PostgreSQL (production via DB_BACKEND=postgres).
"""

from app.infrastructure.database import column_exists as _column_exists
from app.infrastructure.database import get_connection, table_exists as _table_exists

DB_PATH = "aura.db"


def _migrate_faq_company_scope(cursor, conn) -> None:
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faq (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    if not _column_exists(cursor, "faq", "created_at"):
        cursor.execute("ALTER TABLE faq ADD COLUMN created_at TEXT")
        cursor.execute("UPDATE faq SET created_at = datetime('now') WHERE created_at IS NULL")

    if not _column_exists(cursor, "faq", "company_id"):
        cursor.execute("ALTER TABLE faq ADD COLUMN company_id INTEGER DEFAULT 1")
        cursor.execute("UPDATE faq SET company_id = 1 WHERE company_id IS NULL")

    conn.commit()

    cursor.execute("""
    DELETE FROM faq
    WHERE id NOT IN (
        SELECT MIN(id)
        FROM faq
        GROUP BY company_id, LOWER(question)
    )
    """)
    conn.commit()

    cursor.execute("DROP INDEX IF EXISTS idx_faq_question")
    cursor.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_faq_company_question
    ON faq (company_id, question COLLATE NOCASE)
    """)
    conn.commit()


def init_db() -> None:
    """Create tables, run migrations, and seed defaults."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL DEFAULT '',
        profile_image TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)
    if not _column_exists(cursor, "users", "full_name"):
        cursor.execute("ALTER TABLE users ADD COLUMN full_name TEXT NOT NULL DEFAULT ''")
        conn.commit()
    if not _column_exists(cursor, "users", "profile_image"):
        cursor.execute("ALTER TABLE users ADD COLUMN profile_image TEXT NOT NULL DEFAULT ''")
        conn.commit()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS oauth_identities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        provider TEXT NOT NULL,
        subject TEXT NOT NULL,
        email TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(provider, subject),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER,
        company_name TEXT NOT NULL,
        company_profile TEXT NOT NULL DEFAULT '',
        company_profile_source TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (owner_id) REFERENCES users(id)
    )
    """)
    if not _column_exists(cursor, "companies", "company_profile_source"):
        cursor.execute("ALTER TABLE companies ADD COLUMN company_profile_source TEXT NOT NULL DEFAULT ''")
        cursor.execute(
            "UPDATE companies SET company_profile_source = company_profile "
            "WHERE company_profile_source = '' AND company_profile != ''"
        )
        conn.commit()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS company_profile_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        version_name TEXT NOT NULL DEFAULT '',
        company_profile TEXT NOT NULL,
        company_profile_source TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (company_id) REFERENCES companies(id)
    )
    """)
    if not _column_exists(cursor, "company_profile_versions", "version_name"):
        cursor.execute(
            "ALTER TABLE company_profile_versions ADD COLUMN version_name TEXT NOT NULL DEFAULT ''"
        )
        conn.commit()
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_company_profile_versions_company
    ON company_profile_versions (company_id, id DESC)
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL UNIQUE,
        plan TEXT NOT NULL DEFAULT 'free',
        status TEXT NOT NULL DEFAULT 'active',
        expires_at TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (company_id) REFERENCES companies(id)
    )
    """)
    subscription_columns = {
        "billing_cycle_start": "TEXT",
        "billing_cycle_end": "TEXT",
        "plan_price_minor": "INTEGER NOT NULL DEFAULT 0",
        "monthly_ai_allowance_minor": "INTEGER NOT NULL DEFAULT 0",
        "ai_usage_consumed_minor": "INTEGER NOT NULL DEFAULT 0",
        "allowance_currency": "TEXT NOT NULL DEFAULT 'PHP'",
        "allowance_reset_at": "TEXT",
    }
    for column_name, column_type in subscription_columns.items():
        if not _column_exists(cursor, "subscriptions", column_name):
            cursor.execute(
                f"ALTER TABLE subscriptions ADD COLUMN {column_name} {column_type}"
            )
    conn.commit()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ai_gateway_requests (
        request_id TEXT PRIMARY KEY,
        company_id INTEGER NOT NULL,
        user_id INTEGER,
        provider TEXT NOT NULL DEFAULT '',
        model TEXT NOT NULL DEFAULT '',
        input_tokens INTEGER NOT NULL DEFAULT 0,
        output_tokens INTEGER NOT NULL DEFAULT 0,
        provider_cost_usd REAL,
        allowance_deducted_minor INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'pending',
        error_code TEXT NOT NULL DEFAULT '',
        attempt_count INTEGER NOT NULL DEFAULT 0,
        response_text TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        completed_at TEXT,
        FOREIGN KEY (company_id) REFERENCES companies(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
    if not _column_exists(cursor, "ai_gateway_requests", "allowance_deducted_minor"):
        cursor.execute(
            "ALTER TABLE ai_gateway_requests ADD COLUMN allowance_deducted_minor INTEGER NOT NULL DEFAULT 0"
        )
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_ai_gateway_requests_company_created
    ON ai_gateway_requests (company_id, created_at)
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mock_payment_events (
        event_id TEXT PRIMARY KEY,
        company_id INTEGER NOT NULL,
        plan TEXT NOT NULL,
        amount_minor INTEGER NOT NULL,
        currency TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'processing',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        processed_at TEXT,
        FOREIGN KEY (company_id) REFERENCES companies(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token_hash TEXT NOT NULL UNIQUE,
        expires_at TEXT NOT NULL,
        used_at TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS email_login_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        code_hash TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        attempts INTEGER NOT NULL DEFAULT 0,
        used_at TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_email_login_codes_email
    ON email_login_codes (email, created_at)
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (company_id) REFERENCES companies(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS company_settings (
        company_id INTEGER PRIMARY KEY,
        settings_json TEXT NOT NULL DEFAULT '{}',
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (company_id) REFERENCES companies(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ai_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        contact_key TEXT NOT NULL DEFAULT 'default',
        memory_type TEXT NOT NULL DEFAULT 'general',
        content TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (company_id) REFERENCES companies(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usage_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        event_type TEXT NOT NULL DEFAULT 'message',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (company_id) REFERENCES companies(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ai_provider_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        provider TEXT NOT NULL,
        model TEXT NOT NULL DEFAULT '',
        input_tokens INTEGER NOT NULL DEFAULT 0,
        output_tokens INTEGER NOT NULL DEFAULT 0,
        estimated_cost REAL,
        status TEXT NOT NULL DEFAULT 'success',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (company_id) REFERENCES companies(id)
    )
    """)
    if not _column_exists(cursor, "ai_provider_usage", "request_id"):
        cursor.execute("ALTER TABLE ai_provider_usage ADD COLUMN request_id TEXT")
    if not _column_exists(cursor, "ai_provider_usage", "allowance_deducted_minor"):
        cursor.execute(
            "ALTER TABLE ai_provider_usage ADD COLUMN allowance_deducted_minor INTEGER NOT NULL DEFAULT 0"
        )
    cursor.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_ai_provider_usage_request
    ON ai_provider_usage (request_id)
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ai_provider_credentials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        provider TEXT NOT NULL,
        encrypted_key TEXT NOT NULL,
        key_suffix TEXT NOT NULL DEFAULT '',
        connected_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(company_id, provider),
        FOREIGN KEY (company_id) REFERENCES companies(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS facebook_connections (
        company_id INTEGER PRIMARY KEY,
        page_id TEXT NOT NULL UNIQUE,
        page_name TEXT NOT NULL DEFAULT '',
        encrypted_page_token TEXT NOT NULL,
        encrypted_app_secret TEXT NOT NULL,
        verify_token TEXT NOT NULL UNIQUE,
        connected_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (company_id) REFERENCES companies(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS facebook_oauth_sessions (
        session_id TEXT PRIMARY KEY,
        company_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        encrypted_pages TEXT NOT NULL,
        expires_at INTEGER NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (company_id) REFERENCES companies(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS channel_spam_state (
        company_id INTEGER NOT NULL,
        channel TEXT NOT NULL,
        sender_id TEXT NOT NULL,
        window_started_at INTEGER NOT NULL,
        message_count INTEGER NOT NULL DEFAULT 0,
        last_message_hash TEXT NOT NULL DEFAULT '',
        repeated_count INTEGER NOT NULL DEFAULT 0,
        blocked_until INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        PRIMARY KEY (company_id, channel, sender_id),
        FOREIGN KEY (company_id) REFERENCES companies(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS widget_settings (
        company_id INTEGER PRIMARY KEY,
        public_token TEXT NOT NULL UNIQUE,
        enabled INTEGER NOT NULL DEFAULT 1,
        title TEXT NOT NULL DEFAULT 'Chat with us',
        welcome_message TEXT NOT NULL DEFAULT 'Hello! How can we help you today?',
        primary_color TEXT NOT NULL DEFAULT '#7c3aed',
        position TEXT NOT NULL DEFAULT 'right',
        allowed_domains TEXT NOT NULL DEFAULT '[]',
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (company_id) REFERENCES companies(id)
    )
    """)
    if not _column_exists(cursor, "widget_settings", "allowed_domains"):
        cursor.execute(
            "ALTER TABLE widget_settings ADD COLUMN allowed_domains TEXT NOT NULL DEFAULT '[]'"
        )

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS widget_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        session_id TEXT NOT NULL DEFAULT '',
        event_type TEXT NOT NULL,
        question TEXT NOT NULL DEFAULT '',
        answer_source TEXT NOT NULL DEFAULT '',
        origin TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (company_id) REFERENCES companies(id)
    )
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_widget_events_company_created
    ON widget_events (company_id, created_at)
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        content_type TEXT NOT NULL DEFAULT 'text/plain',
        size_bytes INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'ready',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (company_id) REFERENCES companies(id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        document_id INTEGER NOT NULL,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (company_id) REFERENCES companies(id),
        FOREIGN KEY (document_id) REFERENCES knowledge_documents(id)
    )
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_company_document
    ON knowledge_chunks (company_id, document_id)
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS support_conversations (
        company_id INTEGER NOT NULL,
        session_id TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'open',
        mode TEXT NOT NULL DEFAULT 'ai',
        assigned_user_id INTEGER,
        customer_name TEXT NOT NULL DEFAULT '',
        customer_email TEXT NOT NULL DEFAULT '',
        last_activity_at TEXT NOT NULL DEFAULT (datetime('now')),
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        PRIMARY KEY (company_id, session_id),
        FOREIGN KEY (company_id) REFERENCES companies(id)
    )
    """)

    conn.commit()

    _migrate_faq_company_scope(cursor, conn)

    cursor.execute("SELECT id FROM companies WHERE id = 1")
    if cursor.fetchone() is None:
        cursor.execute("""
        INSERT INTO companies (id, owner_id, company_name, company_profile)
        VALUES (1, NULL, 'Legacy Company', '')
        """)
        conn.commit()

    cursor.execute("SELECT id FROM subscriptions WHERE company_id = 1")
    if cursor.fetchone() is None:
        cursor.execute("""
        INSERT INTO subscriptions (company_id, plan, status)
        VALUES (1, 'enterprise', 'active')
        """)
        conn.commit()

    cursor.execute("SELECT COUNT(*) FROM faq WHERE company_id = 1")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO faq (company_id, question, answer)
        VALUES (1, ?, ?)
        """, (
            "What are your business hours?",
            "We are open from 8 AM to 5 PM.",
        ))
        conn.commit()

    from app.modules.schema import init_business_modules
    init_business_modules(cursor, conn)

    from app.agents.schema import init_agent_schema
    init_agent_schema(cursor, conn)

    from app.agents.repository import ensure_company_agents
    ensure_company_agents(1)

    from app.plugins.registry.schema import init_plugin_schema
    init_plugin_schema(cursor, conn)

    from app.infrastructure.audit.repository import init_audit_schema
    init_audit_schema(cursor, conn)

    from app.infrastructure.team.repository import init_team_schema
    init_team_schema(cursor, conn)

    from app.cloud.schema import init_cloud_schema
    init_cloud_schema(cursor, conn)

    from app.cloud.marketplace import service as marketplace_service
    for key, version in [
        ("email_sender", "1.0.0"),
        ("sms_sender", "1.0.0"),
        ("pdf_generator", "1.0.0"),
        ("inventory_sync", "1.0.0"),
    ]:
        if not marketplace_service.get_latest_version(key):
            marketplace_service.register_update(key, version, "Initial release")

    from app.os.schema import init_os_schema
    init_os_schema(cursor, conn)

    from app.network.schema import init_network_schema
    init_network_schema(cursor, conn)

    from app.intelligence.schema import init_intelligence_schema
    init_intelligence_schema(cursor, conn)

    import importlib
    init_global_schema = importlib.import_module("app.global.schema").init_global_schema
    init_global_schema(cursor, conn)

    from app.enterprise.schema import init_enterprise_schema
    init_enterprise_schema(cursor, conn)

    from app.corporation.schema import init_corporation_schema
    init_corporation_schema(cursor, conn)

    from app.economy.schema import init_economy_schema
    init_economy_schema(cursor, conn)

    from app.commerce.schema import init_commerce_schema
    init_commerce_schema(cursor, conn)

    from app.ecosystem.schema import init_ecosystem_schema
    init_ecosystem_schema(cursor, conn)

    from app.universe.schema import init_universe_schema
    init_universe_schema(cursor, conn)

    from app.civilization.schema import init_civilization_schema
    init_civilization_schema(cursor, conn)

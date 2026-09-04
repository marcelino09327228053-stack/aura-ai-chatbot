"""Global Intelligence database schema."""


def init_global_schema(cursor, conn) -> None:
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS global_language_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL UNIQUE,
        primary_language TEXT NOT NULL DEFAULT 'en',
        supported_languages TEXT NOT NULL DEFAULT 'en',
        timezone TEXT NOT NULL DEFAULT 'UTC',
        date_format TEXT NOT NULL DEFAULT 'YYYY-MM-DD',
        currency_code TEXT NOT NULL DEFAULT 'PHP',
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS global_translations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        source_text TEXT NOT NULL,
        source_lang TEXT NOT NULL DEFAULT 'en',
        target_lang TEXT NOT NULL,
        translated_text TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS global_document_analyses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        document_type TEXT NOT NULL,
        document_name TEXT NOT NULL DEFAULT '',
        content_hash TEXT NOT NULL DEFAULT '',
        extracted_data TEXT NOT NULL DEFAULT '{}',
        summary TEXT NOT NULL DEFAULT '',
        risk_flags TEXT NOT NULL DEFAULT '[]',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS global_insights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        insight_type TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        region TEXT NOT NULL DEFAULT 'global',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS global_regulations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_code TEXT NOT NULL,
        regulation_type TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        effective_date TEXT NOT NULL DEFAULT '',
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS global_audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        details TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    # Seed core regulations
    cursor.execute("SELECT COUNT(*) as cnt FROM global_regulations")
    if cursor.fetchone()["cnt"] == 0:
        regulations = [
            ("PH", "tax", "Philippine VAT", "12% VAT applies to most goods and services", "2006-01-01"),
            ("PH", "labor", "Philippine Labor Code", "Minimum wage, 13th month pay, SSS/PhilHealth/Pag-IBIG mandatory", "1974-05-01"),
            ("PH", "data_privacy", "Data Privacy Act of 2012", "Personal data must be protected; NPC registration required for large processors", "2012-08-15"),
            ("US", "tax", "US Federal Tax", "Corporate tax rate 21%; state taxes vary", "2018-01-01"),
            ("US", "data_privacy", "CCPA", "California Consumer Privacy Act — rights for CA residents", "2020-01-01"),
            ("EU", "data_privacy", "GDPR", "General Data Protection Regulation — strict data handling rules", "2018-05-25"),
            ("EU", "tax", "EU VAT", "Value Added Tax ranges from 17–27% across EU member states", "1977-01-01"),
            ("JP", "tax", "Japan Consumption Tax", "10% consumption tax on most goods and services", "2019-10-01"),
            ("CN", "tax", "China VAT", "13% standard VAT rate; 6% for services", "2019-04-01"),
            ("KR", "tax", "Korea VAT", "10% standard VAT rate", "1977-07-01"),
            ("ES", "tax", "Spain IVA", "21% standard VAT (IVA) rate", "2012-09-01"),
        ]
        cursor.executemany(
            "INSERT INTO global_regulations (country_code, regulation_type, title, description, effective_date) VALUES (?,?,?,?,?)",
            regulations,
        )

    conn.commit()

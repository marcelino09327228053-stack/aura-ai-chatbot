"""Global Intelligence data access layer."""

import json

from app.infrastructure.database import get_connection


def get_language_settings(company_id: int) -> dict:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM global_language_settings WHERE company_id = ?",
        (company_id,),
    )
    row = cursor.fetchone()
    if row:
        data = dict(row)
        data["supported_languages"] = json.loads(data.get("supported_languages") or '["en"]')
        return data
    return {
        "company_id": company_id,
        "primary_language": "en",
        "supported_languages": ["en"],
        "timezone": "UTC",
        "date_format": "YYYY-MM-DD",
        "currency_code": "PHP",
    }


def save_language_settings(company_id: int, settings: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    supported = json.dumps(settings.get("supported_languages", ["en"]))
    cursor.execute(
        """
        INSERT INTO global_language_settings
            (company_id, primary_language, supported_languages, timezone, date_format, currency_code)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(company_id) DO UPDATE SET
            primary_language = excluded.primary_language,
            supported_languages = excluded.supported_languages,
            timezone = excluded.timezone,
            date_format = excluded.date_format,
            currency_code = excluded.currency_code,
            updated_at = datetime('now')
        """,
        (
            company_id,
            settings.get("primary_language", "en"),
            supported,
            settings.get("timezone", "UTC"),
            settings.get("date_format", "YYYY-MM-DD"),
            settings.get("currency_code", "PHP"),
        ),
    )
    conn.commit()
    return get_language_settings(company_id)


def save_translation(
    company_id: int,
    source_text: str,
    source_lang: str,
    target_lang: str,
    translated_text: str,
) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO global_translations
            (company_id, source_text, source_lang, target_lang, translated_text)
        VALUES (?, ?, ?, ?, ?)
        """,
        (company_id, source_text[:2000], source_lang, target_lang, translated_text[:2000]),
    )
    conn.commit()
    cursor.execute("SELECT * FROM global_translations WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_translations(company_id: int, limit: int = 20) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM global_translations WHERE company_id = ? ORDER BY created_at DESC LIMIT ?",
        (company_id, limit),
    )
    return [dict(r) for r in cursor.fetchall()]


def save_document_analysis(
    company_id: int,
    document_type: str,
    document_name: str,
    extracted_data: dict,
    summary: str,
    risk_flags: list,
    content_hash: str = "",
) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO global_document_analyses
            (company_id, document_type, document_name, content_hash, extracted_data, summary, risk_flags)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            company_id,
            document_type,
            document_name,
            content_hash,
            json.dumps(extracted_data),
            summary[:1000],
            json.dumps(risk_flags),
        ),
    )
    conn.commit()
    cursor.execute(
        "SELECT * FROM global_document_analyses WHERE id = ?", (cursor.lastrowid,)
    )
    row = dict(cursor.fetchone())
    row["extracted_data"] = extracted_data
    row["risk_flags"] = risk_flags
    return row


def list_document_analyses(company_id: int, doc_type: str | None = None, limit: int = 20) -> list[dict]:
    cursor = get_connection().cursor()
    if doc_type:
        cursor.execute(
            "SELECT * FROM global_document_analyses WHERE company_id = ? AND document_type = ? ORDER BY created_at DESC LIMIT ?",
            (company_id, doc_type, limit),
        )
    else:
        cursor.execute(
            "SELECT * FROM global_document_analyses WHERE company_id = ? ORDER BY created_at DESC LIMIT ?",
            (company_id, limit),
        )
    rows = []
    for r in cursor.fetchall():
        data = dict(r)
        try:
            data["extracted_data"] = json.loads(data.get("extracted_data") or "{}")
            data["risk_flags"] = json.loads(data.get("risk_flags") or "[]")
        except Exception:
            data["extracted_data"] = {}
            data["risk_flags"] = []
        rows.append(data)
    return rows


def save_insight(
    company_id: int,
    insight_type: str,
    title: str,
    content: str,
    region: str = "global",
) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO global_insights (company_id, insight_type, title, content, region) VALUES (?,?,?,?,?)",
        (company_id, insight_type, title, content[:1000], region),
    )
    conn.commit()
    cursor.execute("SELECT * FROM global_insights WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_insights(company_id: int, insight_type: str | None = None, limit: int = 20) -> list[dict]:
    cursor = get_connection().cursor()
    if insight_type:
        cursor.execute(
            "SELECT * FROM global_insights WHERE company_id = ? AND insight_type = ? ORDER BY created_at DESC LIMIT ?",
            (company_id, insight_type, limit),
        )
    else:
        cursor.execute(
            "SELECT * FROM global_insights WHERE company_id = ? ORDER BY created_at DESC LIMIT ?",
            (company_id, limit),
        )
    return [dict(r) for r in cursor.fetchall()]


def get_regulations(country_code: str | None = None, regulation_type: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    conditions = []
    params = []
    if country_code:
        conditions.append("country_code = ?")
        params.append(country_code.upper())
    if regulation_type:
        conditions.append("regulation_type = ?")
        params.append(regulation_type)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    cursor.execute(f"SELECT * FROM global_regulations {where} ORDER BY country_code, regulation_type", params)
    return [dict(r) for r in cursor.fetchall()]


def log_global_action(company_id: int, action: str, details: str = "") -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO global_audit (company_id, action, details) VALUES (?,?,?)",
        (company_id, action, details[:500]),
    )
    conn.commit()

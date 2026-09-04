"""Per-company settings storage."""

import json

from app.database.connection import get_connection


def get_settings(company_id: int) -> dict:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT settings_json FROM company_settings WHERE company_id = ?",
        (company_id,),
    )
    row = cursor.fetchone()
    if not row:
        return {}
    try:
        return json.loads(row["settings_json"])
    except json.JSONDecodeError:
        return {}


def save_settings(company_id: int, settings: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO company_settings (company_id, settings_json, updated_at)
        VALUES (?, ?, datetime('now'))
        ON CONFLICT(company_id) DO UPDATE SET
            settings_json = excluded.settings_json,
            updated_at = datetime('now')
        """,
        (company_id, json.dumps(settings)),
    )
    conn.commit()
    return get_settings(company_id)

"""White-label branding data access."""

import json

from app.infrastructure.database import get_connection


def get_branding(company_id: int) -> dict:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM white_label_settings WHERE company_id = ?",
        (company_id,),
    )
    row = cursor.fetchone()
    if not row:
        return {
            "company_id": company_id,
            "logo_url": "",
            "custom_domain": "",
            "theme": {},
            "brand_name": "",
        }
    data = dict(row)
    data["theme"] = json.loads(data.pop("theme_json", "{}") or "{}")
    return data


def update_branding(company_id: int, **fields) -> dict:
    current = get_branding(company_id)
    logo_url = fields.get("logo_url", current.get("logo_url", ""))
    custom_domain = fields.get("custom_domain", current.get("custom_domain", ""))
    brand_name = fields.get("brand_name", current.get("brand_name", ""))
    theme = fields.get("theme", current.get("theme", {}))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO white_label_settings (company_id, logo_url, custom_domain, theme_json, brand_name)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(company_id) DO UPDATE SET
            logo_url = excluded.logo_url,
            custom_domain = excluded.custom_domain,
            theme_json = excluded.theme_json,
            brand_name = excluded.brand_name,
            updated_at = datetime('now')
        """,
        (company_id, logo_url, custom_domain, json.dumps(theme), brand_name),
    )
    conn.commit()
    return get_branding(company_id)

"""Encrypted Facebook Page connections and short-lived OAuth handoffs."""

import json
import secrets
import time

from app.cloud.security import decrypt_value, encrypt_value
from app.database.connection import get_connection


def save(company_id: int, page_id: str, page_name: str, page_token: str, app_secret: str) -> dict:
    verify_token = secrets.token_urlsafe(24)
    conn = get_connection()
    conn.cursor().execute(
        """
        INSERT INTO facebook_connections
        (company_id, page_id, page_name, encrypted_page_token, encrypted_app_secret, verify_token)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(company_id) DO UPDATE SET
            page_id = excluded.page_id,
            page_name = excluded.page_name,
            encrypted_page_token = excluded.encrypted_page_token,
            encrypted_app_secret = excluded.encrypted_app_secret,
            verify_token = excluded.verify_token,
            updated_at = datetime('now')
        """,
        (company_id, page_id, page_name, encrypt_value(page_token), encrypt_value(app_secret), verify_token),
    )
    conn.commit()
    return get_for_company(company_id) or {}


def _decode(row) -> dict | None:
    if not row:
        return None
    data = dict(row)
    data["page_token"] = decrypt_value(data.pop("encrypted_page_token"))
    data["app_secret"] = decrypt_value(data.pop("encrypted_app_secret"))
    return data


def get_for_company(company_id: int) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute("SELECT * FROM facebook_connections WHERE company_id = ?", (company_id,))
    return _decode(cursor.fetchone())


def get_for_page(page_id: str) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute("SELECT * FROM facebook_connections WHERE page_id = ?", (page_id,))
    return _decode(cursor.fetchone())


def verify_token_exists(verify_token: str) -> bool:
    cursor = get_connection().cursor()
    cursor.execute("SELECT 1 FROM facebook_connections WHERE verify_token = ?", (verify_token,))
    return cursor.fetchone() is not None


def delete(company_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM facebook_connections WHERE company_id = ?", (company_id,))
    conn.commit()
    return cursor.rowcount > 0


def save_oauth_session(session_id: str, company_id: int, user_id: int, pages: list[dict], expires_at: int) -> None:
    conn = get_connection()
    conn.cursor().execute(
        """
        INSERT INTO facebook_oauth_sessions
        (session_id, company_id, user_id, encrypted_pages, expires_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            company_id = excluded.company_id,
            user_id = excluded.user_id,
            encrypted_pages = excluded.encrypted_pages,
            expires_at = excluded.expires_at
        """,
        (session_id, company_id, user_id, encrypt_value(json.dumps(pages)), expires_at),
    )
    conn.commit()


def get_oauth_session(session_id: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM facebook_oauth_sessions WHERE expires_at < ?", (int(time.time()),))
    cursor.execute("SELECT * FROM facebook_oauth_sessions WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()
    conn.commit()
    if not row:
        return None
    data = dict(row)
    data["pages"] = json.loads(decrypt_value(data.pop("encrypted_pages")))
    return data


def delete_oauth_session(session_id: str) -> None:
    conn = get_connection()
    conn.cursor().execute("DELETE FROM facebook_oauth_sessions WHERE session_id = ?", (session_id,))
    conn.commit()

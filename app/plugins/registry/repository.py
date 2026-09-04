"""Plugin data access."""

import json

from app.database.connection import get_connection


def _row_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "company_id": row["company_id"],
        "name": row["name"],
        "version": row["version"],
        "description": row["description"],
        "enabled": bool(row["enabled"]),
        "plugin_key": row["plugin_key"],
        "manifest": json.loads(row["manifest_json"] or "{}"),
        "settings": json.loads(row["settings_json"] or "{}"),
        "created_at": row["created_at"],
    }


def list_plugins(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT id, company_id, name, version, description, enabled,
               plugin_key, manifest_json, settings_json, created_at
        FROM plugins WHERE company_id = ?
        ORDER BY created_at DESC
        """,
        (company_id,),
    )
    return [_row_to_dict(r) for r in cursor.fetchall()]


def get_plugin(company_id: int, plugin_id: int) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT id, company_id, name, version, description, enabled,
               plugin_key, manifest_json, settings_json, created_at
        FROM plugins WHERE company_id = ? AND id = ?
        """,
        (company_id, plugin_id),
    )
    row = cursor.fetchone()
    return _row_to_dict(row) if row else None


def get_plugin_by_key(company_id: int, plugin_key: str) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT id, company_id, name, version, description, enabled,
               plugin_key, manifest_json, settings_json, created_at
        FROM plugins WHERE company_id = ? AND plugin_key = ?
        """,
        (company_id, plugin_key),
    )
    row = cursor.fetchone()
    return _row_to_dict(row) if row else None


def create_plugin(
    company_id: int,
    plugin_key: str,
    name: str,
    version: str,
    description: str,
    manifest: dict,
    enabled: bool = False,
) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO plugins (company_id, plugin_key, name, version, description, enabled, manifest_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            company_id,
            plugin_key,
            name,
            version,
            description,
            1 if enabled else 0,
            json.dumps(manifest),
        ),
    )
    conn.commit()
    return get_plugin(company_id, cursor.lastrowid)


def set_plugin_enabled(company_id: int, plugin_id: int, enabled: bool) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE plugins SET enabled = ? WHERE company_id = ? AND id = ?",
        (1 if enabled else 0, company_id, plugin_id),
    )
    conn.commit()
    return get_plugin(company_id, plugin_id)


def update_plugin_settings(company_id: int, plugin_id: int, settings: dict) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE plugins SET settings_json = ? WHERE company_id = ? AND id = ?",
        (json.dumps(settings), company_id, plugin_id),
    )
    conn.commit()
    return get_plugin(company_id, plugin_id)


def delete_plugin(company_id: int, plugin_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM plugin_logs WHERE plugin_id = ?", (plugin_id,))
    cursor.execute(
        "DELETE FROM plugins WHERE company_id = ? AND id = ?",
        (company_id, plugin_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def add_log(company_id: int, plugin_id: int, message: str, level: str = "info") -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO plugin_logs (company_id, plugin_id, level, message)
        VALUES (?, ?, ?, ?)
        """,
        (company_id, plugin_id, level, message[:2000]),
    )
    conn.commit()


def list_logs(company_id: int, plugin_id: int | None = None, limit: int = 50) -> list[dict]:
    cursor = get_connection().cursor()
    if plugin_id is not None:
        cursor.execute(
            """
            SELECT * FROM plugin_logs
            WHERE company_id = ? AND plugin_id = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (company_id, plugin_id, limit),
        )
    else:
        cursor.execute(
            """
            SELECT * FROM plugin_logs
            WHERE company_id = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (company_id, limit),
        )
    return [dict(r) for r in cursor.fetchall()]


def create_api_key(company_id: int, name: str, key_hash: str, key_prefix: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO plugin_api_keys (company_id, name, key_hash, key_prefix)
        VALUES (?, ?, ?, ?)
        """,
        (company_id, name, key_hash, key_prefix),
    )
    conn.commit()
    cursor.execute("SELECT * FROM plugin_api_keys WHERE id = ?", (cursor.lastrowid,))
    row = dict(cursor.fetchone())
    row["key"] = None
    return row


def list_api_keys(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT id, company_id, name, key_prefix, created_at, last_used_at, revoked_at
        FROM plugin_api_keys WHERE company_id = ?
        ORDER BY created_at DESC
        """,
        (company_id,),
    )
    return [dict(r) for r in cursor.fetchall()]


def get_api_key_by_hash(key_hash: str) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM plugin_api_keys WHERE key_hash = ? AND revoked_at IS NULL",
        (key_hash,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def touch_api_key(key_id: int) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE plugin_api_keys SET last_used_at = datetime('now') WHERE id = ?",
        (key_id,),
    )
    conn.commit()


def revoke_api_key(company_id: int, key_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE plugin_api_keys SET revoked_at = datetime('now')
        WHERE company_id = ? AND id = ? AND revoked_at IS NULL
        """,
        (company_id, key_id),
    )
    conn.commit()
    return cursor.rowcount > 0

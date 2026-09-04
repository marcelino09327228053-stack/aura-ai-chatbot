"""Persistent version history for company profiles."""

from app.database.connection import get_connection


def add_version(
    company_id: int,
    company_profile: str,
    company_profile_source: str = "",
    version_name: str = "",
) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO company_profile_versions
        (company_id, company_profile, company_profile_source, version_name)
        VALUES (?, ?, ?, ?)""",
        (company_id, company_profile, company_profile_source, version_name.strip()),
    )
    conn.commit()
    return get_version(company_id, cursor.lastrowid)


def get_version(company_id: int, version_id: int) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        """SELECT id, company_id, version_name, company_profile, company_profile_source, created_at
        FROM company_profile_versions WHERE company_id = ? AND id = ?""",
        (company_id, version_id),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def list_versions(company_id: int, limit: int = 20) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        """SELECT id, company_id, version_name, company_profile, company_profile_source, created_at
        FROM company_profile_versions WHERE company_id = ? ORDER BY id DESC LIMIT ?""",
        (company_id, max(1, min(limit, 50))),
    )
    return [dict(row) for row in cursor.fetchall()]


def rename_version(company_id: int, version_id: int, version_name: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE company_profile_versions SET version_name = ? WHERE company_id = ? AND id = ?",
        (version_name.strip(), company_id, version_id),
    )
    conn.commit()
    return get_version(company_id, version_id) if cursor.rowcount else None


def delete_version(company_id: int, version_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM company_profile_versions WHERE company_id = ? AND id = ?",
        (company_id, version_id),
    )
    conn.commit()
    return cursor.rowcount > 0

"""Company data access."""

import sqlite3

from app.database.connection import get_connection


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "owner_id": row["owner_id"],
        "company_name": row["company_name"],
        "company_profile": row["company_profile"],
        "company_profile_source": row["company_profile_source"],
        "created_at": row["created_at"],
    }


def create_company(owner_id: int, company_name: str, company_profile: str = "") -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO companies (owner_id, company_name, company_profile)
        VALUES (?, ?, ?)
        """,
        (owner_id, company_name.strip(), company_profile),
    )
    conn.commit()
    company = get_company(cursor.lastrowid)
    from app.agents.repository import ensure_company_agents
    ensure_company_agents(company["id"])
    return company


def get_company(company_id: int) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT id, owner_id, company_name, company_profile, company_profile_source, created_at
        FROM companies WHERE id = ?
        """,
        (company_id,),
    )
    row = cursor.fetchone()
    return _row_to_dict(row) if row else None


def list_companies_by_owner(owner_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT id, owner_id, company_name, company_profile, company_profile_source, created_at
        FROM companies
        WHERE owner_id = ?
        ORDER BY created_at ASC, id ASC
        """,
        (owner_id,),
    )
    return [_row_to_dict(row) for row in cursor.fetchall()]


def count_companies_by_owner(owner_id: int) -> int:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM companies WHERE owner_id = ?",
        (owner_id,),
    )
    return cursor.fetchone()[0]


def user_owns_company(user_id: int, company_id: int) -> bool:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT 1 FROM companies WHERE id = ? AND owner_id = ?",
        (company_id, user_id),
    )
    return cursor.fetchone() is not None


def update_company(
    company_id: int,
    company_name: str | None = None,
    company_profile: str | None = None,
    company_profile_source: str | None = None,
) -> dict | None:
    company = get_company(company_id)
    if company is None:
        return None

    name = company_name if company_name is not None else company["company_name"]
    profile = company_profile if company_profile is not None else company["company_profile"]
    profile_source = (
        company_profile_source
        if company_profile_source is not None
        else company["company_profile_source"]
    )

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE companies
        SET company_name = ?, company_profile = ?, company_profile_source = ?
        WHERE id = ?
        """,
        (name.strip(), profile, profile_source, company_id),
    )
    conn.commit()
    return get_company(company_id)

"""CRM data access."""

import sqlite3

from app.database.connection import get_connection


def _customer_row(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "company_id": row["company_id"],
        "name": row["name"],
        "phone": row["phone"],
        "email": row["email"],
        "created_at": row["created_at"],
    }


def list_customers(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM customers WHERE company_id = ? ORDER BY created_at DESC",
        (company_id,),
    )
    return [_customer_row(r) for r in cursor.fetchall()]


def create_customer(company_id: int, name: str, phone: str = "", email: str = "") -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO customers (company_id, name, phone, email) VALUES (?, ?, ?, ?)",
        (company_id, name.strip(), phone.strip(), email.strip()),
    )
    conn.commit()
    cursor.execute("SELECT * FROM customers WHERE id = ?", (cursor.lastrowid,))
    return _customer_row(cursor.fetchone())


def update_customer(company_id: int, customer_id: int, **fields) -> dict | None:
    customer = get_customer(company_id, customer_id)
    if not customer:
        return None
    name = fields.get("name", customer["name"])
    phone = fields.get("phone", customer["phone"])
    email = fields.get("email", customer["email"])
    conn = get_connection()
    conn.cursor().execute(
        "UPDATE customers SET name=?, phone=?, email=? WHERE id=? AND company_id=?",
        (name, phone, email, customer_id, company_id),
    )
    conn.commit()
    return get_customer(company_id, customer_id)


def get_customer(company_id: int, customer_id: int) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM customers WHERE id = ? AND company_id = ?",
        (customer_id, company_id),
    )
    row = cursor.fetchone()
    return _customer_row(row) if row else None


def delete_customer(company_id: int, customer_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM customers WHERE id = ? AND company_id = ?",
        (customer_id, company_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def count_customers(company_id: int) -> int:
    cursor = get_connection().cursor()
    cursor.execute("SELECT COUNT(*) FROM customers WHERE company_id = ?", (company_id,))
    return cursor.fetchone()[0]


def list_leads(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM crm_leads WHERE company_id = ? ORDER BY created_at DESC",
        (company_id,),
    )
    return [dict(r) for r in cursor.fetchall()]


def create_lead(company_id: int, name: str, status: str = "new", source: str = "", customer_id: int | None = None) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO crm_leads (company_id, customer_id, name, status, source) VALUES (?, ?, ?, ?, ?)",
        (company_id, customer_id, name.strip(), status, source),
    )
    conn.commit()
    cursor.execute("SELECT * FROM crm_leads WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_notes(company_id: int, customer_id: int | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if customer_id:
        cursor.execute(
            "SELECT * FROM crm_notes WHERE company_id = ? AND customer_id = ? ORDER BY created_at DESC",
            (company_id, customer_id),
        )
    else:
        cursor.execute(
            "SELECT * FROM crm_notes WHERE company_id = ? ORDER BY created_at DESC",
            (company_id,),
        )
    return [dict(r) for r in cursor.fetchall()]


def create_note(company_id: int, body: str, customer_id: int | None = None, lead_id: int | None = None) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO crm_notes (company_id, customer_id, lead_id, body) VALUES (?, ?, ?, ?)",
        (company_id, customer_id, lead_id, body.strip()),
    )
    conn.commit()
    cursor.execute("SELECT * FROM crm_notes WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_contact_history(company_id: int, customer_id: int | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if customer_id:
        cursor.execute(
            "SELECT * FROM contact_history WHERE company_id = ? AND customer_id = ? ORDER BY created_at DESC",
            (company_id, customer_id),
        )
    else:
        cursor.execute(
            "SELECT * FROM contact_history WHERE company_id = ? ORDER BY created_at DESC",
            (company_id,),
        )
    return [dict(r) for r in cursor.fetchall()]


def add_contact_history(company_id: int, customer_id: int, channel: str, summary: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO contact_history (company_id, customer_id, channel, summary) VALUES (?, ?, ?, ?)",
        (company_id, customer_id, channel, summary.strip()),
    )
    conn.commit()
    cursor.execute("SELECT * FROM contact_history WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())

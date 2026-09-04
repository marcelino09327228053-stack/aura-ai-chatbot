"""HR data access."""

from app.database.connection import get_connection


def list_employees(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM employees WHERE company_id = ? ORDER BY name ASC",
        (company_id,),
    )
    return [dict(r) for r in cursor.fetchall()]


def create_employee(company_id: int, name: str, role: str, salary: float) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO employees (company_id, name, role, salary) VALUES (?, ?, ?, ?)",
        (company_id, name.strip(), role.strip(), salary),
    )
    conn.commit()
    cursor.execute("SELECT * FROM employees WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def count_employees(company_id: int) -> int:
    cursor = get_connection().cursor()
    cursor.execute("SELECT COUNT(*) FROM employees WHERE company_id = ?", (company_id,))
    return cursor.fetchone()[0]


def list_attendance(company_id: int, employee_id: int | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if employee_id:
        cursor.execute(
            "SELECT * FROM attendance WHERE company_id = ? AND employee_id = ? ORDER BY work_date DESC",
            (company_id, employee_id),
        )
    else:
        cursor.execute(
            "SELECT * FROM attendance WHERE company_id = ? ORDER BY work_date DESC",
            (company_id,),
        )
    return [dict(r) for r in cursor.fetchall()]


def record_attendance(company_id: int, employee_id: int, work_date: str, status: str = "present") -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO attendance (company_id, employee_id, work_date, status)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(company_id, employee_id, work_date) DO UPDATE SET status = excluded.status
        """,
        (company_id, employee_id, work_date, status),
    )
    conn.commit()
    cursor.execute(
        "SELECT * FROM attendance WHERE company_id = ? AND employee_id = ? AND work_date = ?",
        (company_id, employee_id, work_date),
    )
    return dict(cursor.fetchone())


def list_payroll(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM payroll WHERE company_id = ? ORDER BY created_at DESC",
        (company_id,),
    )
    return [dict(r) for r in cursor.fetchall()]


def create_payroll(company_id: int, employee_id: int, period: str, amount: float, status: str = "pending") -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO payroll (company_id, employee_id, period, amount, status) VALUES (?, ?, ?, ?, ?)",
        (company_id, employee_id, period, amount, status),
    )
    conn.commit()
    cursor.execute("SELECT * FROM payroll WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())

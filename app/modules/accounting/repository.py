"""Accounting data access."""

from app.database.connection import get_connection


def list_transactions(company_id: int, txn_type: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if txn_type:
        cursor.execute(
            """
            SELECT * FROM transactions
            WHERE company_id = ? AND type = ?
            ORDER BY created_at DESC
            """,
            (company_id, txn_type),
        )
    else:
        cursor.execute(
            "SELECT * FROM transactions WHERE company_id = ? ORDER BY created_at DESC",
            (company_id,),
        )
    return [dict(r) for r in cursor.fetchall()]


def create_transaction(company_id: int, txn_type: str, amount: float, description: str = "") -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO transactions (company_id, type, amount, description) VALUES (?, ?, ?, ?)",
        (company_id, txn_type, amount, description),
    )
    conn.commit()
    cursor.execute("SELECT * FROM transactions WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def get_summary(company_id: int) -> dict:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) AS income,
            COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) AS expenses
        FROM transactions WHERE company_id = ?
        """,
        (company_id,),
    )
    row = cursor.fetchone()
    income = float(row["income"])
    expenses = float(row["expenses"])
    return {
        "income": income,
        "expenses": expenses,
        "profit": income - expenses,
    }


def get_daily_report(company_id: int) -> dict:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT type, COALESCE(SUM(amount), 0) AS total
        FROM transactions
        WHERE company_id = ? AND date(created_at) = date('now')
        GROUP BY type
        """,
        (company_id,),
    )
    totals = {row["type"]: float(row["total"]) for row in cursor.fetchall()}
    income = totals.get("income", 0)
    expenses = totals.get("expense", 0)
    return {
        "date": "today",
        "income": income,
        "expenses": expenses,
        "profit": income - expenses,
    }

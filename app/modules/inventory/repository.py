"""Inventory data access."""

import sqlite3

from app.database.connection import get_connection


def list_products(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM products WHERE company_id = ? ORDER BY name ASC",
        (company_id,),
    )
    return [dict(r) for r in cursor.fetchall()]


def create_product(company_id: int, name: str, stock: int, price: float, category_id: int | None = None) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (company_id, category_id, name, stock, price) VALUES (?, ?, ?, ?, ?)",
        (company_id, category_id, name.strip(), stock, price),
    )
    conn.commit()
    cursor.execute("SELECT * FROM products WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_categories(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM product_categories WHERE company_id = ? ORDER BY name ASC",
        (company_id,),
    )
    return [dict(r) for r in cursor.fetchall()]


def create_category(company_id: int, name: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO product_categories (company_id, name) VALUES (?, ?)",
            (company_id, name.strip()),
        )
        conn.commit()
        cursor.execute("SELECT * FROM product_categories WHERE id = ?", (cursor.lastrowid,))
        return dict(cursor.fetchone())
    except sqlite3.IntegrityError:
        return None


def record_stock_movement(company_id: int, product_id: int, delta: int, reason: str = "") -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO stock_movements (company_id, product_id, delta, reason) VALUES (?, ?, ?, ?)",
        (company_id, product_id, delta, reason),
    )
    cursor.execute(
        "UPDATE products SET stock = stock + ? WHERE id = ? AND company_id = ?",
        (delta, product_id, company_id),
    )
    conn.commit()
    cursor.execute("SELECT * FROM stock_movements WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_stock_movements(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM stock_movements WHERE company_id = ? ORDER BY created_at DESC",
        (company_id,),
    )
    return [dict(r) for r in cursor.fetchall()]


def total_stock_units(company_id: int) -> int:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT COALESCE(SUM(stock), 0) FROM products WHERE company_id = ?",
        (company_id,),
    )
    return int(cursor.fetchone()[0])

"""Commerce Network data access."""

import json
import secrets
from datetime import datetime, timedelta

from app.cloud.security import encrypt_value
from app.infrastructure.database import get_connection


def log_commerce_action(company_id: int, action: str, user_id: int | None = None, details: str = "") -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO commerce_audit (company_id, user_id, action, details) VALUES (?,?,?,?)",
        (company_id, user_id, action, details[:500]),
    )
    conn.commit()


def list_audit(company_id: int, limit: int = 50) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM commerce_audit WHERE company_id = ? ORDER BY created_at DESC LIMIT ?",
        (company_id, limit),
    )
    return [dict(r) for r in cursor.fetchall()]


# ── Products / Listings ───────────────────────────────────────────────────────

def create_product(company_id: int, data: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO commerce_products
            (company_id, listing_type, name, description, price, currency, category, stock, status)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (
            company_id,
            data.get("listing_type", "product"),
            data.get("name", ""),
            data.get("description", ""),
            data.get("price", 0),
            data.get("currency", "PHP"),
            data.get("category", "general"),
            data.get("stock", 0),
            data.get("status", "active"),
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM commerce_products WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_products(company_id: int, listing_type: str | None = None, status: str = "active") -> list[dict]:
    cursor = get_connection().cursor()
    if listing_type:
        cursor.execute(
            "SELECT * FROM commerce_products WHERE company_id = ? AND listing_type = ? AND status = ? ORDER BY created_at DESC",
            (company_id, listing_type, status),
        )
    else:
        cursor.execute(
            "SELECT * FROM commerce_products WHERE company_id = ? AND status = ? ORDER BY created_at DESC",
            (company_id, status),
        )
    return [dict(r) for r in cursor.fetchall()]


def get_product(company_id: int, product_id: int) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM commerce_products WHERE id = ? AND company_id = ?",
        (product_id, company_id),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def update_product_stock(company_id: int, product_id: int, stock: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE commerce_products SET stock = ? WHERE id = ? AND company_id = ?",
        (stock, product_id, company_id),
    )
    conn.commit()
    return get_product(company_id, product_id)


# ── Reviews ───────────────────────────────────────────────────────────────────

def add_review(company_id: int, product_id: int, customer_name: str, rating: int, comment: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    rating = max(1, min(5, rating))
    cursor.execute(
        """
        INSERT INTO commerce_reviews (company_id, product_id, customer_name, rating, comment)
        VALUES (?,?,?,?,?)
        """,
        (company_id, product_id, customer_name, rating, comment[:1000]),
    )
    conn.commit()
    cursor.execute("SELECT * FROM commerce_reviews WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_reviews(company_id: int, product_id: int | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if product_id:
        cursor.execute(
            "SELECT * FROM commerce_reviews WHERE company_id = ? AND product_id = ? ORDER BY created_at DESC",
            (company_id, product_id),
        )
    else:
        cursor.execute(
            "SELECT * FROM commerce_reviews WHERE company_id = ? ORDER BY created_at DESC LIMIT 50",
            (company_id,),
        )
    return [dict(r) for r in cursor.fetchall()]


def product_avg_rating(company_id: int, product_id: int) -> dict:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT AVG(rating) as avg_rating, COUNT(*) as review_count FROM commerce_reviews WHERE company_id = ? AND product_id = ?",
        (company_id, product_id),
    )
    row = cursor.fetchone()
    return {
        "avg_rating": round(row["avg_rating"] or 0, 2),
        "review_count": row["review_count"] or 0,
    }


# ── Orders ────────────────────────────────────────────────────────────────────

def _order_number() -> str:
    return f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"


def create_order(company_id: int, data: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    items = data.get("items", [])
    subtotal = sum(i.get("price", 0) * i.get("quantity", 1) for i in items)
    tax = round(subtotal * data.get("tax_rate", 0.12), 2)
    total = round(subtotal + tax, 2)
    order_number = _order_number()
    cursor.execute(
        """
        INSERT INTO commerce_orders
            (company_id, order_number, customer_name, customer_email, items, subtotal, tax, total, status, payment_status)
        VALUES (?,?,?,?,?,?,?,?,?,?)
        """,
        (
            company_id,
            order_number,
            data.get("customer_name", ""),
            data.get("customer_email", ""),
            json.dumps(items),
            subtotal,
            tax,
            total,
            data.get("status", "pending"),
            data.get("payment_status", "unpaid"),
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM commerce_orders WHERE id = ?", (cursor.lastrowid,))
    row = dict(cursor.fetchone())
    row["items"] = items
    return row


def list_orders(company_id: int, status: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if status:
        cursor.execute(
            "SELECT * FROM commerce_orders WHERE company_id = ? AND status = ? ORDER BY created_at DESC",
            (company_id, status),
        )
    else:
        cursor.execute(
            "SELECT * FROM commerce_orders WHERE company_id = ? ORDER BY created_at DESC",
            (company_id,),
        )
    rows = []
    for r in cursor.fetchall():
        data = dict(r)
        try:
            data["items"] = json.loads(data.get("items") or "[]")
        except Exception:
            data["items"] = []
        rows.append(data)
    return rows


def get_order(company_id: int, order_id: int) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM commerce_orders WHERE id = ? AND company_id = ?",
        (order_id, company_id),
    )
    row = cursor.fetchone()
    if not row:
        return None
    data = dict(row)
    try:
        data["items"] = json.loads(data.get("items") or "[]")
    except Exception:
        data["items"] = []
    return data


def update_order_status(company_id: int, order_id: int, status: str = None, payment_status: str = None) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    if status:
        cursor.execute(
            "UPDATE commerce_orders SET status = ? WHERE id = ? AND company_id = ?",
            (status, order_id, company_id),
        )
    if payment_status:
        cursor.execute(
            "UPDATE commerce_orders SET payment_status = ? WHERE id = ? AND company_id = ?",
            (payment_status, order_id, company_id),
        )
    conn.commit()
    return get_order(company_id, order_id)


# ── Shipments ─────────────────────────────────────────────────────────────────

def create_shipment(company_id: int, data: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    tracking = data.get("tracking_number") or f"TRK-{secrets.token_hex(5).upper()}"
    cursor.execute(
        """
        INSERT INTO commerce_shipments
            (company_id, order_id, tracking_number, carrier, origin, destination, status, estimated_delivery)
        VALUES (?,?,?,?,?,?,?,?)
        """,
        (
            company_id,
            data.get("order_id"),
            tracking,
            data.get("carrier", "standard"),
            data.get("origin", ""),
            data.get("destination", ""),
            data.get("status", "pending"),
            data.get("estimated_delivery", (datetime.utcnow() + timedelta(days=5)).strftime("%Y-%m-%d")),
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM commerce_shipments WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_shipments(company_id: int, status: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if status:
        cursor.execute(
            "SELECT * FROM commerce_shipments WHERE company_id = ? AND status = ? ORDER BY created_at DESC",
            (company_id, status),
        )
    else:
        cursor.execute(
            "SELECT * FROM commerce_shipments WHERE company_id = ? ORDER BY created_at DESC",
            (company_id,),
        )
    return [dict(r) for r in cursor.fetchall()]


def update_shipment_status(company_id: int, tracking_number: str, status: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE commerce_shipments SET status = ?, updated_at = datetime('now')
        WHERE tracking_number = ? AND company_id = ?
        """,
        (status, tracking_number, company_id),
    )
    conn.commit()
    cursor.execute(
        "SELECT * FROM commerce_shipments WHERE tracking_number = ? AND company_id = ?",
        (tracking_number, company_id),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


# ── Warehouses ────────────────────────────────────────────────────────────────

def create_warehouse(company_id: int, data: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO commerce_warehouses (company_id, name, location, capacity, current_stock, status)
        VALUES (?,?,?,?,?,?)
        """,
        (
            company_id,
            data.get("name", ""),
            data.get("location", ""),
            data.get("capacity", 1000),
            data.get("current_stock", 0),
            data.get("status", "active"),
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM commerce_warehouses WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_warehouses(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM commerce_warehouses WHERE company_id = ? ORDER BY created_at DESC",
        (company_id,),
    )
    return [dict(r) for r in cursor.fetchall()]


def update_warehouse_stock(company_id: int, warehouse_id: int, current_stock: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE commerce_warehouses SET current_stock = ? WHERE id = ? AND company_id = ?",
        (current_stock, warehouse_id, company_id),
    )
    conn.commit()
    cursor.execute(
        "SELECT * FROM commerce_warehouses WHERE id = ? AND company_id = ?",
        (warehouse_id, company_id),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


# ── Payments ──────────────────────────────────────────────────────────────────

def create_payment(company_id: int, data: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    payment_ref = data.get("payment_ref") or f"PAY-{secrets.token_hex(6).upper()}"
    meta = encrypt_value(json.dumps(data.get("meta", {})))
    cursor.execute(
        """
        INSERT INTO commerce_payments
            (company_id, order_id, payment_ref, amount, currency, method, status, fraud_score, encrypted_meta)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (
            company_id,
            data.get("order_id"),
            payment_ref,
            data.get("amount", 0),
            data.get("currency", "PHP"),
            data.get("method", "online"),
            data.get("status", "pending"),
            data.get("fraud_score", 0),
            meta,
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM commerce_payments WHERE id = ?", (cursor.lastrowid,))
    row = dict(cursor.fetchone())
    row.pop("encrypted_meta", None)
    return row


def list_payments(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT id, company_id, order_id, payment_ref, amount, currency, method, status, fraud_score, created_at
        FROM commerce_payments WHERE company_id = ? ORDER BY created_at DESC
        """,
        (company_id,),
    )
    return [dict(r) for r in cursor.fetchall()]


def update_payment_status(company_id: int, payment_ref: str, status: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE commerce_payments SET status = ? WHERE payment_ref = ? AND company_id = ?",
        (status, payment_ref, company_id),
    )
    conn.commit()
    cursor.execute(
        """
        SELECT id, company_id, order_id, payment_ref, amount, currency, method, status, fraud_score, created_at
        FROM commerce_payments WHERE payment_ref = ? AND company_id = ?
        """,
        (payment_ref, company_id),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


# ── Invoices ──────────────────────────────────────────────────────────────────

def create_invoice(company_id: int, data: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    invoice_number = data.get("invoice_number") or f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"
    line_items = data.get("line_items", [])
    subtotal = sum(i.get("amount", 0) for i in line_items)
    tax = round(subtotal * data.get("tax_rate", 0.12), 2)
    total = round(subtotal + tax, 2)
    due = data.get("due_date") or (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")
    cursor.execute(
        """
        INSERT INTO commerce_invoices
            (company_id, invoice_number, order_id, customer_name, line_items, subtotal, tax, total, status, due_date)
        VALUES (?,?,?,?,?,?,?,?,?,?)
        """,
        (
            company_id,
            invoice_number,
            data.get("order_id"),
            data.get("customer_name", ""),
            json.dumps(line_items),
            subtotal,
            tax,
            total,
            data.get("status", "sent"),
            due,
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM commerce_invoices WHERE id = ?", (cursor.lastrowid,))
    row = dict(cursor.fetchone())
    row["line_items"] = line_items
    return row


def list_invoices(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM commerce_invoices WHERE company_id = ? ORDER BY created_at DESC",
        (company_id,),
    )
    rows = []
    for r in cursor.fetchall():
        data = dict(r)
        try:
            data["line_items"] = json.loads(data.get("line_items") or "[]")
        except Exception:
            data["line_items"] = []
        rows.append(data)
    return rows


# ── Subscriptions ─────────────────────────────────────────────────────────────

def create_subscription(company_id: int, data: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    next_bill = data.get("next_billing_date") or (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")
    cursor.execute(
        """
        INSERT INTO commerce_subscriptions
            (company_id, customer_name, plan_name, amount, billing_cycle, status, next_billing_date)
        VALUES (?,?,?,?,?,?,?)
        """,
        (
            company_id,
            data.get("customer_name", ""),
            data.get("plan_name", ""),
            data.get("amount", 0),
            data.get("billing_cycle", "monthly"),
            data.get("status", "active"),
            next_bill,
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM commerce_subscriptions WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_subscriptions(company_id: int) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM commerce_subscriptions WHERE company_id = ? ORDER BY created_at DESC",
        (company_id,),
    )
    return [dict(r) for r in cursor.fetchall()]


# ── Contracts ─────────────────────────────────────────────────────────────────

def create_contract(company_id: int, data: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO commerce_contracts
            (company_id, title, template_type, parties, content, status, renewal_date)
        VALUES (?,?,?,?,?,?,?)
        """,
        (
            company_id,
            data.get("title", ""),
            data.get("template_type", "service"),
            json.dumps(data.get("parties", [])),
            data.get("content", ""),
            data.get("status", "draft"),
            data.get("renewal_date", ""),
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM commerce_contracts WHERE id = ?", (cursor.lastrowid,))
    row = dict(cursor.fetchone())
    try:
        row["parties"] = json.loads(row.get("parties") or "[]")
    except Exception:
        row["parties"] = []
    return row


def list_contracts(company_id: int, archived: bool = False) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM commerce_contracts WHERE company_id = ? AND archived = ? ORDER BY created_at DESC",
        (company_id, int(archived)),
    )
    rows = []
    for r in cursor.fetchall():
        data = dict(r)
        try:
            data["parties"] = json.loads(data.get("parties") or "[]")
        except Exception:
            data["parties"] = []
        rows.append(data)
    return rows


def approve_contract(company_id: int, contract_id: int, user_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE commerce_contracts SET status = 'approved', approved_by = ? WHERE id = ? AND company_id = ?",
        (user_id, contract_id, company_id),
    )
    conn.commit()
    cursor.execute(
        "SELECT * FROM commerce_contracts WHERE id = ? AND company_id = ?",
        (contract_id, company_id),
    )
    row = cursor.fetchone()
    if not row:
        return None
    data = dict(row)
    try:
        data["parties"] = json.loads(data.get("parties") or "[]")
    except Exception:
        data["parties"] = []
    return data


def archive_contract(company_id: int, contract_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE commerce_contracts SET archived = 1, status = 'archived' WHERE id = ? AND company_id = ?",
        (contract_id, company_id),
    )
    conn.commit()
    cursor.execute(
        "SELECT * FROM commerce_contracts WHERE id = ? AND company_id = ?",
        (contract_id, company_id),
    )
    row = cursor.fetchone()
    return dict(row) if row else None

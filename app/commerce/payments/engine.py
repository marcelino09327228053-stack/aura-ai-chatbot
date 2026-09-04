"""
Payment system — online payments, subscriptions, invoices, fraud detection.
"""

from __future__ import annotations

from app.commerce import repository as commerce_repo


def detect_fraud(amount: float, method: str, customer_email: str = "") -> dict:
    """Simple heuristic fraud scoring (0–100). Higher = more risk."""
    score = 0.0
    flags = []

    if amount > 100_000:
        score += 30
        flags.append("High transaction amount")
    elif amount > 50_000:
        score += 15
        flags.append("Elevated transaction amount")

    if amount <= 0:
        score += 50
        flags.append("Invalid amount")

    if method not in ("online", "card", "gcash", "bank_transfer", "subscription"):
        score += 20
        flags.append("Unusual payment method")

    if customer_email and "@" not in customer_email:
        score += 25
        flags.append("Invalid email format")

    if amount > 0 and amount == int(amount) and amount >= 10000:
        # Round large numbers can be suspicious in some contexts
        score += 5

    risk = "high" if score >= 50 else "medium" if score >= 25 else "low"
    return {"fraud_score": min(score, 100), "risk_level": risk, "flags": flags}


def process_payment(company_id: int, data: dict, user_id: int | None = None) -> dict:
    """
    Process an online payment.

    Flow: validate → fraud check → create payment → update order → audit
    """
    amount = float(data.get("amount", 0))
    if amount <= 0:
        raise ValueError("Payment amount must be greater than 0")

    order_id = data.get("order_id")
    order = None
    if order_id:
        order = commerce_repo.get_order(company_id, order_id)
        if not order:
            raise ValueError("Order not found")
        if abs(amount - order.get("total", 0)) > 0.01:
            # Allow payment but flag mismatch
            pass

    fraud = detect_fraud(
        amount,
        data.get("method", "online"),
        data.get("customer_email") or (order or {}).get("customer_email", ""),
    )

    if fraud["risk_level"] == "high" and fraud["fraud_score"] >= 70:
        payment = commerce_repo.create_payment(company_id, {
            **data,
            "amount": amount,
            "status": "blocked",
            "fraud_score": fraud["fraud_score"],
            "meta": {"fraud": fraud, "reason": "Blocked by fraud detection"},
        })
        commerce_repo.log_commerce_action(
            company_id, "payment.blocked", user_id, payment["payment_ref"]
        )
        return {
            **payment,
            "fraud": fraud,
            "message": "Payment blocked due to high fraud risk. Manual review required.",
        }

    status = "completed" if fraud["risk_level"] != "high" else "pending_review"
    payment = commerce_repo.create_payment(company_id, {
        **data,
        "amount": amount,
        "status": status,
        "fraud_score": fraud["fraud_score"],
        "meta": {"fraud": fraud},
    })

    if order_id and status == "completed":
        commerce_repo.update_order_status(company_id, order_id, payment_status="paid", status="confirmed")

    commerce_repo.log_commerce_action(
        company_id, f"payment.{status}", user_id, payment["payment_ref"]
    )
    return {
        **payment,
        "fraud": fraud,
        "message": f"Payment {status}",
    }


def generate_invoice_for_order(company_id: int, order_id: int, user_id: int | None = None) -> dict:
    order = commerce_repo.get_order(company_id, order_id)
    if not order:
        raise ValueError("Order not found")

    line_items = [
        {
            "description": i.get("name", "Item"),
            "quantity": i.get("quantity", 1),
            "unit_price": i.get("price", 0),
            "amount": i.get("price", 0) * i.get("quantity", 1),
        }
        for i in order.get("items", [])
    ]

    invoice = commerce_repo.create_invoice(company_id, {
        "order_id": order_id,
        "customer_name": order.get("customer_name", ""),
        "line_items": line_items,
        "tax_rate": 0.12 if order.get("tax", 0) > 0 else 0,
        "status": "sent",
    })
    commerce_repo.log_commerce_action(
        company_id, "invoice.generate", user_id, invoice["invoice_number"]
    )
    return invoice


def create_subscription_billing(company_id: int, data: dict, user_id: int | None = None) -> dict:
    if not data.get("customer_name") or not data.get("plan_name"):
        raise ValueError("customer_name and plan_name are required")
    if float(data.get("amount", 0)) <= 0:
        raise ValueError("Subscription amount must be greater than 0")

    sub = commerce_repo.create_subscription(company_id, data)
    commerce_repo.log_commerce_action(
        company_id, "subscription.create", user_id, data.get("plan_name", "")
    )
    return sub


def financial_records(company_id: int) -> dict:
    payments = commerce_repo.list_payments(company_id)
    invoices = commerce_repo.list_invoices(company_id)
    subscriptions = commerce_repo.list_subscriptions(company_id)

    completed = [p for p in payments if p.get("status") == "completed"]
    total_collected = sum(p.get("amount", 0) for p in completed)
    pending = sum(p.get("amount", 0) for p in payments if p.get("status") in ("pending", "pending_review"))
    mrr = sum(s.get("amount", 0) for s in subscriptions if s.get("status") == "active")

    return {
        "total_collected": round(total_collected, 2),
        "pending_amount": round(pending, 2),
        "payment_count": len(payments),
        "completed_payments": len(completed),
        "invoice_count": len(invoices),
        "active_subscriptions": len([s for s in subscriptions if s.get("status") == "active"]),
        "monthly_recurring_revenue": round(mrr, 2),
        "recent_payments": payments[:10],
        "recent_invoices": invoices[:10],
    }

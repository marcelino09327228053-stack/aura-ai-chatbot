"""
Commerce analytics — sales performance, customer behavior, market trends, revenue reports.
"""

from __future__ import annotations

from app.commerce import repository as commerce_repo
from app.commerce.marketplace import engine as marketplace_engine


def sales_performance(company_id: int) -> dict:
    orders = commerce_repo.list_orders(company_id)
    completed = [o for o in orders if o.get("status") in ("completed", "confirmed")]
    total_revenue = sum(o.get("total", 0) for o in completed)
    avg_order = total_revenue / max(len(completed), 1)

    by_status = {}
    for o in orders:
        st = o.get("status", "pending")
        by_status[st] = by_status.get(st, 0) + 1

    return {
        "total_orders": len(orders),
        "completed_orders": len(completed),
        "total_revenue": round(total_revenue, 2),
        "average_order_value": round(avg_order, 2),
        "conversion_rate_pct": round(len(completed) / max(len(orders), 1) * 100, 1),
        "orders_by_status": by_status,
    }


def customer_behavior(company_id: int) -> dict:
    orders = commerce_repo.list_orders(company_id)
    reviews = commerce_repo.list_reviews(company_id)

    customers = {}
    for o in orders:
        name = o.get("customer_name") or "Anonymous"
        if name not in customers:
            customers[name] = {"orders": 0, "spent": 0}
        customers[name]["orders"] += 1
        customers[name]["spent"] += o.get("total", 0)

    top_customers = sorted(
        [{"name": k, **v} for k, v in customers.items()],
        key=lambda x: x["spent"],
        reverse=True,
    )[:5]

    avg_rating = (
        round(sum(r.get("rating", 0) for r in reviews) / len(reviews), 2) if reviews else 0
    )

    return {
        "unique_customers": len(customers),
        "repeat_customers": len([c for c in customers.values() if c["orders"] > 1]),
        "top_customers": top_customers,
        "average_review_rating": avg_rating,
        "total_reviews": len(reviews),
        "insights": [
            f"{len(customers)} unique customers tracked",
            f"{len([c for c in customers.values() if c['orders'] > 1])} repeat buyers",
            f"Average satisfaction: {avg_rating}/5" if reviews else "No reviews yet",
        ],
    }


def market_trends(company_id: int) -> dict:
    products = commerce_repo.list_products(company_id)
    orders = commerce_repo.list_orders(company_id)

    category_counts: dict[str, int] = {}
    for p in products:
        cat = p.get("category", "general")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    # Product demand from order items
    demand: dict[str, int] = {}
    for o in orders:
        for item in o.get("items", []):
            name = item.get("name", "Unknown")
            demand[name] = demand.get(name, 0) + item.get("quantity", 1)

    top_demanded = sorted(
        [{"product": k, "units": v} for k, v in demand.items()],
        key=lambda x: x["units"],
        reverse=True,
    )[:5]

    return {
        "categories": category_counts,
        "top_demanded_products": top_demanded,
        "active_listings": len(products),
        "trends": [
            "Premium products gaining demand" if any(p.get("price", 0) > 1000 for p in products) else "Focus on mid-range pricing",
            "Expand best-selling categories" if top_demanded else "Build product catalogue",
            "Encourage customer reviews to boost conversion",
        ],
    }


def revenue_report(company_id: int) -> dict:
    sales = sales_performance(company_id)
    payments = commerce_repo.list_payments(company_id)
    subscriptions = commerce_repo.list_subscriptions(company_id)

    paid = sum(p.get("amount", 0) for p in payments if p.get("status") == "completed")
    mrr = sum(s.get("amount", 0) for s in subscriptions if s.get("status") == "active")

    return {
        "order_revenue": sales["total_revenue"],
        "collected_payments": round(paid, 2),
        "monthly_recurring_revenue": round(mrr, 2),
        "projected_annual_mrr": round(mrr * 12, 2),
        "average_order_value": sales["average_order_value"],
        "payment_collection_rate_pct": round(
            paid / max(sales["total_revenue"], 1) * 100, 1
        ) if sales["total_revenue"] else 0,
        "summary": (
            f"Order revenue ₱{sales['total_revenue']:,.0f}; "
            f"collected ₱{paid:,.0f}; MRR ₱{mrr:,.0f}"
        ),
    }


def full_commerce_report(company_id: int) -> dict:
    commerce_repo.log_commerce_action(company_id, "analytics.report")
    return {
        "sales_performance": sales_performance(company_id),
        "customer_behavior": customer_behavior(company_id),
        "market_trends": market_trends(company_id),
        "revenue": revenue_report(company_id),
        "marketplace": marketplace_engine.marketplace_summary(company_id),
    }

"""
Optimization engine — expenses, workflow, inventory, customer support.
"""

from app.modules.accounting import repository as accounting_repo
from app.modules.crm import repository as crm_repo
from app.modules.hr import repository as hr_repo
from app.modules.inventory import repository as inventory_repo


def optimize_expenses(company_id: int) -> dict:
    summary = accounting_repo.get_summary(company_id)
    txns = accounting_repo.list_transactions(company_id)
    income = summary.get("income", 0)
    expenses = summary.get("expenses", 0)

    expense_items = [t for t in txns if t.get("type") == "expense"]
    categories: dict[str, float] = {}
    for t in expense_items:
        cat = t.get("description", "Other")[:30]
        categories[cat] = categories.get(cat, 0) + t.get("amount", 0)

    target_savings = round(expenses * 0.10, 2)  # conservative 10% target
    ratio = round(expenses / max(income, 1) * 100, 1)

    return {
        "current_expenses": expenses,
        "current_income": income,
        "expense_to_income_ratio": ratio,
        "potential_savings": target_savings,
        "top_expense_categories": sorted(
            [{"category": k, "amount": v} for k, v in categories.items()],
            key=lambda x: x["amount"],
            reverse=True,
        )[:5],
        "recommendations": [
            f"Target {ratio - 10:.0f}% expense ratio (currently {ratio}%)",
            f"Potential savings: ₱{target_savings}",
        ],
    }


def optimize_workflow(company_id: int) -> dict:
    leads = crm_repo.list_leads(company_id)
    employees = hr_repo.list_employees(company_id)
    attendance = hr_repo.list_attendance(company_id)

    open_leads = [l for l in leads if l.get("status") in ("new", "contacted")]
    conversion_rate = len([l for l in leads if l.get("status") == "converted"]) / max(len(leads), 1)

    bottlenecks = []
    if open_leads:
        bottlenecks.append(f"{len(open_leads)} leads stuck in pipeline")
    if len(employees) > 0 and len(attendance) < len(employees):
        bottlenecks.append("Incomplete attendance records")

    return {
        "open_pipeline_leads": len(open_leads),
        "conversion_rate": f"{round(conversion_rate * 100, 1)}%",
        "employee_count": len(employees),
        "bottlenecks": bottlenecks,
        "optimizations": [
            "Automate follow-up messages for open leads",
            "Set daily attendance check-in reminders",
            "Use workflow engine for standard processes",
        ],
    }


def optimize_inventory(company_id: int) -> dict:
    products = inventory_repo.list_products(company_id)
    if not products:
        return {"status": "no_products", "suggestions": []}

    total = sum(p.get("stock", 0) for p in products)
    avg = total / len(products)
    overstock = [p for p in products if p.get("stock", 0) > avg * 2]
    understock = [p for p in products if 0 < p.get("stock", 0) < max(avg * 0.2, 3)]
    zero_stock = [p for p in products if p.get("stock", 0) == 0]

    return {
        "total_units": total,
        "average_stock_per_product": round(avg, 1),
        "overstocked_items": len(overstock),
        "understocked_items": len(understock),
        "out_of_stock": len(zero_stock),
        "suggestions": [
            f"Reduce stock for {len(overstock)} overstocked items to free up capital",
            f"Reorder {len(understock)} items approaching stockout",
            f"Immediate reorder needed for {len(zero_stock)} out-of-stock items",
        ],
        "out_of_stock_list": [{"name": p["name"]} for p in zero_stock[:5]],
    }


def optimize_support(company_id: int) -> dict:
    from app.infrastructure.database import get_connection
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT role, COUNT(*) as cnt FROM conversations
        WHERE company_id = ? GROUP BY role
        """,
        (company_id,),
    )
    by_role = {r["role"]: r["cnt"] for r in cursor.fetchall()}
    total = sum(by_role.values())
    user_msgs = by_role.get("user", 0)
    bot_msgs = by_role.get("assistant", 0)
    resolution_rate = round(bot_msgs / max(user_msgs, 1) * 100, 1)

    return {
        "total_messages": total,
        "user_messages": user_msgs,
        "bot_responses": bot_msgs,
        "bot_resolution_rate": resolution_rate,
        "suggestions": [
            "Add more FAQs to cover unanswered questions",
            "Enable Support Agent for 24/7 automated responses",
            "Review recent conversations for common issues",
        ] if resolution_rate < 90 else [
            "Support is performing well — maintain FAQ database",
        ],
    }


def run_all_optimizations(company_id: int) -> dict:
    return {
        "expenses": optimize_expenses(company_id),
        "workflow": optimize_workflow(company_id),
        "inventory": optimize_inventory(company_id),
        "support": optimize_support(company_id),
    }

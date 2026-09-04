"""
Recommendation engine — products, marketing, cost reduction, employees.

Each recommender pulls real data and emits scored action items.
"""

from app.intelligence import repository as intel_repo
from app.modules.accounting import repository as accounting_repo
from app.modules.crm import repository as crm_repo
from app.modules.hr import repository as hr_repo
from app.modules.inventory import repository as inventory_repo


def _save(company_id: int, category: str, title: str, description: str, score: float) -> dict:
    return intel_repo.save_recommendation(company_id, category, title, description, score)


# ── product recommendations ───────────────────────────────────────────────────

def recommend_products(company_id: int) -> list[dict]:
    products = inventory_repo.list_products(company_id)
    recs = []

    if not products:
        recs.append(_save(
            company_id, "products",
            "Add your first products",
            "No products in inventory. Add products to enable sales tracking and forecasting.",
            0.9,
        ))
        return recs

    low = [p for p in products if p.get("stock", 0) < 5]
    for p in low[:3]:
        recs.append(_save(
            company_id, "products",
            f"Restock: {p['name']}",
            f"Only {p['stock']} units remaining. Restocking now prevents lost sales.",
            0.85,
        ))

    high_value = sorted(products, key=lambda p: p.get("price", 0), reverse=True)[:2]
    for p in high_value:
        recs.append(_save(
            company_id, "products",
            f"Feature {p['name']} in promotions",
            f"High-value item (₱{p.get('price', 0)}). Promoting it can increase average order value.",
            0.7,
        ))
    return recs


# ── marketing recommendations ─────────────────────────────────────────────────

def recommend_marketing(company_id: int) -> list[dict]:
    leads = crm_repo.list_leads(company_id)
    customers = crm_repo.count_customers(company_id)
    recs = []

    cold_leads = [l for l in leads if l.get("status") == "new"]
    if cold_leads:
        recs.append(_save(
            company_id, "marketing",
            f"Follow up {len(cold_leads)} uncontacted leads",
            "These leads have not been contacted. A follow-up within 24 hours increases conversion by 3×.",
            0.88,
        ))

    if customers < 10:
        recs.append(_save(
            company_id, "marketing",
            "Launch a referral campaign",
            "With fewer than 10 customers, a referral incentive can double your customer base quickly.",
            0.8,
        ))
    else:
        recs.append(_save(
            company_id, "marketing",
            "Run a loyalty reward campaign",
            f"You have {customers} customers. A loyalty program can increase repeat purchases by 20–30%.",
            0.75,
        ))

    return recs


# ── cost reduction recommendations ───────────────────────────────────────────

def recommend_cost_reduction(company_id: int) -> list[dict]:
    summary = accounting_repo.get_summary(company_id)
    recs = []
    income = summary.get("income", 0)
    expenses = summary.get("expenses", 0)
    profit = summary.get("profit", income - expenses)

    if expenses > 0 and income > 0:
        expense_ratio = expenses / income
        if expense_ratio > 0.7:
            recs.append(_save(
                company_id, "cost_reduction",
                "Expense ratio too high",
                f"Expenses are {round(expense_ratio * 100)}% of income. Target below 60% for healthy margins.",
                0.92,
            ))

    txns = accounting_repo.list_transactions(company_id)
    expense_txns = [t for t in txns if t.get("type") == "expense"]
    if expense_txns:
        largest = sorted(expense_txns, key=lambda t: t.get("amount", 0), reverse=True)[:2]
        for t in largest:
            recs.append(_save(
                company_id, "cost_reduction",
                f"Review expense: {t.get('description', 'Large expense')}",
                f"₱{t.get('amount', 0)} — review if this cost can be reduced or eliminated.",
                0.65,
            ))

    if profit < 0:
        recs.append(_save(
            company_id, "cost_reduction",
            "Business is running at a loss",
            f"Current profit: ₱{profit}. Immediate cost audit recommended.",
            0.95,
        ))

    return recs


# ── employee recommendations ──────────────────────────────────────────────────

def recommend_employees(company_id: int) -> list[dict]:
    employees = hr_repo.list_employees(company_id)
    payroll = hr_repo.list_payroll(company_id)
    recs = []

    if not employees:
        recs.append(_save(
            company_id, "employees",
            "Add employee records",
            "No employees tracked. Adding records enables attendance, payroll, and HR analytics.",
            0.6,
        ))
        return recs

    if payroll:
        total_payroll = sum(p.get("amount", p.get("net_pay", 0)) for p in payroll)
        recs.append(_save(
            company_id, "employees",
            "Review payroll efficiency",
            f"Total payroll: ₱{total_payroll}. Ensure payroll aligns with revenue targets.",
            0.7,
        ))

    if len(employees) > 5:
        recs.append(_save(
            company_id, "employees",
            "Consider performance incentive program",
            f"With {len(employees)} employees, a performance bonus system can improve productivity.",
            0.65,
        ))

    return recs


# ── combined ──────────────────────────────────────────────────────────────────

def run_all_recommendations(company_id: int) -> dict:
    intel_repo.log_intelligence_action(company_id, "recommendations.run_all")
    return {
        "products": recommend_products(company_id),
        "marketing": recommend_marketing(company_id),
        "cost_reduction": recommend_cost_reduction(company_id),
        "employees": recommend_employees(company_id),
    }

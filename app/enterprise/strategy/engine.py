"""
Strategic engine — goal tracking, KPI monitoring, long-term planning,
and AI-powered business recommendations.
"""

from __future__ import annotations

from app.enterprise import repository as ent_repo
from app.modules.accounting import repository as accounting_repo
from app.modules.crm import repository as crm_repo
from app.modules.hr import repository as hr_repo
from app.modules.inventory import repository as inventory_repo


# ── KPI auto-generation ───────────────────────────────────────────────────────

def refresh_kpis(company_id: int) -> list[dict]:
    """Pull live data from all modules and record current KPI snapshot."""
    summary = accounting_repo.get_summary(company_id)
    customers = crm_repo.count_customers(company_id)
    leads = crm_repo.list_leads(company_id)
    employees = hr_repo.list_employees(company_id)
    products = inventory_repo.list_products(company_id)

    income = summary.get("income", 0)
    expenses = summary.get("expenses", 0)
    profit = summary.get("profit", income - expenses)
    conversion_rate = (
        len([l for l in leads if l.get("status") == "converted"]) / max(len(leads), 1) * 100
    )
    avg_ticket = income / max(customers, 1)
    expense_ratio = expenses / max(income, 1) * 100 if income > 0 else 0

    kpi_data = [
        {"name": "Monthly Revenue", "category": "financial", "value": income, "target": income * 1.1, "unit": "PHP", "trend": "stable"},
        {"name": "Net Profit", "category": "financial", "value": profit, "target": max(profit * 1.15, 0), "unit": "PHP", "trend": "up" if profit > 0 else "down"},
        {"name": "Expense Ratio", "category": "financial", "value": round(expense_ratio, 1), "target": 60.0, "unit": "%", "trend": "down" if expense_ratio > 60 else "stable"},
        {"name": "Total Customers", "category": "growth", "value": customers, "target": customers * 1.2, "unit": "customers", "trend": "up"},
        {"name": "Lead Conversion Rate", "category": "sales", "value": round(conversion_rate, 1), "target": 30.0, "unit": "%", "trend": "stable"},
        {"name": "Average Customer Value", "category": "sales", "value": round(avg_ticket, 2), "target": avg_ticket * 1.1, "unit": "PHP", "trend": "stable"},
        {"name": "Employee Count", "category": "hr", "value": len(employees), "target": len(employees), "unit": "people", "trend": "stable"},
        {"name": "Product SKUs", "category": "operations", "value": len(products), "target": len(products), "unit": "SKUs", "trend": "stable"},
    ]

    recorded = []
    for kpi in kpi_data:
        recorded.append(ent_repo.record_kpi(company_id, kpi))

    ent_repo.log_enterprise_action(company_id, "kpis.refresh", details=f"{len(recorded)} KPIs recorded")
    return recorded


# ── Goal scoring ──────────────────────────────────────────────────────────────

def score_goals(company_id: int) -> list[dict]:
    """Attach progress percentage to each goal."""
    goals = ent_repo.list_goals(company_id, status="active")
    scored = []
    for g in goals:
        target = g.get("target_value", 0)
        current = g.get("current_value", 0)
        pct = round(current / max(target, 1) * 100, 1)
        scored.append({
            **g,
            "progress_pct": min(pct, 100),
            "on_track": pct >= 70,
            "remaining": round(max(target - current, 0), 2),
        })
    return sorted(scored, key=lambda g: g["progress_pct"], reverse=True)


# ── Strategic recommendations ─────────────────────────────────────────────────

def generate_strategic_recommendations(company_id: int) -> list[dict]:
    summary = accounting_repo.get_summary(company_id)
    customers = crm_repo.count_customers(company_id)
    leads = crm_repo.list_leads(company_id)
    employees = hr_repo.list_employees(company_id)
    products = inventory_repo.list_products(company_id)
    goals = ent_repo.list_goals(company_id, status="active")

    income = summary.get("income", 0)
    expenses = summary.get("expenses", 0)
    profit = income - expenses
    recs = []

    # Financial health
    if profit < 0:
        recs.append({"priority": "critical", "category": "financial", "title": "Restore Profitability",
                     "description": "Business is operating at a loss. Immediate cost review and revenue acceleration required.",
                     "action": "Audit top 3 expense categories; pause non-essential spending."})
    elif expenses / max(income, 1) > 0.75:
        recs.append({"priority": "high", "category": "financial", "title": "Improve Profit Margins",
                     "description": f"Expense ratio is {round(expenses/max(income,1)*100)}%. Industry benchmark is 60%.",
                     "action": "Renegotiate supplier contracts and review SaaS subscriptions."})

    # Growth
    if customers < 20:
        recs.append({"priority": "high", "category": "growth", "title": "Accelerate Customer Acquisition",
                     "description": "Under 20 customers — growth is the top strategic priority.",
                     "action": "Launch targeted digital marketing campaign; set a 90-day customer doubling goal."})

    open_leads = [l for l in leads if l.get("status") in ("new", "contacted")]
    if open_leads:
        recs.append({"priority": "medium", "category": "sales", "title": f"Close {len(open_leads)} Open Leads",
                     "description": "Leads in pipeline represent immediate revenue opportunity.",
                     "action": "Assign each lead to a team member; follow up within 24 hours."})

    # Operations
    if products:
        out_of_stock = [p for p in products if p.get("stock", 0) == 0]
        if out_of_stock:
            recs.append({"priority": "high", "category": "operations", "title": f"Restock {len(out_of_stock)} Products",
                         "description": "Out-of-stock items result in direct revenue loss.",
                         "action": "Place emergency restock orders for zero-stock SKUs."})

    # Goals
    stalled = [g for g in goals if g.get("current_value", 0) / max(g.get("target_value", 1), 1) < 0.3]
    if stalled:
        recs.append({"priority": "medium", "category": "strategy", "title": f"{len(stalled)} Goals Behind Schedule",
                     "description": "Several strategic goals are below 30% progress.",
                     "action": "Schedule quarterly goal review meeting; break goals into weekly milestones."})

    # Always add a forward-looking rec
    recs.append({"priority": "low", "category": "strategy", "title": "Plan Next Fiscal Quarter",
                 "description": "Structured quarterly planning improves execution by 40%.",
                 "action": "Create a quarterly business plan with budget, targets, and KPIs."})

    return sorted(recs, key=lambda r: ["critical", "high", "medium", "low"].index(r["priority"]))


# ── Company health score ──────────────────────────────────────────────────────

def company_health_score(company_id: int) -> dict:
    """Compute a 0–100 health score across four dimensions."""
    summary = accounting_repo.get_summary(company_id)
    customers = crm_repo.count_customers(company_id)
    leads = crm_repo.list_leads(company_id)
    products = inventory_repo.list_products(company_id)
    employees = hr_repo.list_employees(company_id)

    income = summary.get("income", 0)
    expenses = summary.get("expenses", 0)
    profit = income - expenses

    # Financial dimension (0–25)
    fin = 0
    if income > 0: fin += 10
    if profit > 0: fin += 10
    if income > 0 and expenses / income < 0.7: fin += 5

    # Growth dimension (0–25)
    grow = 0
    if customers > 0: grow += 5
    if customers > 10: grow += 5
    if customers > 50: grow += 5
    conversion = len([l for l in leads if l.get("status") == "converted"]) / max(len(leads), 1)
    if conversion > 0.15: grow += 5
    if conversion > 0.30: grow += 5

    # Operations dimension (0–25)
    ops = 0
    if products: ops += 10
    out_of_stock = len([p for p in products if p.get("stock", 0) == 0])
    if out_of_stock == 0: ops += 10
    elif out_of_stock < 3: ops += 5
    if employees: ops += 5

    # Strategy dimension (0–25)
    goals = ent_repo.list_goals(company_id, status="active")
    plans = ent_repo.list_plans(company_id)
    strat = 0
    if goals: strat += 10
    if plans: strat += 10
    kpis = ent_repo.list_kpis(company_id)
    if kpis: strat += 5

    total = fin + grow + ops + strat
    grade = "A" if total >= 80 else "B" if total >= 65 else "C" if total >= 50 else "D" if total >= 35 else "F"

    return {
        "total_score": total,
        "grade": grade,
        "dimensions": {
            "financial": {"score": fin, "max": 25},
            "growth": {"score": grow, "max": 25},
            "operations": {"score": ops, "max": 25},
            "strategy": {"score": strat, "max": 25},
        },
        "interpretation": {
            "A": "Excellent — business is performing strongly across all dimensions",
            "B": "Good — solid fundamentals with room for improvement",
            "C": "Fair — several areas need attention",
            "D": "Poor — significant gaps in business health",
            "F": "Critical — immediate strategic intervention required",
        }[grade],
    }

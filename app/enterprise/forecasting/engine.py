"""
Enterprise forecasting engine — revenue, expense, hiring, and expansion forecasts.

Uses trend extrapolation on live business data. Each forecast is stored with
encrypted assumptions for auditability.
"""

from __future__ import annotations

from app.enterprise import repository as ent_repo
from app.modules.accounting import repository as accounting_repo
from app.modules.crm import repository as crm_repo
from app.modules.hr import repository as hr_repo
from app.modules.inventory import repository as inventory_repo


def _trend_factor(values: list[float]) -> float:
    if len(values) < 2:
        return 1.03  # default 3% growth
    diffs = [(values[i] - values[i - 1]) / max(abs(values[i - 1]), 1) for i in range(1, len(values))]
    avg = sum(diffs) / len(diffs)
    return max(1 + avg, 0.5)  # floor at -50% per period


def _conf(data_points: int) -> float:
    return min(0.45 + data_points * 0.05, 0.90)


# ── Revenue forecast ──────────────────────────────────────────────────────────

def forecast_revenue(company_id: int, periods: int = 3) -> list[dict]:
    txns = accounting_repo.list_transactions(company_id)
    income_values = [t["amount"] for t in txns if t.get("type") == "income"]

    base = sum(income_values[-6:]) / max(len(income_values[-6:]), 1) if income_values else 0
    factor = _trend_factor(income_values[-12:])
    conf = _conf(len(income_values))

    results = []
    val = base
    for i in range(1, periods + 1):
        val = round(val * factor, 2)
        assumptions = {"base": base, "trend_factor": round(factor, 4), "period": i}
        row = ent_repo.save_forecast(company_id, "revenue", "monthly", i, val, conf, assumptions)
        results.append({**row, "period_label": f"Month +{i}", "formatted": f"₱{val:,.2f}"})

    return results


# ── Expense forecast ──────────────────────────────────────────────────────────

def forecast_expenses(company_id: int, periods: int = 3) -> list[dict]:
    txns = accounting_repo.list_transactions(company_id)
    expense_values = [t["amount"] for t in txns if t.get("type") == "expense"]

    base = sum(expense_values[-6:]) / max(len(expense_values[-6:]), 1) if expense_values else 0
    factor = _trend_factor(expense_values[-12:])
    conf = _conf(len(expense_values))

    results = []
    val = base
    for i in range(1, periods + 1):
        val = round(val * factor, 2)
        assumptions = {"base": base, "trend_factor": round(factor, 4), "period": i}
        row = ent_repo.save_forecast(company_id, "expense", "monthly", i, val, conf, assumptions)
        results.append({**row, "period_label": f"Month +{i}", "formatted": f"₱{val:,.2f}"})

    return results


# ── Hiring forecast ───────────────────────────────────────────────────────────

def forecast_hiring(company_id: int, periods: int = 3) -> list[dict]:
    employees = hr_repo.list_employees(company_id)
    summary = accounting_repo.get_summary(company_id)
    customers = crm_repo.count_customers(company_id)

    current_headcount = len(employees)
    income = summary.get("income", 0)

    # Rule of thumb: 1 new hire per 15 new customers or per ₱150k revenue increase
    revenue_capacity = income / max(150_000, 1)
    customer_capacity = customers / max(15, 1)
    growth_capacity = max(revenue_capacity, customer_capacity)
    needed_next = max(round(growth_capacity - current_headcount, 0), 0)

    results = []
    headcount = current_headcount
    for i in range(1, periods + 1):
        # Gradual hiring ramp
        new_hires = max(round(needed_next * (0.4 ** (i - 1))), 0)
        headcount += new_hires
        val = float(headcount)
        conf = 0.65
        assumptions = {
            "current_headcount": current_headcount,
            "new_hires_this_period": new_hires,
            "revenue_driven": round(revenue_capacity, 1),
        }
        row = ent_repo.save_forecast(company_id, "hiring", "quarterly", i, val, conf, assumptions)
        results.append({
            **row,
            "period_label": f"Q+{i}",
            "new_hires": new_hires,
            "total_headcount": headcount,
        })

    return results


# ── Expansion forecast ────────────────────────────────────────────────────────

def forecast_expansion(company_id: int, periods: int = 3) -> list[dict]:
    summary = accounting_repo.get_summary(company_id)
    customers = crm_repo.count_customers(company_id)
    products = inventory_repo.list_products(company_id)

    income = summary.get("income", 0)
    expenses = summary.get("expenses", 0)
    profit = income - expenses

    # Expansion readiness score (0-100)
    readiness = 0
    if profit > 0: readiness += 30
    if customers > 30: readiness += 20
    if income > 200_000: readiness += 20
    if len(products) > 5: readiness += 15
    if profit / max(income, 1) > 0.2: readiness += 15

    results = []
    cumulative_readiness = readiness
    for i in range(1, periods + 1):
        # Readiness grows as business matures
        projected_readiness = min(cumulative_readiness + (i * 8), 100)
        stage = (
            "Ready for expansion" if projected_readiness >= 70
            else "Preparing for expansion" if projected_readiness >= 45
            else "Focus on current market first"
        )
        conf = 0.60
        assumptions = {
            "current_readiness": readiness,
            "projected_readiness": projected_readiness,
            "stage": stage,
        }
        row = ent_repo.save_forecast(company_id, "expansion", "quarterly", i, projected_readiness, conf, assumptions)
        results.append({
            **row,
            "period_label": f"Q+{i}",
            "readiness_score": projected_readiness,
            "stage": stage,
            "recommendation": (
                "Consider opening new location or market" if projected_readiness >= 70
                else "Strengthen core business before expanding"
            ),
        })

    return results


# ── Combined ──────────────────────────────────────────────────────────────────

def run_all_forecasts(company_id: int, periods: int = 3) -> dict:
    ent_repo.log_enterprise_action(company_id, "forecasts.run_all", details=f"periods={periods}")
    return {
        "revenue": forecast_revenue(company_id, periods),
        "expenses": forecast_expenses(company_id, periods),
        "hiring": forecast_hiring(company_id, periods),
        "expansion": forecast_expansion(company_id, periods),
    }

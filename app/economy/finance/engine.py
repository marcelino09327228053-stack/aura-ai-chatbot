"""
Financial intelligence — cash-flow analysis, investment planning,
budget optimization, revenue forecasting.
"""

from __future__ import annotations

from app.economy import repository as econ_repo
from app.modules.accounting import repository as accounting_repo
from app.modules.crm import repository as crm_repo


def cash_flow_analysis(company_id: int) -> dict:
    """Analyse cash inflows, outflows, and net position."""
    summary = accounting_repo.get_summary(company_id)
    txns = accounting_repo.list_transactions(company_id)

    income = summary.get("income", 0)
    expenses = summary.get("expenses", 0)
    net = income - expenses

    income_txns = [t for t in txns if t.get("type") == "income"]
    expense_txns = [t for t in txns if t.get("type") == "expense"]

    avg_income = sum(t.get("amount", 0) for t in income_txns) / max(len(income_txns), 1)
    avg_expense = sum(t.get("amount", 0) for t in expense_txns) / max(len(expense_txns), 1)

    return {
        "monthly_inflow": income,
        "monthly_outflow": expenses,
        "net_cash_flow": net,
        "cash_flow_status": "positive" if net > 0 else "negative",
        "avg_transaction_income": round(avg_income, 2),
        "avg_transaction_expense": round(avg_expense, 2),
        "income_transaction_count": len(income_txns),
        "expense_transaction_count": len(expense_txns),
        "runway_months": round(net * 6 / max(expenses, 1), 1) if net > 0 else 0,
        "recommendations": [
            "Maintain 3-month cash reserve" if net > 0 else "Reduce expenses immediately",
            "Invoice faster to improve inflow timing",
            "Negotiate Net 30 terms with suppliers",
        ],
    }


def investment_planning(company_id: int, available_capital: float | None = None) -> dict:
    """Suggest investment allocation based on available capital."""
    summary = accounting_repo.get_summary(company_id)
    profit = summary.get("income", 0) - summary.get("expenses", 0)
    capital = available_capital if available_capital is not None else max(profit * 3, 0)

    allocations = {
        "growth_marketing": round(capital * 0.30, 2),
        "inventory": round(capital * 0.25, 2),
        "technology": round(capital * 0.20, 2),
        "team": round(capital * 0.15, 2),
        "reserve": round(capital * 0.10, 2),
    }

    econ_repo.log_economy_action(company_id, "finance.investment_plan")
    return {
        "available_capital": capital,
        "allocations": allocations,
        "expected_roi_pct": 25,
        "plan_horizon_months": 12,
        "priority_order": ["growth_marketing", "inventory", "technology", "team", "reserve"],
    }


def budget_optimization(company_id: int) -> dict:
    """Optimise budget allocation based on current spend."""
    summary = accounting_repo.get_summary(company_id)
    txns = accounting_repo.list_transactions(company_id)
    income = summary.get("income", 0)
    expenses = summary.get("expenses", 0)

    expense_items = [t for t in txns if t.get("type") == "expense"]
    categories: dict[str, float] = {}
    for t in expense_items:
        cat = (t.get("description") or "Other")[:30]
        categories[cat] = categories.get(cat, 0) + t.get("amount", 0)

    target_expense_ratio = 0.65
    target_expenses = income * target_expense_ratio
    savings_potential = max(expenses - target_expenses, 0)

    return {
        "current_income": income,
        "current_expenses": expenses,
        "expense_ratio_pct": round(expenses / max(income, 1) * 100, 1),
        "target_expense_ratio_pct": target_expense_ratio * 100,
        "potential_savings": round(savings_potential, 2),
        "top_expense_categories": sorted(
            [{"category": k, "amount": v} for k, v in categories.items()],
            key=lambda x: x["amount"], reverse=True,
        )[:5],
        "optimizations": [
            f"Reduce expenses by ₱{savings_potential:,.0f} to hit 65% ratio" if savings_potential > 0 else "Expense ratio is healthy",
            "Renegotiate top 2 supplier contracts",
            "Review recurring subscriptions",
        ],
    }


def revenue_forecast(company_id: int, periods: int = 6) -> list[dict]:
    """Revenue forecast using transaction trends."""
    txns = accounting_repo.list_transactions(company_id)
    income_values = [t["amount"] for t in txns if t.get("type") == "income"]
    base = sum(income_values[-6:]) / max(len(income_values[-6:]), 1) if income_values else 0

    if len(income_values) >= 2:
        diffs = [income_values[i] - income_values[i - 1] for i in range(1, len(income_values))]
        trend = sum(diffs) / len(diffs)
        factor = 1 + (trend / max(base, 1)) if base > 0 else 1.03
    else:
        factor = 1.05

    results = []
    val = base
    for i in range(1, periods + 1):
        val = round(val * factor, 2)
        assumptions = {"base": base, "trend_factor": round(factor, 4), "period": i}
        row = econ_repo.save_forecast(company_id, "revenue", "monthly", i, val, 0.75, assumptions)
        results.append({**row, "period_label": f"Month +{i}", "formatted": f"₱{val:,.2f}"})

    econ_repo.log_economy_action(company_id, "finance.revenue_forecast")
    return results

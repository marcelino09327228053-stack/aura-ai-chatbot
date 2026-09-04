"""
Simulation system — business, expansion, financial, and risk scenarios.
"""

from __future__ import annotations

from app.ecosystem import repository as eco_repo
from app.modules.accounting import repository as accounting_repo
from app.modules.crm import repository as crm_repo
from app.modules.hr import repository as hr_repo


def simulate_business(company_id: int, params: dict) -> dict:
    """What-if on conversion rate, pricing, and costs."""
    summary = accounting_repo.get_summary(company_id)
    leads = crm_repo.list_leads(company_id)
    income = summary.get("income", 0)
    expenses = summary.get("expenses", 0)

    conversion_boost = params.get("conversion_boost_pct", 10) / 100
    price_boost = params.get("price_increase_pct", 0) / 100
    cost_cut = params.get("cost_cut_pct", 0) / 100

    current_conversion = len([l for l in leads if l.get("status") == "converted"]) / max(len(leads), 1)
    new_income = income * (1 + conversion_boost) * (1 + price_boost)
    new_expenses = expenses * (1 - cost_cut)
    new_profit = new_income - new_expenses
    delta = new_profit - (income - expenses)

    result = {
        "scenario": "business",
        "current": {"income": income, "expenses": expenses, "profit": income - expenses, "conversion": round(current_conversion * 100, 1)},
        "projected": {
            "income": round(new_income, 2),
            "expenses": round(new_expenses, 2),
            "profit": round(new_profit, 2),
            "conversion": round(min(current_conversion * (1 + conversion_boost), 1) * 100, 1),
        },
        "delta_profit": round(delta, 2),
        "verdict": "Favorable" if delta >= 0 else "Unfavorable — revise parameters",
    }
    return eco_repo.save_simulation(company_id, "business", params, result, 0.78)


def simulate_expansion(company_id: int, params: dict) -> dict:
    employees = hr_repo.list_employees(company_id)
    customers = crm_repo.count_customers(company_id)
    summary = accounting_repo.get_summary(company_id)
    income = summary.get("income", 0)

    new_markets = params.get("new_markets", 1)
    new_hires = params.get("new_hires", 2)
    cost_per_hire = params.get("monthly_hire_cost", 25000)
    revenue_per_market = params.get("revenue_per_market", 50000)

    extra_cost = new_hires * cost_per_hire
    extra_revenue = new_markets * revenue_per_market
    net = extra_revenue - extra_cost
    payback = round(extra_cost / max(extra_revenue / 12, 1), 1) if extra_revenue else 999

    result = {
        "scenario": "expansion",
        "current": {"employees": len(employees), "customers": customers, "income": income},
        "projected": {
            "employees": len(employees) + new_hires,
            "markets": new_markets,
            "extra_monthly_cost": extra_cost,
            "extra_monthly_revenue": extra_revenue,
            "net_monthly": round(net, 2),
        },
        "payback_months": payback,
        "verdict": "Ready to expand" if payback < 12 and net > 0 else "High risk — stage smaller pilot first",
    }
    return eco_repo.save_simulation(company_id, "expansion", params, result, 0.72)


def simulate_financial(company_id: int, params: dict) -> dict:
    summary = accounting_repo.get_summary(company_id)
    income = summary.get("income", 0)
    expenses = summary.get("expenses", 0)
    months = params.get("months", 6)
    growth = params.get("monthly_growth_pct", 5) / 100
    expense_growth = params.get("expense_growth_pct", 2) / 100

    projections = []
    rev, exp = income, expenses
    for m in range(1, months + 1):
        rev = rev * (1 + growth)
        exp = exp * (1 + expense_growth)
        projections.append({
            "month": m,
            "revenue": round(rev, 2),
            "expenses": round(exp, 2),
            "profit": round(rev - exp, 2),
        })

    total_profit = sum(p["profit"] for p in projections)
    result = {
        "scenario": "financial",
        "months": months,
        "projections": projections,
        "cumulative_profit": round(total_profit, 2),
        "ending_revenue": projections[-1]["revenue"] if projections else 0,
        "verdict": "Healthy trajectory" if total_profit > 0 else "Loss trajectory — adjust growth/cost assumptions",
    }
    return eco_repo.save_simulation(company_id, "financial", params, result, 0.8)


def simulate_risk(company_id: int, params: dict) -> dict:
    summary = accounting_repo.get_summary(company_id)
    income = summary.get("income", 0)
    expenses = summary.get("expenses", 0)
    customers = crm_repo.count_customers(company_id)

    revenue_drop = params.get("revenue_drop_pct", 20) / 100
    customer_churn = params.get("customer_churn_pct", 15) / 100
    cost_spike = params.get("cost_spike_pct", 10) / 100

    stressed_income = income * (1 - revenue_drop)
    stressed_expenses = expenses * (1 + cost_spike)
    stressed_customers = round(customers * (1 - customer_churn))
    stressed_profit = stressed_income - stressed_expenses
    runway = round(max(stressed_profit, 0) * 3 / max(stressed_expenses, 1), 1)

    severity = "critical" if stressed_profit < 0 else "high" if runway < 2 else "medium" if revenue_drop >= 0.15 else "low"

    result = {
        "scenario": "risk",
        "stress_test": {
            "revenue_drop_pct": revenue_drop * 100,
            "customer_churn_pct": customer_churn * 100,
            "cost_spike_pct": cost_spike * 100,
        },
        "stressed": {
            "income": round(stressed_income, 2),
            "expenses": round(stressed_expenses, 2),
            "profit": round(stressed_profit, 2),
            "customers": stressed_customers,
            "runway_months": runway,
        },
        "severity": severity,
        "mitigations": [
            "Build 3-month cash reserve",
            "Diversify revenue streams",
            "Negotiate flexible supplier terms",
            "Activate retention campaigns early",
        ],
        "verdict": f"Risk severity: {severity}",
    }
    return eco_repo.save_simulation(company_id, "risk", params, result, 0.75)


SCENARIO_RUNNERS = {
    "business": simulate_business,
    "expansion": simulate_expansion,
    "financial": simulate_financial,
    "risk": simulate_risk,
}


def run_simulation(company_id: int, scenario_type: str, params: dict | None = None) -> dict:
    params = params or {}
    eco_repo.log_ecosystem_action(company_id, f"simulation.{scenario_type}", details=str(params)[:150])
    runner = SCENARIO_RUNNERS.get(scenario_type)
    if not runner:
        raise ValueError(f"Unknown scenario: {scenario_type}. Choose: {list(SCENARIO_RUNNERS)}")
    sim = runner(company_id, params)
    eco_repo.create_notification(
        company_id,
        f"Simulation complete: {scenario_type}",
        sim.get("result", {}).get("verdict", "See results"),
        "low",
        "simulations",
    )
    return sim

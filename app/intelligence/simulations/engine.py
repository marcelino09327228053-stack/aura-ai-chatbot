"""
Simulation engine — what-if scenarios, budget simulation, business expansion.

All simulations are deterministic given the same parameters + live business data,
so users can compare scenarios side-by-side.
"""

from app.intelligence import repository as intel_repo
from app.modules.accounting import repository as accounting_repo
from app.modules.crm import repository as crm_repo
from app.modules.hr import repository as hr_repo
from app.modules.inventory import repository as inventory_repo


# ── scenario runners ──────────────────────────────────────────────────────────

def simulate_budget(company_id: int, params: dict) -> dict:
    """What happens if we change income/expense targets?"""
    summary = accounting_repo.get_summary(company_id)
    current_income = summary.get("income", 0)
    current_expenses = summary.get("expenses", 0)

    income_change_pct = params.get("income_change_pct", 0)
    expense_change_pct = params.get("expense_change_pct", 0)

    new_income = current_income * (1 + income_change_pct / 100)
    new_expenses = current_expenses * (1 + expense_change_pct / 100)
    new_profit = new_income - new_expenses

    result = {
        "scenario": "budget",
        "params": params,
        "current": {
            "income": current_income,
            "expenses": current_expenses,
            "profit": current_income - current_expenses,
        },
        "projected": {
            "income": round(new_income, 2),
            "expenses": round(new_expenses, 2),
            "profit": round(new_profit, 2),
        },
        "delta_profit": round(new_profit - (current_income - current_expenses), 2),
        "verdict": (
            "Profitable scenario" if new_profit > 0
            else "Warning: projected loss"
        ),
    }
    intel_repo.save_simulation(company_id, "budget", params, result)
    return result


def simulate_expansion(company_id: int, params: dict) -> dict:
    """What if we hire more staff and expand to new markets?"""
    employees = hr_repo.list_employees(company_id)
    customers = crm_repo.count_customers(company_id)
    summary = accounting_repo.get_summary(company_id)

    new_hires = params.get("new_hires", 1)
    new_markets = params.get("new_markets", 1)
    monthly_hire_cost = params.get("monthly_hire_cost", 25000)
    expected_revenue_per_market = params.get("expected_revenue_per_market", 50000)

    additional_cost = new_hires * monthly_hire_cost
    additional_revenue = new_markets * expected_revenue_per_market
    projected_net = additional_revenue - additional_cost
    payback_months = (
        round(additional_cost * 6 / max(additional_revenue, 1), 1) if additional_revenue > 0 else 999
    )

    result = {
        "scenario": "expansion",
        "params": params,
        "current": {
            "employees": len(employees),
            "customers": customers,
            "monthly_income": summary.get("income", 0),
        },
        "projected": {
            "total_employees": len(employees) + new_hires,
            "new_markets": new_markets,
            "additional_monthly_cost": additional_cost,
            "additional_monthly_revenue": additional_revenue,
            "net_gain": round(projected_net, 2),
        },
        "payback_months": payback_months,
        "verdict": (
            f"ROI achieved in {payback_months} months" if payback_months < 12
            else "High risk — consider smaller expansion first"
        ),
    }
    intel_repo.save_simulation(company_id, "expansion", params, result)
    return result


def simulate_what_if(company_id: int, params: dict) -> dict:
    """Generic what-if: adjust conversion rate, product pricing, or cost base."""
    leads = crm_repo.list_leads(company_id)
    products = inventory_repo.list_products(company_id)
    summary = accounting_repo.get_summary(company_id)

    conversion_boost_pct = params.get("conversion_boost_pct", 10)
    price_increase_pct = params.get("price_increase_pct", 0)
    cost_cut_pct = params.get("cost_cut_pct", 0)

    current_conversion = len([l for l in leads if l.get("status") == "converted"]) / max(len(leads), 1)
    new_conversion = min(current_conversion * (1 + conversion_boost_pct / 100), 1.0)
    avg_price = (
        sum(p.get("price", 0) for p in products) / len(products) if products else 0
    )
    new_avg_price = avg_price * (1 + price_increase_pct / 100)

    current_expenses = summary.get("expenses", 0)
    new_expenses = current_expenses * (1 - cost_cut_pct / 100)

    additional_customers = round(len(leads) * (new_conversion - current_conversion), 1)
    revenue_boost = additional_customers * new_avg_price
    expense_savings = current_expenses - new_expenses
    net_impact = round(revenue_boost + expense_savings, 2)

    result = {
        "scenario": "what_if",
        "params": params,
        "current": {
            "conversion_rate": f"{round(current_conversion * 100, 1)}%",
            "avg_product_price": round(avg_price, 2),
            "monthly_expenses": current_expenses,
        },
        "projected": {
            "new_conversion_rate": f"{round(new_conversion * 100, 1)}%",
            "new_avg_price": round(new_avg_price, 2),
            "new_expenses": round(new_expenses, 2),
            "additional_customers": additional_customers,
            "revenue_boost": round(revenue_boost, 2),
            "expense_savings": round(expense_savings, 2),
            "total_net_impact": net_impact,
        },
        "verdict": (
            f"Net impact: +₱{net_impact}" if net_impact >= 0
            else f"Net impact: -₱{abs(net_impact)} — review parameters"
        ),
    }
    intel_repo.save_simulation(company_id, "what_if", params, result)
    return result


SCENARIO_RUNNERS = {
    "budget": simulate_budget,
    "expansion": simulate_expansion,
    "what_if": simulate_what_if,
}


def run_simulation(company_id: int, scenario_type: str, params: dict) -> dict:
    intel_repo.log_intelligence_action(
        company_id,
        f"simulation.{scenario_type}",
        str(params)[:200],
    )
    runner = SCENARIO_RUNNERS.get(scenario_type)
    if not runner:
        raise ValueError(f"Unknown scenario: {scenario_type}. Choose: {list(SCENARIO_RUNNERS)}")
    return runner(company_id, params)

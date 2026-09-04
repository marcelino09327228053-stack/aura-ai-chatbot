"""
Investment tools — ROI calculator, budget allocation, capital planning, forecast models.
"""

from __future__ import annotations
import math

from app.corporation import repository as corp_repo
from app.modules.accounting import repository as accounting_repo
from app.modules.hr import repository as hr_repo


# ── ROI Calculator ────────────────────────────────────────────────────────────

def calculate_roi(company_id: int, name: str, investment_type: str,
                  amount: float, expected_annual_return: float,
                  duration_years: float = 1.0, risk_level: str = "medium") -> dict:
    if amount <= 0:
        raise ValueError("Investment amount must be greater than 0")

    roi_pct = round((expected_annual_return - amount) / amount * 100, 2)
    payback_months = round(amount / max(expected_annual_return / 12, 0.01), 1)
    npv_discount = {"low": 0.08, "medium": 0.12, "high": 0.18}.get(risk_level, 0.12)
    npv = round(
        sum(expected_annual_return / (1 + npv_discount) ** y for y in range(1, int(duration_years) + 1)) - amount,
        2,
    )
    irr_approx = round((expected_annual_return / amount) ** (1 / max(duration_years, 1)) - 1, 4) * 100

    rating = (
        "Excellent" if roi_pct > 100 else
        "Good" if roi_pct > 50 else
        "Fair" if roi_pct > 20 else
        "Poor"
    )

    inv = corp_repo.save_investment(company_id, {
        "investment_type": investment_type,
        "name": name,
        "amount": amount,
        "expected_return": expected_annual_return,
        "roi_pct": roi_pct,
        "payback_months": payback_months,
        "risk_level": risk_level,
        "notes": f"NPV: ₱{npv:,.2f}, IRR approx: {irr_approx:.1f}%",
    })

    corp_repo.log_corp_action(company_id, "investment.roi_calc", "cfo", name)
    return {
        **inv,
        "roi_pct": roi_pct,
        "payback_months": payback_months,
        "npv": npv,
        "irr_approx_pct": irr_approx,
        "rating": rating,
        "recommendation": (
            f"{'Proceed' if roi_pct > 30 and npv > 0 else 'Review'}: "
            f"{rating} ROI of {roi_pct:.1f}% with payback in {payback_months:.1f} months."
        ),
    }


# ── Budget allocation ─────────────────────────────────────────────────────────

BUDGET_ALLOCATION_FRAMEWORKS = {
    "startup": {"marketing": 25, "operations": 30, "technology": 20, "people": 15, "reserve": 10},
    "growth":  {"marketing": 20, "operations": 25, "technology": 15, "people": 30, "reserve": 10},
    "mature":  {"marketing": 15, "operations": 30, "technology": 10, "people": 35, "reserve": 10},
    "lean":    {"marketing": 10, "operations": 40, "technology": 10, "people": 30, "reserve": 10},
}

BUSINESS_STAGE_MAP = {
    "startup": "Early stage — fewer than 20 customers or under ₱50k monthly revenue",
    "growth":  "Growth stage — 20–100 customers or ₱50k–₱500k monthly revenue",
    "mature":  "Mature stage — 100+ customers or ₱500k+ monthly revenue",
    "lean":    "Lean mode — operating under tight cash constraints",
}


def allocate_budget(company_id: int, total_budget: float, stage: str = "growth") -> dict:
    if stage not in BUDGET_ALLOCATION_FRAMEWORKS:
        raise ValueError(f"Unknown stage: {stage}. Choose: {list(BUDGET_ALLOCATION_FRAMEWORKS)}")

    summary = accounting_repo.get_summary(company_id)
    income = summary.get("income", 0)

    framework = BUDGET_ALLOCATION_FRAMEWORKS[stage]
    allocation = {}
    for category, pct in framework.items():
        amount = round(total_budget * pct / 100, 2)
        allocation[category] = {
            "percentage": pct,
            "amount": amount,
            "formatted": f"₱{amount:,.2f}",
        }

    corp_repo.log_corp_action(company_id, "investment.budget_allocation", "cfo", f"₱{total_budget:,.0f} / {stage}")
    return {
        "total_budget": total_budget,
        "stage": stage,
        "stage_description": BUSINESS_STAGE_MAP[stage],
        "allocation": allocation,
        "monthly_income": income,
        "budget_as_pct_of_income": round(total_budget / max(income, 1) * 100, 1) if income > 0 else None,
    }


# ── Capital planning ──────────────────────────────────────────────────────────

def capital_plan(company_id: int, growth_target_pct: float = 20.0, months: int = 12) -> dict:
    summary = accounting_repo.get_summary(company_id)
    employees = hr_repo.list_employees(company_id)

    income = summary.get("income", 0)
    expenses = summary.get("expenses", 0)
    profit = income - expenses
    monthly_cash_surplus = max(profit, 0)

    target_monthly_income = income * (1 + growth_target_pct / 100)
    revenue_gap = max(target_monthly_income - income, 0)
    required_investment = round(revenue_gap * 2.5, 0)  # Rule of thumb: 2.5x revenue gap

    # Hiring cost estimate
    target_employees = max(len(employees) + round(revenue_gap / 150_000), len(employees))
    new_hires = max(target_employees - len(employees), 0)
    hiring_budget = new_hires * 25_000  # avg monthly cost per hire

    # Cash runway
    runway_months = round(monthly_cash_surplus * months / max(required_investment, 1), 1) if required_investment > 0 else 999

    corp_repo.log_corp_action(company_id, "investment.capital_plan", "cfo", f"target={growth_target_pct}%")
    return {
        "current_monthly_income": income,
        "target_monthly_income": round(target_monthly_income, 2),
        "growth_target_pct": growth_target_pct,
        "revenue_gap": round(revenue_gap, 2),
        "required_investment": required_investment,
        "hiring_budget": hiring_budget,
        "new_hires_needed": new_hires,
        "monthly_cash_surplus": monthly_cash_surplus,
        "capital_runway_months": runway_months,
        "funding_options": [
            {"option": "Retained earnings", "feasibility": "high" if monthly_cash_surplus > 0 else "low"},
            {"option": "Business loan", "feasibility": "medium"},
            {"option": "Angel / seed investment", "feasibility": "medium" if income > 50_000 else "low"},
            {"option": "Revenue-based financing", "feasibility": "high" if income > 100_000 else "low"},
        ],
        "plan_horizon_months": months,
    }


def list_investments_summary(company_id: int) -> dict:
    investments = corp_repo.list_investments(company_id)
    total_invested = sum(i.get("amount", 0) for i in investments)
    total_expected = sum(i.get("expected_return", 0) for i in investments)
    avg_roi = (
        sum(i.get("roi_pct", 0) for i in investments) / len(investments) if investments else 0
    )
    return {
        "count": len(investments),
        "total_invested": round(total_invested, 2),
        "total_expected_return": round(total_expected, 2),
        "average_roi_pct": round(avg_roi, 1),
        "investments": investments,
    }

"""
Decision engine — business analysis, investment recommendations,
expansion planning, and risk assessment decisions.
"""

from __future__ import annotations

from app.corporation import repository as corp_repo
from app.modules.accounting import repository as accounting_repo
from app.modules.crm import repository as crm_repo
from app.modules.hr import repository as hr_repo
from app.modules.inventory import repository as inventory_repo


def analyze_business(company_id: int) -> dict:
    """Full business analysis across all dimensions."""
    summary = accounting_repo.get_summary(company_id)
    customers = crm_repo.count_customers(company_id)
    leads = crm_repo.list_leads(company_id)
    employees = hr_repo.list_employees(company_id)
    products = inventory_repo.list_products(company_id)

    income = summary.get("income", 0)
    expenses = summary.get("expenses", 0)
    profit = income - expenses
    margin = profit / max(income, 1) * 100
    expense_ratio = expenses / max(income, 1) * 100
    conversion = len([l for l in leads if l.get("status") == "converted"]) / max(len(leads), 1) * 100

    # Score each dimension 0–10
    financial_score = min(10, max(0,
        (3 if profit > 0 else 0) +
        (3 if margin > 15 else 2 if margin > 5 else 0) +
        (2 if expense_ratio < 70 else 1 if expense_ratio < 85 else 0) +
        (2 if income > 100_000 else 1 if income > 20_000 else 0)
    ))
    growth_score = min(10, max(0,
        (3 if customers > 50 else 2 if customers > 10 else 1 if customers > 0 else 0) +
        (3 if conversion > 30 else 2 if conversion > 15 else 1 if conversion > 5 else 0) +
        (2 if len(leads) > 10 else 1 if len(leads) > 0 else 0) +
        (2 if customers > 100 else 0)
    ))
    ops_score = min(10, max(0,
        (4 if products else 0) +
        (3 if employees else 0) +
        (3 if len([p for p in products if p.get("stock", 0) == 0]) == 0 else 1)
    ))

    overall = round((financial_score + growth_score + ops_score) / 30 * 100, 1)

    analysis = {
        "overall_score": overall,
        "financial": {"score": financial_score, "max": 10, "income": income, "expenses": expenses, "profit": profit, "margin_pct": round(margin, 1)},
        "growth": {"score": growth_score, "max": 10, "customers": customers, "leads": len(leads), "conversion_pct": round(conversion, 1)},
        "operations": {"score": ops_score, "max": 10, "employees": len(employees), "products": len(products)},
        "strengths": [],
        "weaknesses": [],
        "next_actions": [],
    }

    if profit > 0: analysis["strengths"].append("Profitable operations")
    if customers > 20: analysis["strengths"].append(f"Established customer base ({customers})")
    if conversion > 20: analysis["strengths"].append(f"Strong conversion rate ({conversion:.1f}%)")
    if products: analysis["strengths"].append(f"Active product catalogue ({len(products)} SKUs)")

    if profit <= 0: analysis["weaknesses"].append("Operating at a loss")
    if expense_ratio > 80: analysis["weaknesses"].append(f"High expense ratio ({expense_ratio:.0f}%)")
    if customers < 10: analysis["weaknesses"].append("Very small customer base")
    if not products: analysis["weaknesses"].append("No products in inventory")

    if profit <= 0: analysis["next_actions"].append("Immediate cost audit — identify top 3 reducible expenses")
    if customers < 20: analysis["next_actions"].append("Launch customer acquisition campaign with referral incentive")
    if leads: analysis["next_actions"].append(f"Follow up on {len([l for l in leads if l.get('status')=='new'])} new leads within 24 hours")
    analysis["next_actions"].append("Schedule weekly executive review of KPIs")

    corp_repo.save_decision(company_id, "system", "business_analysis", "Business Analysis",
                            str(analysis), str(analysis["next_actions"]), 0.85)
    corp_repo.log_corp_action(company_id, "decision.business_analysis")
    return analysis


def recommend_investments(company_id: int) -> list[dict]:
    """Generate investment recommendations based on business state."""
    summary = accounting_repo.get_summary(company_id)
    customers = crm_repo.count_customers(company_id)
    products = inventory_repo.list_products(company_id)
    income = summary.get("income", 0)
    profit = income - summary.get("expenses", 0)

    recs = []

    if profit > 20_000:
        recs.append({
            "category": "marketing", "title": "Digital Marketing Investment",
            "description": "Invest in targeted digital ads to accelerate customer acquisition.",
            "suggested_amount": round(profit * 0.15, 0),
            "expected_roi_pct": 180, "payback_months": 3, "priority": "high",
        })

    if products and any(p.get("stock", 0) < 5 for p in products):
        recs.append({
            "category": "inventory", "title": "Inventory Restocking",
            "description": "Restock low-inventory items before they cause lost sales.",
            "suggested_amount": round(income * 0.05, 0),
            "expected_roi_pct": 120, "payback_months": 1, "priority": "high",
        })

    if customers > 30:
        recs.append({
            "category": "technology", "title": "CRM & Automation Tools",
            "description": "Invest in automation tools to handle growing customer volume efficiently.",
            "suggested_amount": 15_000, "expected_roi_pct": 220, "payback_months": 6, "priority": "medium",
        })

    recs.append({
        "category": "training", "title": "Team Skills Development",
        "description": "Invest in upskilling key team members for long-term productivity gains.",
        "suggested_amount": 10_000, "expected_roi_pct": 150, "payback_months": 12, "priority": "low",
    })

    corp_repo.log_corp_action(company_id, "decision.investment_recommendations")
    return recs


def plan_expansion(company_id: int) -> dict:
    """Generate an expansion readiness report and roadmap."""
    summary = accounting_repo.get_summary(company_id)
    customers = crm_repo.count_customers(company_id)
    employees = hr_repo.list_employees(company_id)
    products = inventory_repo.list_products(company_id)

    income = summary.get("income", 0)
    profit = income - summary.get("expenses", 0)
    margin = profit / max(income, 1) * 100

    readiness_items = [
        {"item": "Positive profit margin", "met": profit > 0, "weight": 25},
        {"item": "Established customer base (30+)", "met": customers >= 30, "weight": 20},
        {"item": "Healthy revenue (₱200k+/month)", "met": income >= 200_000, "weight": 20},
        {"item": "Documented processes (employees)", "met": len(employees) > 0, "weight": 15},
        {"item": "Diversified product catalogue (5+ SKUs)", "met": len(products) >= 5, "weight": 10},
        {"item": "Profit margin above 15%", "met": margin >= 15, "weight": 10},
    ]

    score = sum(item["weight"] for item in readiness_items if item["met"])
    stage = (
        "Ready for expansion" if score >= 70
        else "Near expansion readiness" if score >= 45
        else "Early stage — focus on core market"
    )

    roadmap = []
    if score < 70:
        not_met = [i for i in readiness_items if not i["met"]]
        for item in not_met[:3]:
            roadmap.append({"milestone": f"Achieve: {item['item']}", "timeline": "1-3 months"})
    roadmap.append({"milestone": "Market research for target expansion region", "timeline": "1 month"})
    roadmap.append({"milestone": "Legal and regulatory review for new market", "timeline": "2 months"})
    roadmap.append({"milestone": "Pilot launch with limited product range", "timeline": "3-6 months"})

    corp_repo.log_corp_action(company_id, "decision.expansion_plan")
    return {
        "readiness_score": score,
        "stage": stage,
        "readiness_items": readiness_items,
        "roadmap": roadmap,
        "estimated_expansion_budget": round(income * 0.3, 0) if income > 0 else 0,
    }


def run_decision(company_id: int, decision_type: str, context: dict = {}) -> dict:
    """Dispatch a specific decision request."""
    corp_repo.log_corp_action(company_id, f"decision.{decision_type}", details=str(context)[:100])
    if decision_type == "business_analysis":
        return analyze_business(company_id)
    elif decision_type == "investment":
        return {"recommendations": recommend_investments(company_id)}
    elif decision_type == "expansion":
        return plan_expansion(company_id)
    else:
        raise ValueError(f"Unknown decision type: {decision_type}. Choose: business_analysis, investment, expansion")

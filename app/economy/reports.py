"""
Executive reports — market, financial, strategic, and risk reports.
"""

from __future__ import annotations

from app.economy import repository as econ_repo
from app.economy.finance import engine as finance_engine
from app.economy.markets import engine as markets_engine
from app.economy.partnerships import engine as partnership_engine


def generate_market_report(company_id: int, sector: str = "general") -> dict:
    analysis = markets_engine.analyze_market(company_id, sector)
    competitor = markets_engine.competitor_analysis(company_id)
    growth = markets_engine.growth_analysis(company_id)
    opportunities = markets_engine.detect_opportunities(company_id)

    content = {
        "market_analysis": analysis,
        "competitor_analysis": competitor,
        "growth_analysis": growth,
        "opportunities": opportunities[:5],
    }
    summary = (
        f"Market outlook: {analysis['outlook']}. "
        f"Position: {competitor['market_position']}. "
        f"Growth stage: {growth['growth_stage']}."
    )

    report = econ_repo.save_report(company_id, "market", f"Market Report — {sector.title()}", content, summary)
    econ_repo.log_economy_action(company_id, "report.market")
    return report


def generate_financial_report(company_id: int) -> dict:
    cash_flow = finance_engine.cash_flow_analysis(company_id)
    budget = finance_engine.budget_optimization(company_id)
    investment = finance_engine.investment_planning(company_id)
    revenue_fc = finance_engine.revenue_forecast(company_id, 3)

    content = {
        "cash_flow": cash_flow,
        "budget_optimization": budget,
        "investment_plan": investment,
        "revenue_forecast": revenue_fc,
    }
    summary = (
        f"Cash flow: {cash_flow['cash_flow_status']}. "
        f"Net: ₱{cash_flow['net_cash_flow']:,.0f}. "
        f"Potential savings: ₱{budget['potential_savings']:,.0f}."
    )

    report = econ_repo.save_report(company_id, "financial", "Financial Intelligence Report", content, summary)
    econ_repo.log_economy_action(company_id, "report.financial")
    return report


def generate_strategic_report(company_id: int) -> dict:
    opportunities = markets_engine.detect_opportunities(company_id)
    growth = markets_engine.growth_analysis(company_id)
    collaboration = partnership_engine.collaboration_tools(company_id)
    investment = finance_engine.investment_planning(company_id)

    recommendations = [
        opp.get("title") for opp in opportunities[:3]
    ] + growth.get("key_growth_drivers", [])

    content = {
        "opportunities": opportunities,
        "growth_analysis": growth,
        "collaboration": collaboration,
        "investment_plan": investment,
        "strategic_recommendations": recommendations,
    }
    summary = f"Growth stage: {growth['growth_stage']}. {len(opportunities)} opportunities identified."

    report = econ_repo.save_report(company_id, "strategic", "Strategic Recommendations Report", content, summary)
    econ_repo.log_economy_action(company_id, "report.strategic")
    return report


def generate_risk_report(company_id: int) -> dict:
    cash_flow = finance_engine.cash_flow_analysis(company_id)
    budget = finance_engine.budget_optimization(company_id)

    risks = []
    if cash_flow["cash_flow_status"] == "negative":
        risks.append({"level": "high", "type": "financial", "title": "Negative cash flow", "mitigation": "Reduce expenses and accelerate collections"})
    if budget["expense_ratio_pct"] > 80:
        risks.append({"level": "high", "type": "financial", "title": "High expense ratio", "mitigation": "Budget optimization required"})
    if cash_flow["runway_months"] < 3 and cash_flow["net_cash_flow"] > 0:
        risks.append({"level": "medium", "type": "financial", "title": "Low cash runway", "mitigation": "Build cash reserves"})

    risks.append({"level": "medium", "type": "market", "title": "Competitive pressure", "mitigation": "Differentiate on service and loyalty"})
    risks.append({"level": "low", "type": "operational", "title": "Partner dependency", "mitigation": "Diversify supplier base"})

    if not risks:
        risks.append({"level": "low", "type": "overall", "title": "No major risks", "mitigation": "Continue monitoring"})

    content = {"risks": risks, "cash_flow": cash_flow, "budget": budget}
    summary = f"{len([r for r in risks if r['level'] == 'high'])} high-risk items identified."

    report = econ_repo.save_report(company_id, "risk", "Economic Risk Report", content, summary)
    econ_repo.log_economy_action(company_id, "report.risk")
    return report


def generate_all_reports(company_id: int, sector: str = "general") -> dict:
    return {
        "market": generate_market_report(company_id, sector),
        "financial": generate_financial_report(company_id),
        "strategic": generate_strategic_report(company_id),
        "risk": generate_risk_report(company_id),
    }

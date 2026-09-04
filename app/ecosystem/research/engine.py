"""
Research engine — market analysis, competitor study, opportunity discovery, reports.
"""

from __future__ import annotations

from app.ecosystem import repository as eco_repo
from app.modules.accounting import repository as accounting_repo
from app.modules.crm import repository as crm_repo
from app.modules.inventory import repository as inventory_repo


def analyze_new_markets(company_id: int, sector: str = "general") -> dict:
    summary = accounting_repo.get_summary(company_id)
    customers = crm_repo.count_customers(company_id)
    income = summary.get("income", 0)

    market_segments = [
        {"segment": "Local SMB", "fit_score": 85 if customers < 50 else 60, "entry_barrier": "low"},
        {"segment": "Regional B2B", "fit_score": 70 if income > 50_000 else 40, "entry_barrier": "medium"},
        {"segment": "Online / Digital", "fit_score": 80, "entry_barrier": "low"},
        {"segment": "Export / Cross-border", "fit_score": 55 if income > 100_000 else 25, "entry_barrier": "high"},
    ]
    ranked = sorted(market_segments, key=lambda m: m["fit_score"], reverse=True)

    findings = {
        "sector": sector,
        "current_customers": customers,
        "monthly_revenue": income,
        "segments": ranked,
        "top_recommendation": ranked[0],
        "next_steps": [
            f"Validate demand in {ranked[0]['segment']}",
            "Run a 30-day pilot campaign",
            "Measure CAC and conversion before full expansion",
        ],
    }
    summary_text = (
        f"Top market opportunity: {ranked[0]['segment']} "
        f"(fit {ranked[0]['fit_score']}/100, barrier: {ranked[0]['entry_barrier']})."
    )
    return eco_repo.save_research(company_id, "new_markets", f"Market Analysis — {sector}", findings, summary_text)


def study_competitors(company_id: int) -> dict:
    customers = crm_repo.count_customers(company_id)
    products = inventory_repo.list_products(company_id)
    summary = accounting_repo.get_summary(company_id)
    income = summary.get("income", 0)

    position = (
        "market_leader" if customers > 100
        else "strong_challenger" if customers > 30
        else "growing_player" if customers > 10
        else "early_entrant"
    )
    findings = {
        "position": position,
        "strengths": [
            f"{len(products)} SKUs" if products else "Lean operations",
            f"{customers} customers",
            f"₱{income:,.0f}/mo revenue" if income else "Room to grow revenue",
        ],
        "competitor_threats": [
            "Price undercutting from larger players",
            "Digital-native competitors with better online presence",
            "Customer switching if service quality slips",
        ],
        "counters": [
            "Differentiate on speed and personalization",
            "Build loyalty / referral programs",
            "Monitor competitor pricing monthly",
        ],
    }
    summary_text = f"Competitive position: {position}. Focus on differentiation and retention."
    return eco_repo.save_research(company_id, "competitors", "Competitor Study", findings, summary_text)


def discover_opportunities(company_id: int) -> dict:
    leads = crm_repo.list_leads(company_id)
    products = inventory_repo.list_products(company_id)
    summary = accounting_repo.get_summary(company_id)
    income = summary.get("income", 0)
    expenses = summary.get("expenses", 0)

    opportunities = []
    open_leads = [l for l in leads if l.get("status") in ("new", "contacted")]
    if open_leads:
        opportunities.append({
            "title": f"Convert {len(open_leads)} open leads",
            "value": len(open_leads) * 8000,
            "priority": "high",
        })
    if products and any(p.get("stock", 0) == 0 for p in products):
        opportunities.append({
            "title": "Restock out-of-stock products",
            "value": income * 0.1,
            "priority": "high",
        })
    if income > 0 and expenses / max(income, 1) > 0.7:
        opportunities.append({
            "title": "Cost reduction program",
            "value": expenses * 0.1,
            "priority": "medium",
        })
    opportunities.append({
        "title": "Launch adjacent product line",
        "value": income * 0.25,
        "priority": "medium",
    })

    findings = {"opportunities": opportunities, "count": len(opportunities)}
    summary_text = f"Discovered {len(opportunities)} opportunities; top: {opportunities[0]['title']}."
    return eco_repo.save_research(company_id, "opportunities", "Opportunity Discovery", findings, summary_text)


def generate_research_report(company_id: int, sector: str = "general") -> dict:
    eco_repo.log_ecosystem_action(company_id, "research.report")
    markets = analyze_new_markets(company_id, sector)
    competitors = study_competitors(company_id)
    opportunities = discover_opportunities(company_id)

    report = {
        "markets": markets,
        "competitors": competitors,
        "opportunities": opportunities,
        "executive_summary": (
            f"{markets['summary']} {competitors['summary']} {opportunities['summary']}"
        ),
    }
    eco_repo.save_knowledge(
        company_id, "research", "research_report",
        report["executive_summary"],
    )
    return report


def run_all_research(company_id: int, sector: str = "general") -> dict:
    eco_repo.log_ecosystem_action(company_id, "research.run_all", details=sector)
    return generate_research_report(company_id, sector)

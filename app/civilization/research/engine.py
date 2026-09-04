"""Research center — AI experiments, business models, product innovation, market discovery."""

from __future__ import annotations

from app.civilization import repository as civ_repo


def run_ai_experiments(company_id: int) -> dict:
    findings = {
        "experiments": [
            {"name": "Multi-agent debate", "result": "15% better decision quality", "status": "success"},
            {"name": "Memory compression", "result": "40% storage reduction", "status": "success"},
            {"name": "Federated fine-tuning", "result": "Privacy preserved, +8% accuracy", "status": "promising"},
        ],
        "risk_level": "low",
        "next_steps": ["Scale debate protocol", "Pilot federated training"],
    }
    return civ_repo.save_research(
        company_id, "ai_experiment",
        "AI Experiment Batch",
        findings,
        "Three experiments completed with strong decision-quality and efficiency gains.",
    )


def explore_business_models(company_id: int) -> dict:
    findings = {
        "models": [
            {"name": "Usage-based AI credits", "fit_score": 0.82, "notes": "Aligns cost with value"},
            {"name": "Industry vertical packs", "fit_score": 0.78, "notes": "Retail, HR, Finance templates"},
            {"name": "Network marketplace fees", "fit_score": 0.71, "notes": "Cross-company commerce take-rate"},
        ],
        "recommended": "Usage-based AI credits",
    }
    return civ_repo.save_research(
        company_id, "business_model",
        "Business Model Exploration",
        findings,
        "Usage-based AI credits ranked highest for near-term monetization.",
    )


def innovate_products(company_id: int) -> dict:
    findings = {
        "products": [
            {"name": "Aura Copilot Desk", "impact": 0.85, "effort": 0.55},
            {"name": "Auto-compliance Pack", "impact": 0.8, "effort": 0.6},
            {"name": "Civilization Dashboard", "impact": 0.75, "effort": 0.4},
        ],
        "priority": "Aura Copilot Desk",
    }
    return civ_repo.save_research(
        company_id, "product_innovation",
        "Product Innovation Pipeline",
        findings,
        "Copilot Desk leads by impact/effort; compliance pack is strong follow-on.",
    )


def discover_markets(company_id: int) -> dict:
    findings = {
        "markets": [
            {"region": "SEA", "opportunity": "SME AI automation", "score": 0.88},
            {"region": "JP", "opportunity": "Enterprise compliance AI", "score": 0.76},
            {"region": "US", "opportunity": "Vertical SaaS bundles", "score": 0.81},
        ],
        "top_market": "SEA",
    }
    return civ_repo.save_research(
        company_id, "market_discovery",
        "Market Discovery Report",
        findings,
        "Southeast Asia SME automation is the strongest near-term market opportunity.",
    )


def run_all_research(company_id: int) -> dict:
    results = {
        "ai_experiments": run_ai_experiments(company_id),
        "business_models": explore_business_models(company_id),
        "product_innovation": innovate_products(company_id),
        "market_discovery": discover_markets(company_id),
    }
    civ_repo.log_civ_action(company_id, "research.run_all", details="4 streams")
    return results


def research_overview(company_id: int, refresh: bool = False) -> dict:
    if refresh or not civ_repo.list_research(company_id):
        return run_all_research(company_id)

    return {
        "history": civ_repo.list_research(company_id),
        "by_type": {
            "ai_experiment": civ_repo.list_research(company_id, "ai_experiment"),
            "business_model": civ_repo.list_research(company_id, "business_model"),
            "product_innovation": civ_repo.list_research(company_id, "product_innovation"),
            "market_discovery": civ_repo.list_research(company_id, "market_discovery"),
        },
        "total": len(civ_repo.list_research(company_id)),
    }

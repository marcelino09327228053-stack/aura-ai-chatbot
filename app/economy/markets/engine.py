"""
Economic engine — market analysis, industry forecasting,
price prediction, and opportunity detection.
"""

from __future__ import annotations

from app.economy import repository as econ_repo
from app.modules.accounting import repository as accounting_repo
from app.modules.crm import repository as crm_repo
from app.modules.inventory import repository as inventory_repo


INDUSTRY_TRENDS = [
    {"sector": "retail", "trend": "Omnichannel retail growth", "growth_pct": 18, "region": "SEA"},
    {"sector": "technology", "trend": "AI adoption in SMBs", "growth_pct": 35, "region": "global"},
    {"sector": "services", "trend": "Subscription economy expansion", "growth_pct": 22, "region": "global"},
    {"sector": "manufacturing", "trend": "Supply chain digitisation", "growth_pct": 15, "region": "SEA"},
    {"sector": "food", "trend": "Food delivery and cloud kitchens", "growth_pct": 25, "region": "local"},
    {"sector": "healthcare", "trend": "Telehealth and wellness services", "growth_pct": 20, "region": "global"},
]


def analyze_market(company_id: int, sector: str = "general") -> dict:
    """Market analysis based on business data and sector benchmarks."""
    summary = accounting_repo.get_summary(company_id)
    customers = crm_repo.count_customers(company_id)
    products = inventory_repo.list_products(company_id)
    income = summary.get("income", 0)

    sector_trends = [t for t in INDUSTRY_TRENDS if t["sector"] == sector or sector == "general"]
    avg_growth = sum(t["growth_pct"] for t in sector_trends) / max(len(sector_trends), 1)

    market_size_estimate = max(income * 12 * 50, 1_000_000)  # rough TAM proxy
    market_share = round(income * 12 / market_size_estimate * 100, 4) if market_size_estimate > 0 else 0

    analysis = {
        "sector": sector,
        "market_size_estimate": round(market_size_estimate, 0),
        "estimated_market_share_pct": market_share,
        "sector_growth_rate_pct": round(avg_growth, 1),
        "customer_base": customers,
        "product_count": len(products),
        "annual_revenue_estimate": round(income * 12, 2),
        "competition_level": "high" if customers > 50 else "medium" if customers > 10 else "low",
        "trends": sector_trends[:3] if sector_trends else INDUSTRY_TRENDS[:3],
        "outlook": (
            "Strong growth potential" if avg_growth > 20
            else "Moderate growth" if avg_growth > 10
            else "Stable market"
        ),
    }

    econ_repo.save_market(company_id, {
        "market_name": f"{sector.title()} Market",
        "sector": sector,
        "region": "local",
        "size_estimate": market_size_estimate,
        "growth_rate": avg_growth,
        "competition_level": analysis["competition_level"],
        "notes": analysis["outlook"],
    })
    econ_repo.log_economy_action(company_id, "market.analyze", details=sector)
    return analysis


def industry_forecast(company_id: int, sector: str = "general", periods: int = 4) -> list[dict]:
    """Industry-level growth forecast."""
    analysis = analyze_market(company_id, sector)
    base_growth = analysis["sector_growth_rate_pct"] / 100
    income = accounting_repo.get_summary(company_id).get("income", 0)
    base = income

    results = []
    val = base
    for i in range(1, periods + 1):
        val = round(val * (1 + base_growth / periods), 2)
        conf = min(0.5 + i * 0.08, 0.85)
        assumptions = {"sector": sector, "growth_rate": base_growth, "period": i}
        row = econ_repo.save_forecast(company_id, "industry", "quarterly", i, val, conf, assumptions)
        results.append({**row, "period_label": f"Q+{i}", "formatted": f"₱{val:,.2f}"})

    return results


def predict_prices(company_id: int) -> list[dict]:
    """Price prediction for inventory products."""
    products = inventory_repo.list_products(company_id)
    if not products:
        return []

    predictions = []
    for p in products[:10]:
        current = p.get("price", 0)
        stock = p.get("stock", 0)
        # Low stock → price can increase; high stock → competitive pricing
        if stock < 5:
            change_pct = 5.0
            direction = "increase"
        elif stock > 50:
            change_pct = -3.0
            direction = "decrease"
        else:
            change_pct = 2.0
            direction = "stable_increase"

        predicted = round(current * (1 + change_pct / 100), 2)
        predictions.append({
            "product_id": p.get("id"),
            "name": p.get("name"),
            "current_price": current,
            "predicted_price": predicted,
            "change_pct": change_pct,
            "direction": direction,
            "stock_level": stock,
            "confidence": 0.72,
        })

    econ_repo.log_economy_action(company_id, "market.price_prediction", details=f"{len(predictions)} products")
    return predictions


def detect_opportunities(company_id: int) -> list[dict]:
    """Detect market and business opportunities."""
    summary = accounting_repo.get_summary(company_id)
    leads = crm_repo.list_leads(company_id)
    products = inventory_repo.list_products(company_id)
    customers = crm_repo.count_customers(company_id)
    income = summary.get("income", 0)

    opportunities = []

    open_leads = [l for l in leads if l.get("status") in ("new", "contacted")]
    if open_leads:
        opp = econ_repo.save_opportunity(company_id, {
            "opportunity_type": "sales",
            "title": f"Convert {len(open_leads)} open leads",
            "description": "Immediate revenue from pipeline conversion.",
            "estimated_value": len(open_leads) * 8000,
            "priority": "high",
        })
        opportunities.append(opp)

    if products:
        high_margin = [p for p in products if p.get("price", 0) > 1000]
        if high_margin:
            opp = econ_repo.save_opportunity(company_id, {
                "opportunity_type": "product",
                "title": f"Promote {len(high_margin)} premium products",
                "description": "High-value SKUs can lift average order value.",
                "estimated_value": sum(p.get("price", 0) for p in high_margin),
                "priority": "medium",
            })
            opportunities.append(opp)

    if customers < 50 and income > 0:
        opp = econ_repo.save_opportunity(company_id, {
            "opportunity_type": "market",
            "title": "Expand to adjacent market segment",
            "description": "Customer base has room to grow — target new demographics.",
            "estimated_value": income * 0.5,
            "priority": "high",
        })
        opportunities.append(opp)

    if income > 100_000:
        opp = econ_repo.save_opportunity(company_id, {
            "opportunity_type": "partnership",
            "title": "Strategic partnership opportunity",
            "description": "Revenue scale supports joint ventures or reseller partnerships.",
            "estimated_value": income * 0.2,
            "priority": "medium",
        })
        opportunities.append(opp)

    econ_repo.log_economy_action(company_id, "market.opportunities", details=f"{len(opportunities)} found")
    return opportunities


def competitor_analysis(company_id: int) -> dict:
    """Competitor positioning analysis."""
    summary = accounting_repo.get_summary(company_id)
    customers = crm_repo.count_customers(company_id)
    products = inventory_repo.list_products(company_id)
    income = summary.get("income", 0)

    return {
        "market_position": (
            "Market leader" if customers > 100
            else "Established player" if customers > 30
            else "Growing challenger" if customers > 10
            else "Early-stage entrant"
        ),
        "competitive_advantages": [
            f"Product catalogue: {len(products)} SKUs" if products else None,
            f"Customer base: {customers} customers" if customers else None,
            f"Revenue scale: ₱{income:,.0f}/month" if income > 0 else None,
        ],
        "competitive_gaps": [
            "Limited brand awareness" if customers < 50 else None,
            "Price competition risk" if not products else None,
            "Digital presence needs strengthening",
        ],
        "recommended_actions": [
            "Differentiate on service quality and speed",
            "Build customer loyalty programme",
            "Monitor competitor pricing monthly",
        ],
    }


def demand_forecast(company_id: int, periods: int = 3) -> list[dict]:
    """Demand forecasting based on leads and customer growth."""
    leads = crm_repo.list_leads(company_id)
    customers = crm_repo.count_customers(company_id)
    conversion = len([l for l in leads if l.get("status") == "converted"]) / max(len(leads), 1)

    base_demand = customers + len([l for l in leads if l.get("status") in ("new", "contacted")]) * conversion
    results = []
    val = base_demand
    for i in range(1, periods + 1):
        val = round(val * 1.08, 1)
        assumptions = {"base": base_demand, "conversion_rate": round(conversion * 100, 1), "period": i}
        row = econ_repo.save_forecast(company_id, "demand", "monthly", i, val, 0.68, assumptions)
        results.append({**row, "period_label": f"Month +{i}", "units": val})

    econ_repo.log_economy_action(company_id, "market.demand_forecast")
    return results


def growth_analysis(company_id: int) -> dict:
    """Growth trajectory analysis."""
    summary = accounting_repo.get_summary(company_id)
    customers = crm_repo.count_customers(company_id)
    income = summary.get("income", 0)
    expenses = summary.get("expenses", 0)
    profit = income - expenses

    growth_rate = 15.0 if profit > 0 else 5.0
    if customers > 50:
        growth_rate += 5.0

    return {
        "current_monthly_revenue": income,
        "projected_annual_revenue": round(income * 12 * (1 + growth_rate / 100), 2),
        "growth_rate_pct": growth_rate,
        "customer_growth_potential": round(customers * 1.2, 0),
        "profit_margin_pct": round(profit / max(income, 1) * 100, 1),
        "growth_stage": (
            "Hypergrowth" if growth_rate > 25
            else "Growth" if growth_rate > 15
            else "Stable" if growth_rate > 5
            else "Recovery"
        ),
        "key_growth_drivers": [
            "Customer acquisition" if customers < 50 else "Customer retention",
            "Product expansion" if income > 0 else "Market entry",
            "Operational efficiency",
        ],
    }

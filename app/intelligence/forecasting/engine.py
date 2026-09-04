"""
Forecasting engine — short and long-range business forecasts.

Produces multi-period forecasts using trend extrapolation on actual data.
"""

from app.intelligence.predictions.engine import (
    predict_customer_growth,
    predict_inventory,
    predict_revenue,
    predict_sales,
)


def forecast_next_periods(company_id: int, periods: int = 3) -> dict:
    """Extrapolate current predictions across N future periods."""
    base = {
        "revenue": predict_revenue(company_id)["value"],
        "sales": predict_sales(company_id)["value"],
        "customer_growth": predict_customer_growth(company_id)["value"],
    }

    trend_factors = {
        "revenue": 1.05,
        "sales": 1.08,
        "customer_growth": 1.04,
    }

    forecast = {}
    for metric, start in base.items():
        factor = trend_factors.get(metric, 1.03)
        periods_list = []
        val = start
        for i in range(1, periods + 1):
            val = round(val * factor, 2)
            periods_list.append({"period": i, "value": val})
        forecast[metric] = periods_list

    return {
        "periods": periods,
        "period_unit": "month",
        "forecast": forecast,
        "note": "Assumes current growth trend continues. Adjust via simulation for custom scenarios.",
    }


def risk_indicators(company_id: int) -> dict:
    """Compute risk flags based on current data."""
    from app.modules.accounting import repository as accounting_repo
    from app.modules.crm import repository as crm_repo
    from app.modules.inventory import repository as inventory_repo

    summary = accounting_repo.get_summary(company_id)
    leads = crm_repo.list_leads(company_id)
    products = inventory_repo.list_products(company_id)

    risks = []
    income = summary.get("income", 0)
    expenses = summary.get("expenses", 0)
    profit = summary.get("profit", income - expenses)

    if profit < 0:
        risks.append({"level": "high", "type": "financial", "message": "Business is operating at a loss"})
    elif income > 0 and expenses / max(income, 1) > 0.8:
        risks.append({"level": "medium", "type": "financial", "message": "High expense ratio (>80%)"})

    stale_leads = [l for l in leads if l.get("status") == "new"]
    if len(stale_leads) > 5:
        risks.append({"level": "medium", "type": "sales", "message": f"{len(stale_leads)} leads with no follow-up"})

    if products:
        out_of_stock = [p for p in products if p.get("stock", 0) == 0]
        if out_of_stock:
            risks.append({"level": "high", "type": "inventory", "message": f"{len(out_of_stock)} products out of stock"})

    if not risks:
        risks.append({"level": "low", "type": "overall", "message": "No major risks detected"})

    return {
        "risk_count": len(risks),
        "highest_level": max((r["level"] for r in risks), key=["low", "medium", "high"].index),
        "risks": risks,
    }


def growth_opportunities(company_id: int) -> dict:
    from app.modules.crm import repository as crm_repo
    from app.modules.inventory import repository as inventory_repo

    leads = crm_repo.list_leads(company_id)
    products = inventory_repo.list_products(company_id)

    opportunities = []
    open_leads = [l for l in leads if l.get("status") in ("new", "contacted")]
    if open_leads:
        opportunities.append({
            "type": "sales",
            "title": f"Convert {len(open_leads)} open leads",
            "potential_value": len(open_leads) * 5000,
        })

    high_value = [p for p in products if p.get("price", 0) > 1000 and p.get("stock", 0) > 0]
    if high_value:
        opportunities.append({
            "type": "revenue",
            "title": f"Push {len(high_value)} premium products",
            "potential_value": sum(p.get("price", 0) for p in high_value),
        })

    return {
        "opportunity_count": len(opportunities),
        "opportunities": opportunities,
        "total_potential": sum(o.get("potential_value", 0) for o in opportunities),
    }

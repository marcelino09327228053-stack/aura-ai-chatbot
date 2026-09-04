"""
Trading module — price benchmarks and trade opportunity scoring.
"""

from __future__ import annotations

from app.economy import repository as econ_repo
from app.modules.inventory import repository as inventory_repo


def price_benchmarks(company_id: int) -> list[dict]:
    """Compare product prices against simple market benchmarks."""
    products = inventory_repo.list_products(company_id)
    benchmarks = []
    for p in products[:15]:
        price = p.get("price", 0)
        # Simple benchmark: ±15% of current as market range
        low = round(price * 0.85, 2)
        high = round(price * 1.15, 2)
        position = "competitive" if price else "unknown"
        if price < low:
            position = "below_market"
        elif price > high:
            position = "above_market"

        benchmarks.append({
            "product": p.get("name"),
            "current_price": price,
            "market_low": low,
            "market_high": high,
            "position": position,
            "recommendation": (
                "Consider price increase" if position == "below_market"
                else "Review pricing — may be too high" if position == "above_market"
                else "Price is competitive"
            ),
        })

    econ_repo.log_economy_action(company_id, "trading.benchmarks")
    return benchmarks


def trade_opportunity_score(company_id: int) -> dict:
    """Score overall trading/commerce opportunity."""
    products = inventory_repo.list_products(company_id)
    if not products:
        return {"score": 0, "level": "none", "message": "Add products to enable trade analysis"}

    in_stock = len([p for p in products if p.get("stock", 0) > 0])
    avg_price = sum(p.get("price", 0) for p in products) / len(products)
    score = min(100, in_stock * 5 + (10 if avg_price > 500 else 5))

    return {
        "score": score,
        "level": "high" if score >= 70 else "medium" if score >= 40 else "low",
        "products_tradeable": in_stock,
        "avg_price": round(avg_price, 2),
        "message": f"{in_stock} products ready for trade/commerce",
    }

"""
Prediction engine — sales, revenue, inventory, and customer growth forecasting.

Uses simple statistical models (moving average + trend factor) on real business
data. No external ML libraries required — all predictions run in-process.
"""

from app.intelligence import repository as intel_repo
from app.modules.accounting import repository as accounting_repo
from app.modules.crm import repository as crm_repo
from app.modules.inventory import repository as inventory_repo


# ── helpers ──────────────────────────────────────────────────────────────────

def _trend(values: list[float]) -> float:
    """Linear trend factor: positive = growing, negative = shrinking."""
    if len(values) < 2:
        return 0.0
    diffs = [values[i] - values[i - 1] for i in range(1, len(values))]
    return sum(diffs) / len(diffs)


def _moving_avg(values: list[float], window: int = 3) -> float:
    if not values:
        return 0.0
    tail = values[-window:]
    return sum(tail) / len(tail)


def _confidence(data_points: int) -> float:
    """More historical data → higher confidence (capped at 0.92)."""
    return min(0.50 + data_points * 0.04, 0.92)


# ── individual predictors ─────────────────────────────────────────────────────

def predict_revenue(company_id: int) -> dict:
    txns = accounting_repo.list_transactions(company_id)
    incomes = [t["amount"] for t in txns if t.get("type") == "income"]

    base = _moving_avg(incomes, 5) if incomes else 0.0
    trend = _trend(incomes[-10:]) if len(incomes) >= 2 else 0.0
    predicted = round(max(base + trend, 0.0), 2)
    confidence = _confidence(len(incomes))

    result = intel_repo.save_prediction(
        company_id, "revenue", predicted, confidence, "monthly"
    )
    return {
        **result,
        "basis": f"{len(incomes)} income transactions",
        "trend_per_period": round(trend, 2),
    }


def predict_sales(company_id: int) -> dict:
    leads = crm_repo.list_leads(company_id)
    customers = crm_repo.count_customers(company_id)

    conversion_rate = (
        len([l for l in leads if l.get("status") == "converted"]) / max(len(leads), 1)
    )
    open_leads = len([l for l in leads if l.get("status") in ("new", "contacted")])
    predicted_new_sales = round(open_leads * conversion_rate, 1)
    confidence = _confidence(len(leads))

    result = intel_repo.save_prediction(
        company_id, "sales", predicted_new_sales, confidence, "monthly"
    )
    return {
        **result,
        "open_leads": open_leads,
        "conversion_rate": round(conversion_rate * 100, 1),
        "existing_customers": customers,
    }


def predict_customer_growth(company_id: int) -> dict:
    leads = crm_repo.list_leads(company_id)
    customers = crm_repo.count_customers(company_id)

    monthly_growth_rate = len(leads) / max(customers, 1) * 0.3
    predicted = round(customers * (1 + monthly_growth_rate), 1)
    confidence = _confidence(customers)

    result = intel_repo.save_prediction(
        company_id, "customer_growth", predicted, confidence, "monthly"
    )
    return {
        **result,
        "current_customers": customers,
        "estimated_growth_rate": f"{round(monthly_growth_rate * 100, 1)}%",
    }


def predict_inventory(company_id: int) -> dict:
    products = inventory_repo.list_products(company_id)
    if not products:
        result = intel_repo.save_prediction(
            company_id, "inventory", 0.0, 0.5, "monthly"
        )
        return {**result, "low_stock_items": [], "restock_needed": 0}

    total_units = sum(p.get("stock", 0) for p in products)
    avg_stock = total_units / len(products)
    low_stock = [p for p in products if p.get("stock", 0) < max(avg_stock * 0.2, 5)]

    # Predict weeks until stockout at current "velocity" (avg stock / product count)
    velocity = max(avg_stock * 0.15, 1)
    weeks_to_restock = round(avg_stock / velocity, 1)
    confidence = _confidence(len(products))

    result = intel_repo.save_prediction(
        company_id, "inventory", weeks_to_restock, confidence, "weekly"
    )
    return {
        **result,
        "total_units": total_units,
        "low_stock_items": [{"name": p["name"], "stock": p["stock"]} for p in low_stock[:5]],
        "restock_needed": len(low_stock),
        "weeks_to_critical": weeks_to_restock,
    }


# ── combined ──────────────────────────────────────────────────────────────────

def run_all_predictions(company_id: int) -> dict:
    intel_repo.log_intelligence_action(company_id, "predictions.run_all")
    return {
        "revenue": predict_revenue(company_id),
        "sales": predict_sales(company_id),
        "customer_growth": predict_customer_growth(company_id),
        "inventory": predict_inventory(company_id),
    }

"""
Forecasting engine — unified forecast dispatcher for economy module.
"""

from __future__ import annotations

from app.economy import repository as econ_repo
from app.economy.finance import engine as finance_engine
from app.economy.markets import engine as markets_engine


FORECAST_TYPES = {
    "revenue": finance_engine.revenue_forecast,
    "industry": markets_engine.industry_forecast,
    "demand": markets_engine.demand_forecast,
    "price": lambda cid, periods: markets_engine.predict_prices(cid),
}


def run_forecast(company_id: int, forecast_type: str, periods: int = 3, sector: str = "general") -> dict:
    """Run a specific forecast type."""
    econ_repo.log_economy_action(company_id, f"forecast.{forecast_type}", details=f"periods={periods}")

    if forecast_type == "industry":
        return {"forecast_type": forecast_type, "results": markets_engine.industry_forecast(company_id, sector, periods)}
    elif forecast_type == "revenue":
        return {"forecast_type": forecast_type, "results": finance_engine.revenue_forecast(company_id, periods)}
    elif forecast_type == "demand":
        return {"forecast_type": forecast_type, "results": markets_engine.demand_forecast(company_id, periods)}
    elif forecast_type == "price":
        return {"forecast_type": forecast_type, "results": markets_engine.predict_prices(company_id)}
    elif forecast_type == "all":
        return {
            "revenue": finance_engine.revenue_forecast(company_id, periods),
            "industry": markets_engine.industry_forecast(company_id, sector, periods),
            "demand": markets_engine.demand_forecast(company_id, periods),
            "prices": markets_engine.predict_prices(company_id),
        }
    else:
        raise ValueError(f"Unknown forecast type: {forecast_type}. Choose: {list(FORECAST_TYPES)} + all")


def forecast_history(company_id: int, forecast_type: str | None = None) -> list[dict]:
    return econ_repo.list_forecasts(company_id, forecast_type)

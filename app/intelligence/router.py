"""Autonomous Business Intelligence API routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.deps import require_auth
from app.intelligence import repository as intel_repo
from app.intelligence.forecasting import engine as forecast_engine
from app.intelligence.optimization import engine as opt_engine
from app.intelligence.predictions import engine as pred_engine
from app.intelligence.recommendations import engine as rec_engine
from app.intelligence.simulations import engine as sim_engine

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


class SimulateRequest(BaseModel):
    scenario_type: str
    params: dict = {}


class ForecastRequest(BaseModel):
    periods: int = 3


@router.get("/predictions")
def get_predictions(ctx=Depends(require_auth)):
    """Run all prediction models and return results."""
    return pred_engine.run_all_predictions(ctx.company_id)


@router.get("/predictions/{prediction_type}")
def get_prediction_type(prediction_type: str, ctx=Depends(require_auth)):
    """Run a single prediction model: revenue | sales | customer_growth | inventory"""
    runners = {
        "revenue": pred_engine.predict_revenue,
        "sales": pred_engine.predict_sales,
        "customer_growth": pred_engine.predict_customer_growth,
        "inventory": pred_engine.predict_inventory,
    }
    runner = runners.get(prediction_type)
    if not runner:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown type. Choose: {list(runners)}",
        )
    return runner(ctx.company_id)


@router.get("/predictions/history/{prediction_type}")
def prediction_history(prediction_type: str, ctx=Depends(require_auth)):
    return intel_repo.list_predictions(ctx.company_id, prediction_type)


@router.get("/recommendations")
def get_recommendations(ctx=Depends(require_auth)):
    """Run all recommendation engines and return prioritised suggestions."""
    return rec_engine.run_all_recommendations(ctx.company_id)


@router.get("/recommendations/{category}")
def get_recommendations_by_category(category: str, ctx=Depends(require_auth)):
    """Get recommendations for one category: products | marketing | cost_reduction | employees"""
    runners = {
        "products": rec_engine.recommend_products,
        "marketing": rec_engine.recommend_marketing,
        "cost_reduction": rec_engine.recommend_cost_reduction,
        "employees": rec_engine.recommend_employees,
    }
    runner = runners.get(category)
    if not runner:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown category. Choose: {list(runners)}",
        )
    return runner(ctx.company_id)


@router.get("/optimizations")
def get_optimizations(ctx=Depends(require_auth)):
    return opt_engine.run_all_optimizations(ctx.company_id)


@router.post("/simulate")
def run_simulation(body: SimulateRequest, ctx=Depends(require_auth)):
    """
    Run a what-if simulation.

    scenario_type: budget | expansion | what_if

    Example params for each:
      budget:    { income_change_pct: 20, expense_change_pct: -10 }
      expansion: { new_hires: 2, new_markets: 1, monthly_hire_cost: 25000 }
      what_if:   { conversion_boost_pct: 15, price_increase_pct: 5, cost_cut_pct: 5 }
    """
    try:
        return sim_engine.run_simulation(ctx.company_id, body.scenario_type, body.params)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/simulations")
def list_simulations(ctx=Depends(require_auth)):
    return intel_repo.list_simulations(ctx.company_id)


@router.get("/forecast")
def get_forecast(periods: int = 3, ctx=Depends(require_auth)):
    if periods < 1 or periods > 12:
        raise HTTPException(status_code=400, detail="periods must be 1–12")
    return forecast_engine.forecast_next_periods(ctx.company_id, periods)


@router.get("/risks")
def get_risks(ctx=Depends(require_auth)):
    return forecast_engine.risk_indicators(ctx.company_id)


@router.get("/opportunities")
def get_opportunities(ctx=Depends(require_auth)):
    return forecast_engine.growth_opportunities(ctx.company_id)


@router.get("/dashboard")
def intelligence_dashboard(ctx=Depends(require_auth)):
    """Full BI dashboard — predictions, recommendations, risks, opportunities."""
    intel_repo.log_intelligence_action(ctx.company_id, "dashboard.view")
    return {
        "predictions": pred_engine.run_all_predictions(ctx.company_id),
        "recommendations": rec_engine.run_all_recommendations(ctx.company_id),
        "risks": forecast_engine.risk_indicators(ctx.company_id),
        "opportunities": forecast_engine.growth_opportunities(ctx.company_id),
        "forecast": forecast_engine.forecast_next_periods(ctx.company_id, 3),
        "optimizations": opt_engine.run_all_optimizations(ctx.company_id),
    }

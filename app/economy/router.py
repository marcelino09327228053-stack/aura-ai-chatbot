"""Aura Economic Network API routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.deps import require_auth
from app.economy import repository as econ_repo
from app.economy import reports as report_service
from app.economy.finance import engine as finance_engine
from app.economy.forecasting import engine as forecast_engine
from app.economy.markets import engine as markets_engine
from app.economy.partnerships import engine as partnership_engine
from app.economy.trading import engine as trading_engine

router = APIRouter(prefix="/economy", tags=["economy"])


class ForecastRequest(BaseModel):
    forecast_type: str = "all"
    periods: int = 3
    sector: str = "general"


class MarketRequest(BaseModel):
    sector: str = "general"


class PartnerRequest(BaseModel):
    partner_type: str = "supplier"
    name: str
    contact: str = ""
    rating: float = 0
    notes: str = ""


class JointProjectRequest(BaseModel):
    partner_id: int | None = None
    title: str
    description: str = ""
    budget: float = 0
    start_date: str = ""
    end_date: str = ""


class ReportRequest(BaseModel):
    report_type: str = "all"
    sector: str = "general"


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard")
def economy_dashboard(ctx=Depends(require_auth)):
    econ_repo.log_economy_action(ctx.company_id, "dashboard.view", ctx.user_id)
    return {
        "markets": markets_engine.analyze_market(ctx.company_id),
        "cash_flow": finance_engine.cash_flow_analysis(ctx.company_id),
        "opportunities": markets_engine.detect_opportunities(ctx.company_id),
        "growth": markets_engine.growth_analysis(ctx.company_id),
        "partners": partnership_engine.collaboration_tools(ctx.company_id),
        "trade_score": trading_engine.trade_opportunity_score(ctx.company_id),
    }


# ── Markets ───────────────────────────────────────────────────────────────────

@router.get("/markets")
def get_markets(ctx=Depends(require_auth)):
    """Market analysis, trends, competitor intel, and stored markets."""
    econ_repo.log_economy_action(ctx.company_id, "markets.view", ctx.user_id)
    return {
        "analysis": markets_engine.analyze_market(ctx.company_id),
        "stored_markets": econ_repo.list_markets(ctx.company_id),
        "industry_trends": markets_engine.INDUSTRY_TRENDS[:6],
        "competitor_analysis": markets_engine.competitor_analysis(ctx.company_id),
        "growth_analysis": markets_engine.growth_analysis(ctx.company_id),
        "opportunities": econ_repo.list_opportunities(ctx.company_id),
    }


@router.post("/markets/analyze")
def analyze_market(body: MarketRequest, ctx=Depends(require_auth)):
    return markets_engine.analyze_market(ctx.company_id, body.sector)


@router.get("/markets/trends")
def industry_trends():
    return markets_engine.INDUSTRY_TRENDS


@router.get("/markets/competitor")
def competitor_analysis(ctx=Depends(require_auth)):
    return markets_engine.competitor_analysis(ctx.company_id)


@router.get("/markets/opportunities")
def list_opportunities(ctx=Depends(require_auth)):
    return markets_engine.detect_opportunities(ctx.company_id)


@router.get("/markets/prices")
def price_predictions(ctx=Depends(require_auth)):
    return markets_engine.predict_prices(ctx.company_id)


# ── Forecasting ───────────────────────────────────────────────────────────────

@router.post("/forecast")
def run_forecast(body: ForecastRequest, ctx=Depends(require_auth)):
    """
    Run economic forecasts.

    forecast_type: revenue | industry | demand | price | all
    """
    if body.periods < 1 or body.periods > 12:
        raise HTTPException(status_code=400, detail="periods must be 1–12")
    try:
        return forecast_engine.run_forecast(
            ctx.company_id, body.forecast_type, body.periods, body.sector
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/forecast/history")
def forecast_history(forecast_type: str | None = None, ctx=Depends(require_auth)):
    return forecast_engine.forecast_history(ctx.company_id, forecast_type)


# ── Financial Intelligence ──────────────────────────────────────────────────────

@router.get("/finance/cash-flow")
def cash_flow(ctx=Depends(require_auth)):
    return finance_engine.cash_flow_analysis(ctx.company_id)


@router.get("/finance/budget")
def budget_optimization(ctx=Depends(require_auth)):
    return finance_engine.budget_optimization(ctx.company_id)


@router.get("/finance/investment-plan")
def investment_plan(available_capital: float | None = None, ctx=Depends(require_auth)):
    return finance_engine.investment_planning(ctx.company_id, available_capital)


@router.get("/finance/revenue-forecast")
def revenue_forecast(periods: int = 6, ctx=Depends(require_auth)):
    return finance_engine.revenue_forecast(ctx.company_id, periods)


# ── Partnerships ──────────────────────────────────────────────────────────────

@router.get("/partners")
def list_partners(partner_type: str | None = None, ctx=Depends(require_auth)):
    return econ_repo.list_partners(ctx.company_id, partner_type)


@router.post("/partners")
def add_partner(body: PartnerRequest, ctx=Depends(require_auth)):
    if body.partner_type == "supplier":
        return partnership_engine.add_supplier(
            ctx.company_id, body.name, body.contact, body.rating, body.notes
        )
    return partnership_engine.add_partner_company(ctx.company_id, body.name, body.contact, body.notes)


@router.get("/partners/suppliers")
def supplier_summary(ctx=Depends(require_auth)):
    return partnership_engine.supplier_management_summary(ctx.company_id)


@router.get("/partners/collaboration")
def collaboration_tools(ctx=Depends(require_auth)):
    return partnership_engine.collaboration_tools(ctx.company_id)


@router.get("/projects")
def list_projects(ctx=Depends(require_auth)):
    return econ_repo.list_joint_projects(ctx.company_id)


@router.post("/projects")
def create_project(body: JointProjectRequest, ctx=Depends(require_auth)):
    return partnership_engine.create_joint_project(ctx.company_id, body.model_dump())


# ── Trading ───────────────────────────────────────────────────────────────────

@router.get("/trading/benchmarks")
def price_benchmarks(ctx=Depends(require_auth)):
    return trading_engine.price_benchmarks(ctx.company_id)


@router.get("/trading/score")
def trade_score(ctx=Depends(require_auth)):
    return trading_engine.trade_opportunity_score(ctx.company_id)


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports")
def get_reports(report_type: str | None = None, ctx=Depends(require_auth)):
    """Generate or list executive reports."""
    econ_repo.log_economy_action(ctx.company_id, "reports.view", ctx.user_id)
    if report_type:
        generators = {
            "market": lambda: report_service.generate_market_report(ctx.company_id),
            "financial": lambda: report_service.generate_financial_report(ctx.company_id),
            "strategic": lambda: report_service.generate_strategic_report(ctx.company_id),
            "risk": lambda: report_service.generate_risk_report(ctx.company_id),
        }
        gen = generators.get(report_type)
        if not gen:
            raise HTTPException(status_code=400, detail=f"Unknown type. Choose: {list(generators)}")
        return gen()
    return {
        "recent": econ_repo.list_reports(ctx.company_id),
        "available_types": ["market", "financial", "strategic", "risk"],
    }


@router.post("/reports")
def generate_report(body: ReportRequest, ctx=Depends(require_auth)):
    if body.report_type == "all":
        return report_service.generate_all_reports(ctx.company_id, body.sector)
    generators = {
        "market": lambda: report_service.generate_market_report(ctx.company_id, body.sector),
        "financial": report_service.generate_financial_report,
        "strategic": report_service.generate_strategic_report,
        "risk": report_service.generate_risk_report,
    }
    gen = generators.get(body.report_type)
    if not gen:
        raise HTTPException(status_code=400, detail=f"Unknown type. Choose: {list(generators)} + all")
    return gen(ctx.company_id) if body.report_type != "market" else gen()


# ── Audit ─────────────────────────────────────────────────────────────────────

@router.get("/audit")
def audit_log(limit: int = 50, ctx=Depends(require_auth)):
    return econ_repo.list_audit(ctx.company_id, min(limit, 100))

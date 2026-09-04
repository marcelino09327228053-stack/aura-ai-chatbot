"""Aura Corporation API routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.deps import require_auth
from app.corporation import repository as corp_repo
from app.corporation.decision_engine import engine as decision_engine
from app.corporation.executives import agents as exec_agents
from app.corporation.investments import engine as invest_engine
from app.corporation.negotiations import engine as neg_engine
from app.corporation.risk_management import engine as risk_engine

router = APIRouter(prefix="/corporation", tags=["corporation"])


# ── Request models ────────────────────────────────────────────────────────────

class AgentRequest(BaseModel):
    agent_role: str
    question: str | None = None


class DecisionRequest(BaseModel):
    decision_type: str
    context: dict = {}


class SupplierNegotiationRequest(BaseModel):
    supplier_name: str
    product: str
    current_price: float
    desired_discount_pct: float = 10.0


class CustomerProposalRequest(BaseModel):
    customer_name: str
    deal_value: float
    proposal_type: str = "standard"


class ContractRequest(BaseModel):
    contract_type: str


class ROIRequest(BaseModel):
    name: str
    investment_type: str = "capex"
    amount: float
    expected_annual_return: float
    duration_years: float = 1.0
    risk_level: str = "medium"


class BudgetRequest(BaseModel):
    total_budget: float
    stage: str = "growth"


class CapitalPlanRequest(BaseModel):
    growth_target_pct: float = 20.0
    months: int = 12


class ApproveDecisionRequest(BaseModel):
    decision_id: int


# ── Executive Dashboard ───────────────────────────────────────────────────────

@router.get("/dashboard")
def corporation_dashboard(ctx=Depends(require_auth)):
    """Full executive dashboard — analysis, risks, investments, decisions."""
    corp_repo.log_corp_action(ctx.company_id, "dashboard.view")
    analysis = decision_engine.analyze_business(ctx.company_id)
    risks = risk_engine.run_full_risk_assessment(ctx.company_id)
    investments = invest_engine.list_investments_summary(ctx.company_id)
    recent_decisions = corp_repo.list_decisions(ctx.company_id, limit=5)

    return {
        "business_analysis": analysis,
        "risk_summary": {
            "overall_level": risks["overall_risk_level"],
            "critical_count": risks["critical_count"],
            "total_risks": risks["total_risks"],
            "top_risks": risks["top_risks"][:3],
        },
        "investments": investments,
        "recent_decisions": recent_decisions,
        "investment_recommendations": decision_engine.recommend_investments(ctx.company_id),
    }


# ── Executive Agents ──────────────────────────────────────────────────────────

@router.get("/agents")
def list_agents():
    """List all available executive agents."""
    return [
        {
            "role": role,
            "title": info["title"],
            "emoji": info["emoji"],
            "domain": info["domain"],
            "decision_types": info["decision_types"],
        }
        for role, info in exec_agents.EXECUTIVE_AGENTS.items()
    ]


@router.post("/agents/run")
def run_agent(body: AgentRequest, ctx=Depends(require_auth)):
    """Run a specific executive agent."""
    try:
        return exec_agents.run_agent(ctx.company_id, body.agent_role, body.question)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/agents/briefing")
def run_all_agents(ctx=Depends(require_auth)):
    """Run all five executive agents for a full C-suite briefing."""
    return exec_agents.run_all_agents(ctx.company_id)


@router.get("/agents/decisions")
def list_decisions(agent_role: str | None = None, ctx=Depends(require_auth)):
    return corp_repo.list_decisions(ctx.company_id, agent_role)


@router.post("/agents/decisions/{decision_id}/approve")
def approve_decision(decision_id: int, ctx=Depends(require_auth)):
    result = corp_repo.approve_decision(decision_id, ctx.company_id, ctx.user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Decision not found")
    corp_repo.log_corp_action(ctx.company_id, "decision.approve", details=f"id={decision_id}")
    return result


# ── Decision Engine ───────────────────────────────────────────────────────────

@router.post("/decisions")
def make_decision(body: DecisionRequest, ctx=Depends(require_auth)):
    """
    Run a specific decision type.

    decision_type: business_analysis | investment | expansion
    """
    try:
        return decision_engine.run_decision(ctx.company_id, body.decision_type, body.context)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/decisions/analysis")
def business_analysis(ctx=Depends(require_auth)):
    return decision_engine.analyze_business(ctx.company_id)


@router.get("/decisions/investment-recommendations")
def investment_recommendations(ctx=Depends(require_auth)):
    return decision_engine.recommend_investments(ctx.company_id)


@router.get("/decisions/expansion")
def expansion_plan(ctx=Depends(require_auth)):
    return decision_engine.plan_expansion(ctx.company_id)


# ── Negotiations ──────────────────────────────────────────────────────────────

@router.get("/negotiations")
def list_negotiations(status: str | None = None, ctx=Depends(require_auth)):
    return corp_repo.list_negotiations(ctx.company_id, status)


@router.post("/negotiations/supplier")
def supplier_negotiation(body: SupplierNegotiationRequest, ctx=Depends(require_auth)):
    return neg_engine.negotiate_supplier(
        ctx.company_id,
        body.supplier_name, body.product,
        body.current_price, body.desired_discount_pct,
    )


@router.post("/negotiations/customer-proposal")
def customer_proposal(body: CustomerProposalRequest, ctx=Depends(require_auth)):
    return neg_engine.generate_customer_proposal(
        ctx.company_id,
        body.customer_name, body.deal_value, body.proposal_type,
    )


@router.post("/negotiations/contract-recommendation")
def contract_recommendation(body: ContractRequest, ctx=Depends(require_auth)):
    try:
        return neg_engine.recommend_contract(ctx.company_id, body.contract_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ── Investments ───────────────────────────────────────────────────────────────

@router.get("/investments")
def list_investments(ctx=Depends(require_auth)):
    return invest_engine.list_investments_summary(ctx.company_id)


@router.post("/investments/roi")
def calculate_roi(body: ROIRequest, ctx=Depends(require_auth)):
    try:
        return invest_engine.calculate_roi(
            ctx.company_id,
            body.name, body.investment_type,
            body.amount, body.expected_annual_return,
            body.duration_years, body.risk_level,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/investments/budget-allocation")
def budget_allocation(body: BudgetRequest, ctx=Depends(require_auth)):
    try:
        return invest_engine.allocate_budget(ctx.company_id, body.total_budget, body.stage)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/investments/capital-plan")
def capital_plan(body: CapitalPlanRequest, ctx=Depends(require_auth)):
    return invest_engine.capital_plan(ctx.company_id, body.growth_target_pct, body.months)


# ── Risk Management ───────────────────────────────────────────────────────────

@router.get("/risks")
def get_risks(ctx=Depends(require_auth)):
    """Full risk assessment across all four categories."""
    return risk_engine.run_full_risk_assessment(ctx.company_id)


@router.get("/risks/register")
def risk_register(ctx=Depends(require_auth)):
    return risk_engine.get_risk_register(ctx.company_id)


@router.get("/risks/{risk_type}")
def risks_by_type(risk_type: str, ctx=Depends(require_auth)):
    runners = {
        "financial": risk_engine.assess_financial_risks,
        "operational": risk_engine.assess_operational_risks,
        "security": risk_engine.assess_security_risks,
        "compliance": risk_engine.assess_compliance_risks,
    }
    runner = runners.get(risk_type)
    if not runner:
        raise HTTPException(status_code=400, detail=f"Unknown type. Choose: {list(runners)}")
    return runner(ctx.company_id)


# ── Audit ─────────────────────────────────────────────────────────────────────

@router.get("/audit")
def audit_log(limit: int = 50, ctx=Depends(require_auth)):
    return corp_repo.list_audit(ctx.company_id, min(limit, 100))

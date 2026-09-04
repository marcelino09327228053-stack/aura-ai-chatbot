"""Aura Enterprise API routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.deps import require_auth
from app.enterprise import repository as ent_repo
from app.enterprise.compliance import engine as compliance_engine
from app.enterprise.forecasting import engine as forecast_engine
from app.enterprise.governance import engine as gov_engine
from app.enterprise.strategy import engine as strategy_engine

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


# ── Request models ────────────────────────────────────────────────────────────

class GoalRequest(BaseModel):
    title: str
    description: str = ""
    category: str = "growth"
    target_value: float = 0
    current_value: float = 0
    unit: str = ""
    deadline: str = ""
    priority: str = "medium"


class GoalProgressRequest(BaseModel):
    current_value: float
    status: str | None = None


class KPIRequest(BaseModel):
    name: str
    category: str = "financial"
    value: float = 0
    target: float = 0
    unit: str = ""
    period: str = "monthly"
    trend: str = "stable"


class PlanRequest(BaseModel):
    title: str
    plan_type: str = "annual"
    description: str = ""
    start_date: str = ""
    end_date: str = ""
    budget: float = 0
    milestones: list[dict] = []


class PolicyRequest(BaseModel):
    title: str
    category: str = "general"
    content: str
    version: str = "1.0"
    effective_date: str = ""


class ApprovalRequest(BaseModel):
    request_type: str = "expense"
    title: str
    description: str = ""
    amount: float = 0
    assigned_to: int | None = None


class ApprovalDecision(BaseModel):
    decision: str
    note: str = ""
    amount: float = 0


class TaxReportRequest(BaseModel):
    country_code: str = "PH"
    period: str = "monthly"


class DocValidateRequest(BaseModel):
    document_type: str
    content: str


class ComplianceRiskRequest(BaseModel):
    has_employees: bool = False
    processes_personal_data: bool = True
    annual_revenue: float = 0


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard")
def enterprise_dashboard(ctx=Depends(require_auth)):
    """Full executive dashboard — health, KPIs, forecasts, governance summary."""
    ent_repo.log_enterprise_action(ctx.company_id, "dashboard.view", ctx.user_id)
    return {
        "health": strategy_engine.company_health_score(ctx.company_id),
        "kpis": strategy_engine.refresh_kpis(ctx.company_id),
        "goals": strategy_engine.score_goals(ctx.company_id),
        "recommendations": strategy_engine.generate_strategic_recommendations(ctx.company_id),
        "governance": gov_engine.governance_summary(ctx.company_id),
        "compliance": compliance_engine.run_regulatory_checks(ctx.company_id),
    }


# ── Strategy — Goals ──────────────────────────────────────────────────────────

@router.get("/goals")
def list_goals(status: str | None = None, ctx=Depends(require_auth)):
    return strategy_engine.score_goals(ctx.company_id)


@router.post("/goals")
def create_goal(body: GoalRequest, ctx=Depends(require_auth)):
    goal = ent_repo.create_goal(ctx.company_id, body.model_dump())
    ent_repo.log_enterprise_action(ctx.company_id, "goal.create", ctx.user_id, "goal", goal["id"], body.title)
    return goal


@router.patch("/goals/{goal_id}")
def update_goal(goal_id: int, body: GoalProgressRequest, ctx=Depends(require_auth)):
    return ent_repo.update_goal_progress(goal_id, ctx.company_id, body.current_value, body.status)


# ── Strategy — KPIs ───────────────────────────────────────────────────────────

@router.get("/kpis")
def list_kpis(category: str | None = None, ctx=Depends(require_auth)):
    return ent_repo.list_kpis(ctx.company_id, category)


@router.post("/kpis/refresh")
def refresh_kpis(ctx=Depends(require_auth)):
    """Auto-generate KPI snapshot from live business data."""
    return strategy_engine.refresh_kpis(ctx.company_id)


@router.post("/kpis")
def record_kpi(body: KPIRequest, ctx=Depends(require_auth)):
    return ent_repo.record_kpi(ctx.company_id, body.model_dump())


# ── Strategy — Plans ──────────────────────────────────────────────────────────

@router.get("/plans")
def list_plans(ctx=Depends(require_auth)):
    return ent_repo.list_plans(ctx.company_id)


@router.post("/plan")
def create_plan(body: PlanRequest, ctx=Depends(require_auth)):
    plan = ent_repo.create_plan(ctx.company_id, body.model_dump(), ctx.user_id)
    ent_repo.log_enterprise_action(ctx.company_id, "plan.create", ctx.user_id, "plan", plan["id"], body.title)
    return plan


@router.get("/recommendations")
def strategic_recommendations(ctx=Depends(require_auth)):
    return strategy_engine.generate_strategic_recommendations(ctx.company_id)


@router.get("/health")
def company_health(ctx=Depends(require_auth)):
    return strategy_engine.company_health_score(ctx.company_id)


# ── Forecasting ───────────────────────────────────────────────────────────────

@router.get("/forecast")
def get_forecasts(periods: int = 3, ctx=Depends(require_auth)):
    if periods < 1 or periods > 12:
        raise HTTPException(status_code=400, detail="periods must be 1–12")
    return forecast_engine.run_all_forecasts(ctx.company_id, periods)


@router.get("/forecast/{forecast_type}")
def get_forecast_type(forecast_type: str, periods: int = 3, ctx=Depends(require_auth)):
    runners = {
        "revenue": forecast_engine.forecast_revenue,
        "expenses": forecast_engine.forecast_expenses,
        "hiring": forecast_engine.forecast_hiring,
        "expansion": forecast_engine.forecast_expansion,
    }
    runner = runners.get(forecast_type)
    if not runner:
        raise HTTPException(status_code=400, detail=f"Unknown type. Choose: {list(runners)}")
    return runner(ctx.company_id, periods)


@router.get("/forecast/history")
def forecast_history(forecast_type: str | None = None, ctx=Depends(require_auth)):
    return ent_repo.list_forecasts(ctx.company_id, forecast_type)


# ── Governance — Policies ─────────────────────────────────────────────────────

@router.get("/policies")
def list_policies(category: str | None = None, ctx=Depends(require_auth)):
    return ent_repo.list_policies(ctx.company_id, category)


@router.post("/policies")
def create_policy(body: PolicyRequest, ctx=Depends(require_auth)):
    policy = ent_repo.create_policy(ctx.company_id, body.model_dump(), ctx.user_id)
    ent_repo.log_enterprise_action(ctx.company_id, "policy.create", ctx.user_id, "policy", policy["id"])
    return policy


@router.post("/policies/seed-defaults")
def seed_default_policies(ctx=Depends(require_auth)):
    return gov_engine.ensure_default_policies(ctx.company_id)


# ── Governance — Approvals ────────────────────────────────────────────────────

@router.get("/approvals")
def list_approvals(status: str | None = None, ctx=Depends(require_auth)):
    return ent_repo.list_approvals(ctx.company_id, status)


@router.post("/approvals")
def submit_approval(body: ApprovalRequest, ctx=Depends(require_auth)):
    try:
        return gov_engine.submit_approval_request(
            ctx.company_id, body.model_dump(), ctx.user_id, getattr(ctx, "role", "employee")
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.patch("/approvals/{approval_id}")
def decide_approval(approval_id: int, body: ApprovalDecision, ctx=Depends(require_auth)):
    try:
        return gov_engine.decide_on_approval(
            ctx.company_id, approval_id, body.decision, body.note,
            ctx.user_id, getattr(ctx, "role", "owner"), body.amount
        )
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/governance")
def governance_summary(ctx=Depends(require_auth)):
    return gov_engine.governance_summary(ctx.company_id)


@router.get("/roles")
def list_roles():
    return [
        {"role": k, **{kk: vv for kk, vv in v.items() if kk != "approval_limit"},
         "approval_limit": v["approval_limit"] if v["approval_limit"] != float("inf") else "unlimited"}
        for k, v in gov_engine.ENTERPRISE_ROLES.items()
    ]


# ── Compliance ────────────────────────────────────────────────────────────────

@router.get("/compliance")
def regulatory_checks(ctx=Depends(require_auth)):
    return compliance_engine.run_regulatory_checks(ctx.company_id)


@router.post("/compliance/tax-report")
def tax_report(body: TaxReportRequest, ctx=Depends(require_auth)):
    return compliance_engine.generate_tax_report(ctx.company_id, body.country_code, body.period)


@router.post("/compliance/validate-document")
def validate_document(body: DocValidateRequest, ctx=Depends(require_auth)):
    if not body.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    try:
        return compliance_engine.validate_document(ctx.company_id, body.document_type, body.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/compliance/history")
def compliance_history(ctx=Depends(require_auth)):
    return ent_repo.list_compliance_checks(ctx.company_id)


# ── Audit ─────────────────────────────────────────────────────────────────────

@router.get("/audit")
def audit_log(limit: int = 50, ctx=Depends(require_auth)):
    return ent_repo.list_audit_log(ctx.company_id, min(limit, 100))

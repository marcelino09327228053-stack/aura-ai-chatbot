"""Aura Autonomous Ecosystem API routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.deps import require_auth
from app.ecosystem import repository as eco_repo
from app.ecosystem.automation import engine as automation_engine
from app.ecosystem.innovation import engine as innovation_engine
from app.ecosystem.intelligence import engine as intelligence_engine
from app.ecosystem.research import engine as research_engine
from app.ecosystem.simulations import engine as simulation_engine

router = APIRouter(prefix="/ecosystem", tags=["ecosystem"])


class SimulateRequest(BaseModel):
    scenario_type: str
    params: dict = {}


class ResearchRequest(BaseModel):
    sector: str = "general"


class KnowledgeRequest(BaseModel):
    source_agent: str
    topic: str
    content: str


class AutomationRequest(BaseModel):
    suite: bool = True
    job_type: str | None = None


# ── Status ────────────────────────────────────────────────────────────────────

@router.get("/status")
def ecosystem_status(ctx=Depends(require_auth)):
    """Full ecosystem operational status."""
    return intelligence_engine.ecosystem_status(ctx.company_id)


@router.get("/dashboard")
def ecosystem_dashboard(ctx=Depends(require_auth)):
    status = intelligence_engine.ecosystem_status(ctx.company_id)
    return {
        "status": status,
        "recent_research": eco_repo.list_research(ctx.company_id)[:5],
        "top_innovations": eco_repo.list_innovations(ctx.company_id)[:5],
        "recent_simulations": eco_repo.list_simulations(ctx.company_id, 5),
        "coordinated_decisions": intelligence_engine.coordinate_decisions(ctx.company_id),
    }


# ── Research ──────────────────────────────────────────────────────────────────

@router.get("/research")
def get_research(sector: str = "general", refresh: bool = True, ctx=Depends(require_auth)):
    """Run or list research (markets, competitors, opportunities)."""
    if refresh:
        return research_engine.run_all_research(ctx.company_id, sector)
    return {
        "history": eco_repo.list_research(ctx.company_id),
        "by_type": {
            "new_markets": eco_repo.list_research(ctx.company_id, "new_markets"),
            "competitors": eco_repo.list_research(ctx.company_id, "competitors"),
            "opportunities": eco_repo.list_research(ctx.company_id, "opportunities"),
        },
    }


@router.post("/research")
def run_research(body: ResearchRequest, ctx=Depends(require_auth)):
    return research_engine.run_all_research(ctx.company_id, body.sector)


@router.get("/research/history")
def research_history(research_type: str | None = None, ctx=Depends(require_auth)):
    return eco_repo.list_research(ctx.company_id, research_type)


# ── Innovations ───────────────────────────────────────────────────────────────

@router.get("/innovations")
def get_innovations(refresh: bool = True, ctx=Depends(require_auth)):
    """Generate or list innovation suggestions."""
    if refresh:
        return innovation_engine.run_all_innovations(ctx.company_id)
    return eco_repo.list_innovations(ctx.company_id)


@router.get("/innovations/{category}")
def innovations_by_category(category: str, ctx=Depends(require_auth)):
    runners = {
        "product": innovation_engine.suggest_products,
        "service": innovation_engine.suggest_services,
        "workflow": innovation_engine.improve_workflows,
        "technology": innovation_engine.recommend_technologies,
    }
    runner = runners.get(category)
    if not runner:
        raise HTTPException(status_code=400, detail=f"Choose: {list(runners)}")
    return runner(ctx.company_id)


# ── Simulations ───────────────────────────────────────────────────────────────

@router.post("/simulate")
def run_simulate(body: SimulateRequest, ctx=Depends(require_auth)):
    """
    Run a simulation scenario.

    scenario_type: business | expansion | financial | risk
    """
    try:
        return simulation_engine.run_simulation(ctx.company_id, body.scenario_type, body.params)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/simulations")
def list_simulations(ctx=Depends(require_auth)):
    return eco_repo.list_simulations(ctx.company_id)


# ── Automation ────────────────────────────────────────────────────────────────

@router.post("/automation/run")
def run_automation(body: AutomationRequest, ctx=Depends(require_auth)):
    if body.suite or not body.job_type:
        return automation_engine.run_automation_suite(ctx.company_id, ctx.user_id)
    runners = {
        "reporting": automation_engine.automatic_reporting,
        "delegation": automation_engine.task_delegation,
        "workflow": automation_engine.optimize_workflows,
        "notifications": lambda cid, uid=None: automation_engine.smart_notifications(cid),
    }
    runner = runners.get(body.job_type)
    if not runner:
        raise HTTPException(status_code=400, detail=f"Choose: {list(runners)}")
    if body.job_type == "notifications":
        return runner(ctx.company_id)
    return runner(ctx.company_id, ctx.user_id)


@router.get("/automation/jobs")
def list_jobs(ctx=Depends(require_auth)):
    return eco_repo.list_automation_jobs(ctx.company_id)


@router.get("/notifications")
def list_notifications(unread_only: bool = False, ctx=Depends(require_auth)):
    return eco_repo.list_notifications(ctx.company_id, unread_only)


@router.post("/notifications/{notification_id}/read")
def mark_read(notification_id: int, ctx=Depends(require_auth)):
    eco_repo.mark_notification_read(ctx.company_id, notification_id)
    return {"ok": True}


# ── Intelligence Hub ──────────────────────────────────────────────────────────

@router.post("/intelligence/connect")
def connect_agents(ctx=Depends(require_auth)):
    return intelligence_engine.connect_all_agents(ctx.company_id)


@router.get("/intelligence/performance")
def agent_performance(ctx=Depends(require_auth)):
    return intelligence_engine.monitor_performance(ctx.company_id)


@router.get("/intelligence/decisions")
def coordinated_decisions(ctx=Depends(require_auth)):
    return intelligence_engine.coordinate_decisions(ctx.company_id)


@router.post("/intelligence/knowledge")
def share_knowledge(body: KnowledgeRequest, ctx=Depends(require_auth)):
    return intelligence_engine.share_knowledge(
        ctx.company_id, body.source_agent, body.topic, body.content
    )


@router.get("/intelligence/knowledge")
def list_knowledge(ctx=Depends(require_auth)):
    return eco_repo.list_knowledge(ctx.company_id)


# ── Audit ─────────────────────────────────────────────────────────────────────

@router.get("/audit")
def audit_log(limit: int = 50, ctx=Depends(require_auth)):
    return eco_repo.list_audit(ctx.company_id, min(limit, 100))

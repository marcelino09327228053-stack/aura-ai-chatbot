"""Aura Civilization Layer API routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.deps import require_auth
from app.civilization import repository as civ_repo
from app.civilization.economy import engine as economy_engine
from app.civilization.education import engine as education_engine
from app.civilization.governance import engine as governance_engine
from app.civilization.infrastructure import engine as infra_engine
from app.civilization.research import engine as research_engine

router = APIRouter(prefix="/civilization", tags=["civilization"])


class PolicyRequest(BaseModel):
    title: str
    category: str = "general"
    content: str


class VoteRequest(BaseModel):
    title: str
    description: str = ""
    options: list[str] = ["Approve", "Reject"]


class CastVoteRequest(BaseModel):
    option: str


class EnrollRequest(BaseModel):
    employee_key: str
    course_title: str
    course_type: str = "training"


class RewardRequest(BaseModel):
    account_key: str
    amount: float
    reason: str
    reward_type: str = "incentive"


class IncentiveRequest(BaseModel):
    account_key: str
    metrics: dict[str, float]


# ── Status ────────────────────────────────────────────────────────────────────

@router.get("/status")
def civilization_status(ctx=Depends(require_auth)):
    """Full civilization layer status."""
    civ_repo.log_civ_action(ctx.company_id, "status.view", user_id=ctx.user_id)
    gov = governance_engine.governance_summary(ctx.company_id)
    edu = education_engine.education_summary(ctx.company_id)
    eco = economy_engine.economy_summary(ctx.company_id)
    infra = infra_engine.infrastructure_summary(ctx.company_id)
    research = civ_repo.list_research(ctx.company_id)

    return {
        "status": "operational",
        "governance": gov["totals"],
        "education": edu["totals"],
        "economy": eco["totals"],
        "infrastructure": {
            "health_score": infra["health_score"],
            "healthy": infra["healthy"],
            "degraded": infra["degraded"],
            **infra["modules"],
            "backups": infra["backup_count"],
        },
        "research_count": len(research),
        "modules": {
            "governance": "active",
            "education": "active",
            "economy": "active",
            "infrastructure": "active",
            "research": "active",
        },
    }


@router.get("/dashboard")
def civilization_dashboard(ctx=Depends(require_auth)):
    return {
        "status": civilization_status(ctx),
        "governance": governance_engine.governance_summary(ctx.company_id),
        "education": education_engine.education_summary(ctx.company_id),
        "economy": economy_engine.economy_summary(ctx.company_id),
        "infrastructure": infra_engine.infrastructure_summary(ctx.company_id),
        "research": research_engine.research_overview(ctx.company_id),
    }


# ── Research ──────────────────────────────────────────────────────────────────

@router.get("/research")
def get_research(refresh: bool = False, ctx=Depends(require_auth)):
    """List or refresh civilization research."""
    return research_engine.research_overview(ctx.company_id, refresh=refresh)


@router.post("/research/run")
def run_research(ctx=Depends(require_auth)):
    return research_engine.run_all_research(ctx.company_id)


# ── Policies ──────────────────────────────────────────────────────────────────

@router.post("/policies")
def create_policy(body: PolicyRequest, ctx=Depends(require_auth)):
    """Create a civilization policy and track the decision."""
    return governance_engine.create_policy(
        ctx.company_id, body.title, body.category, body.content, ctx.user_id,
    )


@router.get("/policies")
def list_policies(ctx=Depends(require_auth)):
    return governance_engine.ensure_default_policies(ctx.company_id)


# ── Analytics ─────────────────────────────────────────────────────────────────

@router.get("/analytics")
def civilization_analytics(ctx=Depends(require_auth)):
    gov = governance_engine.governance_summary(ctx.company_id)
    edu = education_engine.education_summary(ctx.company_id)
    eco = economy_engine.economy_summary(ctx.company_id)
    infra = infra_engine.infrastructure_summary(ctx.company_id)
    research = civ_repo.list_research(ctx.company_id)
    audit = civ_repo.list_audit(ctx.company_id, 20)

    return {
        "governance": gov["totals"],
        "education": edu["totals"],
        "economy": eco["totals"],
        "infrastructure": {
            "health_score": infra["health_score"],
            "nodes": len(infra["nodes"]),
            "backups": infra["backup_count"],
        },
        "research": {
            "total": len(research),
            "by_type": _count_by(research, "research_type"),
        },
        "audit_events": len(audit),
        "recent_audit": audit[:10],
    }


# ── Governance extras ─────────────────────────────────────────────────────────

@router.get("/governance")
def get_governance(ctx=Depends(require_auth)):
    return governance_engine.governance_summary(ctx.company_id)


@router.post("/governance/votes")
def open_vote(body: VoteRequest, ctx=Depends(require_auth)):
    return governance_engine.open_vote(
        ctx.company_id, body.title, body.description, body.options, ctx.user_id,
    )


@router.post("/governance/votes/{vote_id}/cast")
def cast_vote(vote_id: int, body: CastVoteRequest, ctx=Depends(require_auth)):
    result = governance_engine.cast_and_track(ctx.company_id, vote_id, body.option, ctx.user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Vote not found or option invalid")
    return result


@router.post("/governance/votes/{vote_id}/close")
def close_vote(vote_id: int, ctx=Depends(require_auth)):
    result = governance_engine.close_and_record(ctx.company_id, vote_id, ctx.user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Vote not found")
    return result


@router.post("/governance/constitution/{constitution_id}/ratify")
def ratify_constitution(constitution_id: int, ctx=Depends(require_auth)):
    result = civ_repo.ratify_constitution(ctx.company_id, constitution_id)
    if not result:
        raise HTTPException(status_code=404, detail="Constitution not found")
    civ_repo.log_civ_action(ctx.company_id, "governance.ratify", ctx.user_id, str(constitution_id))
    return result


# ── Education ─────────────────────────────────────────────────────────────────

@router.get("/education")
def get_education(ctx=Depends(require_auth)):
    return education_engine.education_summary(ctx.company_id)


@router.post("/education/enroll")
def enroll(body: EnrollRequest, ctx=Depends(require_auth)):
    return education_engine.enroll_employee(
        ctx.company_id, body.employee_key, body.course_title, body.course_type,
    )


@router.post("/education/enroll-catalog")
def enroll_catalog(employee_key: str, ctx=Depends(require_auth)):
    return education_engine.enroll_from_catalog(ctx.company_id, employee_key)


# ── Economy ───────────────────────────────────────────────────────────────────

@router.get("/economy")
def get_economy(ctx=Depends(require_auth)):
    return economy_engine.economy_summary(ctx.company_id)


@router.post("/economy/rewards")
def grant_reward(body: RewardRequest, ctx=Depends(require_auth)):
    return economy_engine.reward_member(
        ctx.company_id, body.account_key, body.amount, body.reason, body.reward_type,
    )


@router.post("/economy/incentives")
def apply_incentives(body: IncentiveRequest, ctx=Depends(require_auth)):
    return economy_engine.apply_incentives(ctx.company_id, body.account_key, body.metrics)


# ── Infrastructure ────────────────────────────────────────────────────────────

@router.get("/infrastructure")
def get_infrastructure(ctx=Depends(require_auth)):
    return infra_engine.infrastructure_summary(ctx.company_id)


@router.post("/infrastructure/backup")
def create_backup(backup_type: str = "full", ctx=Depends(require_auth)):
    return infra_engine.run_backup(ctx.company_id, backup_type)


# ── Audit ─────────────────────────────────────────────────────────────────────

@router.get("/audit")
def get_audit(ctx=Depends(require_auth)):
    return civ_repo.list_audit(ctx.company_id)


def _count_by(items: list[dict], key: str) -> dict:
    counts: dict[str, int] = {}
    for item in items:
        k = item.get(key, "unknown")
        counts[k] = counts.get(k, 0) + 1
    return counts

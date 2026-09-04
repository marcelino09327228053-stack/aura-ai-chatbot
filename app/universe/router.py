"""Aura Universal Platform API routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.deps import require_auth
from app.universe import repository as uni_repo
from app.universe.ai_core import brain as ai_core
from app.universe.collaboration import engine as collab_engine
from app.universe.expansion import engine as expansion_engine
from app.universe.governance import engine as governance_engine
from app.universe.knowledge import engine as knowledge_engine

router = APIRouter(prefix="/universe", tags=["universe"])


class ExpandRequest(BaseModel):
    expansion_type: str
    params: dict = {}


class ProjectRequest(BaseModel):
    title: str
    description: str = ""
    members: list[str] = []
    project_type: str = "team"


class ApprovalRequest(BaseModel):
    approval_type: str
    title: str
    details: str = ""


class MemoryRequest(BaseModel):
    memory_key: str
    content: str
    memory_type: str = "shared"


class ApprovalDecisionRequest(BaseModel):
    approved: bool


# ── Status ────────────────────────────────────────────────────────────────────

@router.get("/status")
def universe_status(ctx=Depends(require_auth)):
    """Full universal platform status."""
    uni_repo.log_universe_action(ctx.company_id, "status.view", user_id=ctx.user_id)
    core = ai_core.ai_core_status(ctx.company_id)
    collab = collab_engine.collaboration_summary(ctx.company_id)
    gov = governance_engine.governance_summary(ctx.company_id)
    exp = expansion_engine.expansion_overview(ctx.company_id)

    return {
        "status": "operational",
        "ai_core": core,
        "collaboration": collab["totals"],
        "governance": {
            "policies": len(gov["policies"]),
            "security_rules": len(gov["security_rules"]),
            "pending_approvals": gov["approvals"]["pending"],
        },
        "expansion": {
            "total": exp["total"],
            "branches": len(exp["branches"]),
            "markets": len(exp["markets"]),
            "deployments": len(exp["deployments"]),
        },
        "modules": {
            "ai_core": "active",
            "collaboration": "active",
            "knowledge": "active",
            "governance": "active",
            "expansion": "active",
        },
    }


@router.get("/dashboard")
def universe_dashboard(ctx=Depends(require_auth)):
    knowledge = knowledge_engine.knowledge_overview(ctx.company_id)
    return {
        "status": universe_status(ctx),
        "knowledge": knowledge,
        "collaboration": collab_engine.collaboration_summary(ctx.company_id),
        "governance": governance_engine.governance_summary(ctx.company_id),
        "expansion": expansion_engine.expansion_overview(ctx.company_id),
        "decisions": ai_core.run_decision_cycle(ctx.company_id),
    }


# ── Knowledge ─────────────────────────────────────────────────────────────────

@router.get("/knowledge")
def get_knowledge(refresh: bool = False, ctx=Depends(require_auth)):
    """Get knowledge base — optionally refresh learning."""
    if refresh:
        return knowledge_engine.run_full_learning(ctx.company_id)
    return knowledge_engine.knowledge_overview(ctx.company_id)


@router.post("/knowledge/learn")
def run_learning(ctx=Depends(require_auth)):
    return knowledge_engine.run_full_learning(ctx.company_id)


@router.post("/knowledge/summary")
def generate_summary(summary_type: str = "daily", ctx=Depends(require_auth)):
    return knowledge_engine.generate_automatic_summary(ctx.company_id, summary_type)


# ── Expansion ─────────────────────────────────────────────────────────────────

@router.post("/expand")
def expand(body: ExpandRequest, ctx=Depends(require_auth)):
    """Plan branch, company, market, or global deployment expansion."""
    result = expansion_engine.run_expansion(ctx.company_id, body.expansion_type, body.params)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    uni_repo.log_universe_action(
        ctx.company_id, f"expansion.{body.expansion_type}",
        user_id=ctx.user_id, details=body.params.get("name", ""),
    )
    return result


@router.get("/expansion")
def list_expansions(ctx=Depends(require_auth)):
    return expansion_engine.expansion_overview(ctx.company_id)


# ── Analytics ─────────────────────────────────────────────────────────────────

@router.get("/analytics")
def universe_analytics(ctx=Depends(require_auth)):
    """Platform-wide analytics across all universe modules."""
    knowledge = knowledge_engine.knowledge_overview(ctx.company_id)
    core = ai_core.ai_core_status(ctx.company_id)
    collab = collab_engine.collaboration_summary(ctx.company_id)
    exp = expansion_engine.expansion_overview(ctx.company_id)
    gov = governance_engine.governance_summary(ctx.company_id)
    audit = uni_repo.list_audit(ctx.company_id, 20)

    return {
        "knowledge": {
            "total_entries": knowledge["total_entries"],
            "by_source": knowledge["by_source"],
            "summaries": len(knowledge["summaries"]),
        },
        "ai_core": {
            "memory_count": core["brain"]["memory_count"],
            "pending_decisions": core["decisions"]["pending"],
            "coordination_links": core["coordination"]["active_links"],
        },
        "collaboration": collab["totals"],
        "expansion": {
            "total": exp["total"],
            "by_type": {
                "branches": len(exp["branches"]),
                "companies": len(exp["companies"]),
                "markets": len(exp["markets"]),
                "deployments": len(exp["deployments"]),
            },
        },
        "governance": {
            "policies": len(gov["policies"]),
            "security_rules": len(gov["security_rules"]),
            "pending_approvals": gov["approvals"]["pending"],
        },
        "audit_events": len(audit),
        "recent_audit": audit[:10],
    }


# ── AI Core ───────────────────────────────────────────────────────────────────

@router.get("/ai-core")
def get_ai_core(ctx=Depends(require_auth)):
    return ai_core.ai_core_status(ctx.company_id)


@router.post("/ai-core/initialize")
def initialize_ai_core(ctx=Depends(require_auth)):
    return ai_core.initialize_brain(ctx.company_id)


@router.post("/ai-core/decisions")
def run_decisions(ctx=Depends(require_auth)):
    return ai_core.run_decision_cycle(ctx.company_id)


@router.get("/ai-core/memory")
def get_memory(ctx=Depends(require_auth)):
    return ai_core.get_shared_memory(ctx.company_id)


@router.post("/ai-core/memory")
def store_memory(body: MemoryRequest, ctx=Depends(require_auth)):
    return ai_core.store_shared_memory(ctx.company_id, body.memory_key, body.content, body.memory_type)


# ── Collaboration ─────────────────────────────────────────────────────────────

@router.get("/collaboration")
def get_collaboration(ctx=Depends(require_auth)):
    collab_engine.ensure_default_projects(ctx.company_id)
    return collab_engine.collaboration_summary(ctx.company_id)


@router.post("/collaboration/projects")
def create_project(body: ProjectRequest, ctx=Depends(require_auth)):
    if body.project_type == "company":
        partner = body.members[0] if body.members else "Partner"
        return collab_engine.create_company_collaboration(ctx.company_id, body.title, partner, body.description)
    return collab_engine.create_team_project(ctx.company_id, body.title, body.description, body.members)


# ── Governance ────────────────────────────────────────────────────────────────

@router.get("/governance")
def get_governance(ctx=Depends(require_auth)):
    return governance_engine.governance_summary(ctx.company_id)


@router.get("/governance/roles")
def get_roles():
    return governance_engine.UNIVERSE_ROLES


@router.post("/governance/approvals")
def submit_approval(body: ApprovalRequest, ctx=Depends(require_auth)):
    return governance_engine.submit_approval(
        ctx.company_id, body.approval_type, body.title, body.details, ctx.user_id,
    )


@router.post("/governance/approvals/{approval_id}")
def decide_approval(approval_id: int, body: ApprovalDecisionRequest, ctx=Depends(require_auth)):
    result = governance_engine.decide_approval(ctx.company_id, approval_id, body.approved, ctx.user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Approval not found")
    return result


# ── Audit ─────────────────────────────────────────────────────────────────────

@router.get("/audit")
def get_audit(ctx=Depends(require_auth)):
    return uni_repo.list_audit(ctx.company_id)

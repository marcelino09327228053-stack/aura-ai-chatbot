"""Aura OS API routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.agents.orchestrator import handle_agent_chat
from app.core.config import agents_enabled
from app.core.deps import require_auth
from app.database import company_repository
from app.infrastructure.monitoring import metrics
from app.infrastructure.team import repository as team_repo
from app.os import permissions, repository as os_repo
from app.os.automation import service as automation_service
from app.os.communication import bus as comm_bus
from app.os.memory import service as memory_service
from app.os.orchestrator import service as orchestrator
from app.os.reasoning import knowledge_engine
from app.os.workflows import engine as workflow_engine

router = APIRouter(prefix="/os", tags=["aura-os"])


class TaskRequest(BaseModel):
    text: str
    task_type: str = "auto"


class WorkflowStart(BaseModel):
    workflow_key: str
    payload: dict | None = None


class AgentMessage(BaseModel):
    from_agent: str
    to_agent: str
    message: str | None = None


class MemoryStore(BaseModel):
    memory_type: str
    subject_key: str = "default"
    summary: str


def _get_role(ctx) -> str:
    company = company_repository.get_company(ctx.company_id)
    owner_id = company["owner_id"] if company else None
    member = team_repo.get_member(ctx.company_id, ctx.user_id) if ctx.user_id else None
    team_role = member["role"] if member else None
    return permissions.resolve_role(ctx.user_id, owner_id, team_role)


def _require_perm(ctx, perm: str) -> None:
    role = _get_role(ctx)
    if not permissions.has_permission(role, perm):
        raise HTTPException(status_code=403, detail=f"Permission denied: {perm}")


@router.get("/dashboard")
def os_dashboard(ctx=Depends(require_auth)):
    _require_perm(ctx, "os.view")
    agents = orchestrator.list_agent_status(ctx.company_id)
    workflows = os_repo.list_workflows(ctx.company_id, status="running")
    memory = memory_service.usage_summary(ctx.company_id)
    health = metrics.get_metrics(ctx.company_id)
    return {
        "os_enabled": agents_enabled(),
        "active_agents": [a for a in agents if a["enabled"]],
        "agent_status": agents,
        "running_workflows": workflows,
        "memory_usage": memory,
        "ai_health": {
            "cpu_percent": health["cpu_percent"],
            "memory_percent": health["memory"]["percent"],
            "error_count": health["error_count"],
            "messages_today": health["api_usage"]["messages_today"],
        },
        "notifications": os_repo.list_notifications(ctx.company_id),
        "permissions_role": _get_role(ctx),
    }


@router.post("/tasks")
async def create_task(body: TaskRequest, ctx=Depends(require_auth)):
    _require_perm(ctx, "os.manage_agents")
    job = orchestrator.create_and_assign_job(ctx.company_id, body.task_type, body.text)
    os_repo.update_job_status(ctx.company_id, job["id"], "running")

    company = company_repository.get_company(ctx.company_id)
    profile = company.get("company_profile", "") if company else ""

    try:
        result = await handle_agent_chat(
            agent_type=job["assigned_agent"],
            text=body.text,
            company_id=ctx.company_id,
            company_profile=profile,
            user_id=str(ctx.user_id),
        )
        completed = orchestrator.complete_job(
            ctx.company_id, job["id"], result.get("reply", ""), success=True
        )
        return {"job": completed, "result": result}
    except Exception as exc:
        orchestrator.complete_job(ctx.company_id, job["id"], str(exc), success=False)
        raise


@router.get("/tasks")
def list_tasks(ctx=Depends(require_auth)):
    _require_perm(ctx, "os.view")
    return os_repo.list_jobs(ctx.company_id)


@router.get("/workflows/templates")
def workflow_templates(ctx=Depends(require_auth)):
    _require_perm(ctx, "os.view")
    return workflow_engine.list_workflow_templates()


@router.post("/workflows")
def start_workflow(body: WorkflowStart, ctx=Depends(require_auth)):
    _require_perm(ctx, "os.run_workflows")
    try:
        wf = workflow_engine.start_workflow(ctx.company_id, body.workflow_key, body.payload)
        return workflow_engine.run_all_steps(ctx.company_id, wf["id"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/workflows")
def list_workflows(ctx=Depends(require_auth)):
    _require_perm(ctx, "os.view")
    return os_repo.list_workflows(ctx.company_id)


@router.post("/communication")
def agent_communication(body: AgentMessage, ctx=Depends(require_auth)):
    _require_perm(ctx, "os.manage_agents")
    try:
        return comm_bus.send_message(ctx.company_id, body.from_agent, body.to_agent, body.message)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/communication/channels")
def communication_channels(ctx=Depends(require_auth)):
    _require_perm(ctx, "os.view")
    return comm_bus.list_channels()


@router.get("/communication")
def list_messages(ctx=Depends(require_auth)):
    _require_perm(ctx, "os.view")
    return os_repo.list_agent_messages(ctx.company_id)


@router.get("/memory")
def get_memory(ctx=Depends(require_auth)):
    _require_perm(ctx, "os.view_memory")
    return {
        "usage": memory_service.usage_summary(ctx.company_id),
        "memories": memory_service.recall(ctx.company_id),
    }


@router.post("/memory")
def store_memory(body: MemoryStore, ctx=Depends(require_auth)):
    _require_perm(ctx, "os.manage")
    try:
        return memory_service.store(ctx.company_id, body.memory_type, body.subject_key, body.summary)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/knowledge/learn")
def learn_knowledge(ctx=Depends(require_auth)):
    _require_perm(ctx, "os.manage")
    return knowledge_engine.run_full_learning(ctx.company_id)


@router.get("/knowledge")
def get_knowledge(ctx=Depends(require_auth)):
    _require_perm(ctx, "os.view_memory")
    return os_repo.list_knowledge(ctx.company_id)


@router.get("/automation")
def list_automation(ctx=Depends(require_auth)):
    _require_perm(ctx, "os.view")
    return automation_service.list_tasks(ctx.company_id)


@router.post("/automation/{task_key}/run")
def run_automation(task_key: str, ctx=Depends(require_auth)):
    _require_perm(ctx, "os.manage_automation")
    return automation_service.run_task(ctx.company_id, task_key)

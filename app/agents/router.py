"""Agent platform API routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.agents import repository as agent_repo
from app.agents.scheduler import service as scheduler_service
from app.core.config import agents_enabled
from app.core.deps import require_auth
from app.database import usage_repository

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentToggle(BaseModel):
    enabled: bool


class ReminderCreate(BaseModel):
    title: str
    message: str
    remind_at: str


@router.get("")
def list_agents(ctx=Depends(require_auth)):
    return agent_repo.list_agents(ctx.company_id)


@router.put("/{agent_type}/toggle")
def toggle_agent(agent_type: str, body: AgentToggle, ctx=Depends(require_auth)):
    row = agent_repo.set_agent_enabled(ctx.company_id, agent_type, body.enabled)
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return row


@router.get("/memories")
def get_memories(user_id: str | None = None, ctx=Depends(require_auth)):
    return agent_repo.list_memories(ctx.company_id, user_id=user_id)


@router.get("/logs")
def get_logs(ctx=Depends(require_auth)):
    return agent_repo.list_agent_logs(ctx.company_id)


@router.get("/dashboard")
def agent_dashboard(ctx=Depends(require_auth)):
    agents = agent_repo.list_agents(ctx.company_id)
    return {
        "agents_enabled": agents_enabled(),
        "agents": agents,
        "memory_count": agent_repo.count_memories(ctx.company_id),
        "messages_today": usage_repository.count_messages_today(ctx.company_id),
        "recent_logs": agent_repo.list_agent_logs(ctx.company_id, limit=10),
        "scheduler_tasks": agent_repo.list_scheduler_tasks(ctx.company_id),
        "reminders": agent_repo.list_reminders(ctx.company_id),
    }


@router.post("/scheduler/daily")
def run_daily(ctx=Depends(require_auth)):
    scheduler_service.setup_default_schedules(ctx.company_id)
    return scheduler_service.run_daily_report(ctx.company_id)


@router.post("/scheduler/weekly")
def run_weekly(ctx=Depends(require_auth)):
    scheduler_service.setup_default_schedules(ctx.company_id)
    return scheduler_service.run_weekly_report(ctx.company_id)


@router.post("/reminders", status_code=201)
def create_reminder(body: ReminderCreate, ctx=Depends(require_auth)):
    return agent_repo.create_reminder(
        ctx.company_id, body.title, body.message, body.remind_at
    )


@router.get("/reminders")
def list_reminders(ctx=Depends(require_auth)):
    return scheduler_service.process_due_reminders(ctx.company_id)

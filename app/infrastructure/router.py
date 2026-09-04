"""Enterprise infrastructure API routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from app.core.deps import require_auth
from app.database import company_repository, user_repository
from app.infrastructure.audit import service as audit_service
from app.infrastructure.backups import service as backup_service
from app.infrastructure.database.config import is_postgres
from app.infrastructure.monitoring import metrics
from app.infrastructure.profiles import get_env_name, get_profile
from app.infrastructure.redis.client import is_redis_available
from app.infrastructure.team import permissions, repository as team_repo
from app.infrastructure.team import service as team_service

router = APIRouter(prefix="/api/infrastructure", tags=["infrastructure"])


class TeamInvite(BaseModel):
    email: EmailStr
    role: str = "member"


class TeamRoleUpdate(BaseModel):
    role: str


class RestoreRequest(BaseModel):
    backup_name: str


@router.get("/status")
def infrastructure_status(ctx=Depends(require_auth)):
    profile = get_profile()
    return {
        "environment": get_env_name(),
        "profile": profile,
        "database": "postgresql" if is_postgres() else "sqlite",
        "redis": is_redis_available(),
        "metrics": metrics.get_metrics(ctx.company_id),
    }


@router.get("/monitoring")
def monitoring(ctx=Depends(require_auth)):
    return metrics.get_metrics(ctx.company_id)


@router.get("/monitoring/errors")
def error_logs(ctx=Depends(require_auth)):
    return {
        "buffer": metrics.get_metrics()["recent_errors"],
        "file_logs": metrics.list_error_logs(),
    }


@router.get("/audit")
def audit_logs(ctx=Depends(require_auth)):
    return audit_service.get_logs(company_id=ctx.company_id)


@router.get("/backups")
def list_backups(ctx=Depends(require_auth)):
    _require_admin(ctx)
    return backup_service.list_backups()


@router.post("/backups/daily")
def daily_backup(ctx=Depends(require_auth)):
    _require_admin(ctx)
    result = backup_service.run_daily_backup()
    audit_service.record("backup.daily", ctx.company_id, ctx.user_id)
    return result


@router.post("/backups/weekly")
def weekly_backup(ctx=Depends(require_auth)):
    _require_admin(ctx)
    result = backup_service.run_weekly_backup()
    audit_service.record("backup.weekly", ctx.company_id, ctx.user_id)
    return result


@router.post("/backups/restore")
def restore_backup(body: RestoreRequest, ctx=Depends(require_auth)):
    _require_admin(ctx)
    result = backup_service.restore_backup(body.backup_name)
    if result.get("ok"):
        audit_service.record(f"backup.restore:{body.backup_name}", ctx.company_id, ctx.user_id)
    return result


@router.get("/team")
def list_team(ctx=Depends(require_auth)):
    company = company_repository.get_company(ctx.company_id)
    members = team_repo.list_members(ctx.company_id)
    if company and company.get("owner_id"):
        team_service.ensure_owner_member(ctx.company_id, company["owner_id"])
        members = team_repo.list_members(ctx.company_id)
    return {
        "members": members,
        "roles": list(permissions.ROLES),
        "permissions": {r: list(permissions.ROLE_PERMISSIONS[r]) for r in permissions.ROLES},
    }


@router.post("/team/invite", status_code=201)
def invite_team_member(body: TeamInvite, ctx=Depends(require_auth)):
    _require_admin(ctx)
    user = user_repository.get_user_by_email(body.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    member = team_service.invite_member(ctx.company_id, user["id"], body.role)
    team_repo.log_activity(ctx.company_id, ctx.user_id, "team.invite", body.email)
    audit_service.record(f"team.invite:{body.email}", ctx.company_id, ctx.user_id)
    return member


@router.put("/team/{user_id}/role")
def update_team_role(user_id: int, body: TeamRoleUpdate, ctx=Depends(require_auth)):
    _require_admin(ctx)
    if body.role not in permissions.ROLES or body.role == "owner":
        raise HTTPException(status_code=400, detail="Invalid role.")
    row = team_repo.set_role(ctx.company_id, user_id, body.role)
    if not row:
        raise HTTPException(status_code=404, detail="Team member not found.")
    audit_service.record(f"team.role:{user_id}:{body.role}", ctx.company_id, ctx.user_id)
    return row


@router.delete("/team/{user_id}")
def remove_team_member(user_id: int, ctx=Depends(require_auth)):
    _require_admin(ctx)
    if not team_repo.remove_member(ctx.company_id, user_id):
        raise HTTPException(status_code=404, detail="Team member not found.")
    audit_service.record(f"team.remove:{user_id}", ctx.company_id, ctx.user_id)
    return {"ok": True}


@router.get("/activity")
def activity_history(ctx=Depends(require_auth)):
    return team_repo.list_activity(ctx.company_id)


def _require_admin(ctx) -> None:
    company = company_repository.get_company(ctx.company_id)
    owner_id = company["owner_id"] if company else None
    if not team_service.check_permission(ctx.company_id, ctx.user_id, owner_id, "manage_team"):
        raise HTTPException(status_code=403, detail="Admin permission required.")

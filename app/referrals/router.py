"""Authenticated customer endpoints for the human Marketing Agent program."""
from fastapi import APIRouter, Depends, Request

from app.core.deps import require_auth
from app.infrastructure.audit import service as audit_service
from app.referrals import service

router = APIRouter(prefix="/referral-agent", tags=["referral-agent"])


@router.get("/me")
def my_agent_dashboard(request: Request, ctx=Depends(require_auth)):
    return service.public_dashboard(ctx.user_id, str(request.base_url))


@router.post("/apply", status_code=201)
def apply(ctx=Depends(require_auth)):
    result = service.apply(ctx.user_id)
    audit_service.record("referral_agent.application", ctx.company_id, ctx.user_id)
    return result

"""Aura Network API routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.deps import require_auth
from app.infrastructure.audit import service as audit_service
from app.network.analytics import service as analytics_service
from app.network.federation import learning as fed_learning
from app.network.federation import service as federation_service
from app.network.federation.agents import execute_agent
from app.network.governance.policies import NETWORK_MODES, get_policies, set_policies
from app.network.marketplace import service as network_marketplace
from app.network.security import require_network_admin
from app.network.synchronization import service as sync_service
from app.database import company_repository

router = APIRouter(prefix="/network", tags=["network"])


class JoinRequest(BaseModel):
    network_mode: str = "shared"
    remote_node_id: str | None = None


class AgentExecuteRequest(BaseModel):
    agent_type: str
    text: str
    execution_mode: str = "local"


class FederatedTrainRequest(BaseModel):
    model_key: str = "aura_default"
    metrics: dict = {}


class SyncRequest(BaseModel):
    sync_type: str = "all"


@router.post("/join")
def join_network(body: JoinRequest, ctx=Depends(require_auth)):
    require_network_admin(ctx.company_id, ctx.user_id)
    try:
        result = federation_service.join(
            ctx.company_id, body.network_mode, body.remote_node_id
        )
        audit_service.record(f"network.join:{body.network_mode}", ctx.company_id, ctx.user_id)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/leave")
def leave_network(ctx=Depends(require_auth)):
    require_network_admin(ctx.company_id, ctx.user_id)
    result = federation_service.leave(ctx.company_id)
    audit_service.record("network.leave", ctx.company_id, ctx.user_id)
    return result


@router.get("/status")
def network_status(ctx=Depends(require_auth)):
    return federation_service.status(ctx.company_id)


@router.get("/analytics")
def network_analytics(ctx=Depends(require_auth)):
    return analytics_service.full_analytics(ctx.company_id)


@router.get("/modes")
def network_modes():
    return NETWORK_MODES


@router.get("/governance")
def get_governance(ctx=Depends(require_auth)):
    return get_policies(ctx.company_id)


@router.put("/governance")
def update_governance(body: JoinRequest, ctx=Depends(require_auth)):
    require_network_admin(ctx.company_id, ctx.user_id)
    try:
        return set_policies(ctx.company_id, body.network_mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/sync")
def run_sync(body: SyncRequest, ctx=Depends(require_auth)):
    require_network_admin(ctx.company_id, ctx.user_id)
    if body.sync_type == "settings":
        return sync_service.sync_company_settings(ctx.company_id)
    if body.sync_type == "knowledge":
        return sync_service.sync_knowledge(ctx.company_id)
    if body.sync_type == "plugins":
        return sync_service.sync_plugins(ctx.company_id)
    return sync_service.sync_all(ctx.company_id)


@router.post("/agents/execute")
async def distributed_agent(body: AgentExecuteRequest, ctx=Depends(require_auth)):
    company = company_repository.get_company(ctx.company_id)
    profile = company.get("company_profile", "") if company else ""
    try:
        return await execute_agent(
            ctx.company_id,
            body.agent_type,
            body.text,
            mode=body.execution_mode,
            company_profile=profile,
            user_id=str(ctx.user_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/federation/train")
def federated_train(body: FederatedTrainRequest, ctx=Depends(require_auth)):
    return fed_learning.local_train(ctx.company_id, body.model_key, body.metrics)


@router.get("/federation/aggregate")
def federated_aggregate(model_key: str | None = None, ctx=Depends(require_auth)):
    return fed_learning.aggregate_global_improvements(model_key)


@router.get("/marketplace")
def network_marketplace(ctx=Depends(require_auth)):
    return network_marketplace.list_network_extensions()

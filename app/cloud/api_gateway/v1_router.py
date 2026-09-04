import os

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.agents.registry import route_message
from app.cloud.analytics import service as analytics_service
from app.cloud.api_gateway.gateway import check_rate_limit, check_scope, resolve_api_key, track_request
from app.database import company_repository, faq_repository

router = APIRouter(prefix="/api/v1", tags=["api-v1"])


class ChatRequest(BaseModel):
    text: str
    language: str = "english"
    agent_type: str | None = None


def _get_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> dict:
    record = resolve_api_key(x_api_key)
    if not record:
        raise HTTPException(status_code=401, detail="Valid X-API-Key header required.")
    check_rate_limit(record)
    return record


@router.get("/companies")
def v1_companies(api_key=Depends(_get_api_key)):
    check_scope(api_key, "read")
    track_request(api_key, "/api/v1/companies", "GET")
    company = company_repository.get_company(api_key["company_id"])
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")
    return {
        "id": company["id"],
        "company_name": company["company_name"],
        "company_profile": company["company_profile"],
    }


@router.get("/faq")
def v1_faq(api_key=Depends(_get_api_key)):
    check_scope(api_key, "read")
    track_request(api_key, "/api/v1/faq", "GET")
    return faq_repository.list_faqs(api_key["company_id"])


@router.post("/chat")
async def v1_chat(body: ChatRequest, api_key=Depends(_get_api_key)):
    check_scope(api_key, "write")
    track_request(api_key, "/api/v1/chat", "POST")
    company = company_repository.get_company(api_key["company_id"])
    profile = company["company_profile"] if company else ""
    return await route_message(
        text=body.text,
        company_id=api_key["company_id"],
        company_profile=profile,
        language=body.language,
        agent_type=body.agent_type,
    )


@router.get("/analytics")
def v1_analytics(api_key=Depends(_get_api_key)):
    check_scope(api_key, "read")
    track_request(api_key, "/api/v1/analytics", "GET")
    return analytics_service.full_dashboard(api_key["company_id"])

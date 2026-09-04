"""Chat API route — POST /chat."""

from fastapi import APIRouter, Depends

from app.api.schemas import Message
from app.core.deps import require_auth
from app.database import company_repository
from app.agents.registry import route_message

router = APIRouter()


@router.post("/chat")
async def chat(msg: Message, ctx=Depends(require_auth)):
    system_guide = msg.mode == "system_guide"
    company_profile = "" if system_guide else msg.companyProfile
    if ctx.authenticated and not system_guide:
        company = company_repository.get_company(ctx.company_id)
        if company and company.get("company_profile"):
            company_profile = company["company_profile"] or company_profile
    elif not company_profile and not system_guide:
        company = company_repository.get_company(ctx.company_id)
        if company:
            company_profile = company.get("company_profile", "")

    user_id = str(ctx.user_id) if ctx.user_id else "default"

    return await route_message(
        text=msg.text,
        company_id=ctx.company_id,
        company_profile=company_profile,
        voice_type=msg.voiceType,
        language=msg.language,
        session_id=msg.session_id,
        agent_type=msg.agent_type,
        providers=msg.providers,
        user_id=user_id,
        system_guide=system_guide,
        request_id=msg.request_id,
    )

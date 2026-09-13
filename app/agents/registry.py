"""
Agent registry — load agents and route by type.
"""

from app.agents.orchestrator import handle_agent_chat
from app.services import chat_service


async def route_message(
    text: str,
    company_id: int,
    company_profile: str = "",
    voice_type: str = "female",
    language: str = "english",
    session_id: str | None = None,
    agent_type: str | None = None,
    providers: list[str] | None = None,
    user_id: str = "default",
    system_guide: bool = False,
    request_id: str | None = None,
) -> dict:
    if agent_type:
        return await handle_agent_chat(
            agent_type=agent_type,
            text=text,
            company_id=company_id,
            company_profile=company_profile,
            voice_type=voice_type,
            language=language,
            session_id=session_id,
            user_id=user_id,
        )
    return await chat_service.handle_chat(
        text=text,
        company_id=company_id,
        company_profile=company_profile,
        voice_type=voice_type,
        language=language,
        session_id=session_id,
        providers=providers,
        system_guide=system_guide,
        user_id=int(user_id) if str(user_id).isdigit() else None,
        request_id=request_id,
    )

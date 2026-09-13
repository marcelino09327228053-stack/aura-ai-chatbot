"""
Agent orchestrator — routes messages to the correct agent type.
"""

from app.agents import repository as agent_repo
from app.agents.accounting import agent as accounting_agent
from app.agents.hr import agent as hr_agent
from app.agents.marketing import agent as marketing_agent
from app.agents.sales import agent as sales_agent
from app.agents.support import agent as support_agent
from app.core.config import agents_enabled, is_agent_type_enabled
from app.database import conversation_repository, usage_repository
from app.services import tts_service
from app.services.subscription_service import check_message_limit

AGENT_RUNNERS = {
    "support": support_agent.run,
    "sales": sales_agent.run,
    "hr": hr_agent.run,
    "accounting": accounting_agent.run,
    "marketing": marketing_agent.run,
}


async def handle_agent_chat(
    agent_type: str,
    text: str,
    company_id: int,
    company_profile: str = "",
    voice_type: str = "female",
    language: str = "english",
    session_id: str | None = None,
    user_id: str = "default",
) -> dict:
    session_id = session_id or conversation_repository.new_session_id()
    text_lower = text.lower()

    if "voice on" in text_lower:
        tts_service.tts_mode = True
        return {"reply": "🔊 Voice ON", "session_id": session_id, "agent": agent_type}

    if "voice off" in text_lower:
        tts_service.tts_mode = False
        return {"reply": "🔇 Voice OFF", "session_id": session_id, "agent": agent_type}

    if not agents_enabled():
        return {
            "reply": "Agents are disabled. Set AGENTS_ENABLED=true to use agents.",
            "session_id": session_id,
        }

    if not is_agent_type_enabled(agent_type):
        return {
            "reply": f"Agent type '{agent_type}' is disabled.",
            "session_id": session_id,
        }

    if not agent_repo.is_agent_enabled(company_id, agent_type):
        return {
            "reply": f"The {agent_type} agent is disabled for this company.",
            "session_id": session_id,
        }

    runner = AGENT_RUNNERS.get(agent_type)
    if not runner:
        return {"reply": f"Unknown agent type: {agent_type}", "session_id": session_id}

    conversation_repository.add_message(company_id, session_id, "user", text)

    reply, source = await runner(company_id, user_id, text, company_profile, language)

    if source == "ai":
        check_message_limit(company_id)
        usage_repository.record_message(company_id)

    conversation_repository.add_message(company_id, session_id, "assistant", reply)
    agent_repo.log_agent_run(company_id, agent_type, text, source, reply)

    if source == "ai" and len(text) > 20:
        agent_repo.add_memory(
            company_id,
            user_id,
            f"User asked: {text[:120]}. Agent replied briefly.",
        )

    result = {"reply": reply, "session_id": session_id, "agent": agent_type, "source": source}

    if tts_service.tts_mode:
        audio_file = await tts_service.text_to_speech(reply, voice_type, language)
        result["audio"] = audio_file

    return result

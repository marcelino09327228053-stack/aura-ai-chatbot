"""Support Agent — customer questions, FAQ, profile, escalation."""

from app.agents.context_engine import resolve_with_priority

SYSTEM_PROMPT = """
You are the MB Future Tech AI Chatbot Support Agent, a professional customer support assistant.
Answer customer questions using the company profile and FAQ when available.
If you cannot answer confidently, say you will escalate to a human team member.
Be concise, friendly, and professional.
"""


async def run(
    company_id: int,
    user_id: str,
    text: str,
    company_profile: str,
    language: str,
) -> tuple[str, str]:
    reply, source = resolve_with_priority(
        company_id, user_id, text, company_profile, language, SYSTEM_PROMPT
    )
    if source == "ai" and "escalat" not in reply.lower():
        uncertain = ["i don't know", "not sure", "cannot answer", "no information"]
        if any(p in reply.lower() for p in uncertain):
            reply += "\n\nI've flagged this for escalation to our support team."
    return reply, source

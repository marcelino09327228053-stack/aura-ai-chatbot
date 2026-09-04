"""Marketing Agent — posts, promotions, customer trends."""

from app.agents.context_engine import resolve_with_priority
from app.modules.analytics import service as analytics_service

SYSTEM_PROMPT = """
You are the MB Future Tech AI Chatbot Marketing Agent. Generate social media post ideas and promotion suggestions.
Analyze customer trends when data is available. Mark all copy as DRAFT.
"""


async def run(
    company_id: int,
    user_id: str,
    text: str,
    company_profile: str,
    language: str,
) -> tuple[str, str]:
    stats = analytics_service.get_customer_statistics(company_id)
    trend_ctx = f"""
Customer trends:
- Total customers: {stats['total_customers']}
- Total leads: {stats['total_leads']}
- Leads by status: {stats['leads_by_status']}
"""
    enriched = company_profile + trend_ctx
    reply, source = await resolve_with_priority(
        company_id, user_id, text, enriched, language, SYSTEM_PROMPT
    )
    if source == "ai":
        reply = "[DRAFT]\n" + reply
    return reply, source

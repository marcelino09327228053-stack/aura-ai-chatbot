"""Sales Agent — recommendations, lead capture, follow-ups."""

from app.agents.context_engine import resolve_with_priority
from app.modules.crm import repository as crm_repo
from app.modules.inventory import repository as inventory_repo

SYSTEM_PROMPT = """
You are the MB Future Tech AI Chatbot Sales Agent. Recommend products and services based on company data.
Suggest follow-up actions and capture lead interest professionally.
Do not make up products not in the provided catalog.
"""


async def run(
    company_id: int,
    user_id: str,
    text: str,
    company_profile: str,
    language: str,
) -> tuple[str, str]:
    products = inventory_repo.list_products(company_id)[:10]
    catalog = "\n".join(f"- {p['name']} (₱{p['price']}, stock: {p['stock']})" for p in products)
    enriched_profile = company_profile + f"\n\nProduct catalog:\n{catalog or 'No products listed.'}"

    reply, source = resolve_with_priority(
        company_id, user_id, text, enriched_profile, language, SYSTEM_PROMPT
    )

    if any(k in text.lower() for k in ("buy", "interested", "price", "quote", "order")):
        crm_repo.create_lead(company_id, name=user_id, status="new", source="chat")
        reply += "\n\n💡 Follow-up suggestion: Send a personalized quote within 24 hours."

    return reply, source

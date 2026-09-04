"""
Context engine — priority-based response resolution.

Priority 1: Owner-edited AI Database (exact FAQ match)
Priority 2: Generated FAQ (keyword FAQ search)
Priority 3: Memory summaries
Priority 4: AI provider (Gemini)
"""

from app.agents import repository as agent_repo
from app.database.faq_repository import find_faq_answer, list_faqs
from app.services import ai_service


def search_faq_keyword(company_id: int, text: str) -> str | None:
    """Priority 2: find FAQ by keyword overlap."""
    words = [w for w in text.lower().split() if len(w) > 3]
    if not words:
        return None

    faqs = list_faqs(company_id)
    best = None
    best_score = 0
    for faq in faqs:
        q = faq["question"].lower()
        score = sum(1 for w in words if w in q)
        if score > best_score:
            best_score = score
            best = faq["answer"]
    return best if best_score > 0 else None


def get_memory_context(company_id: int, user_id: str, limit: int = 5) -> str:
    """Priority 3: recent memory summaries."""
    memories = agent_repo.list_memories(company_id, user_id=user_id, limit=limit)
    if not memories:
        return ""
    lines = [m["summary"] for m in memories]
    return "Previous context:\n" + "\n".join(f"- {line}" for line in lines)


def resolve_with_priority(
    company_id: int,
    user_id: str,
    text: str,
    company_profile: str,
    language: str,
    system_prompt: str,
) -> tuple[str, str]:
    """
    Returns (reply, source) where source is faq_exact|faq_search|memory|ai.
    """
    exact = find_faq_answer(text, company_id)
    if exact:
        return exact, "faq_exact"

    keyword = search_faq_keyword(company_id, text)
    if keyword:
        return keyword, "faq_search"

    memory_ctx = get_memory_context(company_id, user_id)
    if memory_ctx and any(word in memory_ctx.lower() for word in text.lower().split() if len(word) > 4):
        return (
            f"Based on our previous conversations:\n{memory_ctx}\n\nRegarding your question: I can help with that. "
            f"For more detail, please ask a specific follow-up.",
            "memory",
        )

    lang_map = {
        "filipino": "Respond only in Filipino.",
        "english": "Respond only in English.",
        "japanese": "Respond only in Japanese.",
        "chinese": "Respond only in Simplified Chinese.",
        "korean": "Respond only in Korean.",
        "hindi": "Respond only in Hindi.",
    }
    lang_instruction = lang_map.get(language, "")

    prompt = f"""
{system_prompt}

{lang_instruction}

Company Information:
{company_profile}

{memory_ctx}

User:
{text}
"""
    reply = ai_service.generate_reply(prompt)
    return reply, "ai"

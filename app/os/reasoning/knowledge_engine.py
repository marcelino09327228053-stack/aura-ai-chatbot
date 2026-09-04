"""Knowledge engine — learn from conversations, FAQs, and documents."""

from app.database.faq_repository import list_faqs
from app.os import repository as os_repo
from app.os.memory import service as memory_service


def learn_from_conversations(company_id: int, limit: int = 20) -> list[dict]:
    from app.infrastructure.database import get_connection
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT content, role FROM conversations
        WHERE company_id = ? AND role = 'user'
        ORDER BY created_at DESC LIMIT ?
        """,
        (company_id, limit),
    )
    learned = []
    for row in cursor.fetchall():
        content = row["content"]
        if len(content) < 10:
            continue
        summary = f"User asked: {content[:200]}"
        entry = os_repo.add_knowledge(company_id, "conversation", summary, source_ref=row["role"])
        memory_service.store(company_id, "customer", "default", summary[:500])
        learned.append(entry)
    return learned


def learn_from_faqs(company_id: int) -> list[dict]:
    faqs = list_faqs(company_id)
    learned = []
    for faq in faqs:
        content = f"Q: {faq['question']} A: {faq['answer'][:300]}"
        entry = os_repo.add_knowledge(company_id, "faq", content, source_ref=str(faq["id"]))
        memory_service.store(company_id, "knowledge", f"faq_{faq['id']}", content[:500])
        learned.append(entry)
    return learned


def learn_from_company_profile(company_id: int) -> dict:
    from app.database import company_repository
    company = company_repository.get_company(company_id)
    if not company or not company.get("company_profile"):
        return {"learned": 0}
    content = company["company_profile"][:2000]
    entry = os_repo.add_knowledge(company_id, "document", content, source_ref="company_profile")
    memory_service.store(company_id, "company", str(company_id), content[:500])
    return entry


def run_full_learning(company_id: int) -> dict:
    conv = learn_from_conversations(company_id, limit=10)
    faqs = learn_from_faqs(company_id)
    doc = learn_from_company_profile(company_id)
    return {
        "conversations_learned": len(conv),
        "faqs_learned": len(faqs),
        "documents_learned": 1 if doc else 0,
        "total_knowledge": len(os_repo.list_knowledge(company_id)),
    }


def search_knowledge(company_id: int, query: str, limit: int = 5) -> list[dict]:
    items = os_repo.list_knowledge(company_id, limit=100)
    words = [w.lower() for w in query.split() if len(w) > 3]
    scored = []
    for item in items:
        content_lower = item["content"].lower()
        score = sum(1 for w in words if w in content_lower)
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:limit]]

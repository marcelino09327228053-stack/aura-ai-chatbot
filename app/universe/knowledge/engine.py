"""Knowledge system — document, FAQ, customer learning, automatic summaries."""

from __future__ import annotations

from app.database import faq_repository as faq_repo
from app.database import memory_repository as mem_repo
from app.infrastructure.database import get_connection
from app.services.ai_gateway import generate_sync
from app.universe import repository as uni_repo


def learn_from_documents(company_id: int) -> list[dict]:
    """Extract knowledge from company documents (FAQ entries as proxy)."""
    faqs = faq_repo.list_faqs(company_id)
    learned = []
    for faq in faqs[:20]:
        question = faq.get("question", "")
        answer = faq.get("answer", "")
        if not question:
            continue
        summary = f"Q: {question[:200]} | A: {answer[:300]}"
        entry = uni_repo.save_knowledge_entry(
            company_id, "document", question[:100], answer,
            source_id=str(faq.get("id", "")), summary=summary,
        )
        learned.append(entry)
    uni_repo.log_universe_action(company_id, "knowledge.learn_documents", details=f"{len(learned)} items")
    return learned


def learn_from_faqs(company_id: int) -> list[dict]:
    """Dedicated FAQ learning pass with categorization."""
    faqs = faq_repo.list_faqs(company_id)
    learned = []
    categories: dict[str, int] = {}
    for faq in faqs:
        cat = faq.get("category") or "general"
        categories[cat] = categories.get(cat, 0) + 1
        entry = uni_repo.save_knowledge_entry(
            company_id, "faq",
            faq.get("question", "FAQ")[:100],
            faq.get("answer", ""),
            source_id=str(faq.get("id", "")),
            summary=f"Category: {cat}",
        )
        learned.append(entry)

    if categories:
        uni_repo.save_summary(
            company_id, "faq",
            "FAQ Knowledge Summary",
            f"Learned from {len(learned)} FAQs across categories: {categories}",
        )
    uni_repo.log_universe_action(company_id, "knowledge.learn_faqs", details=f"{len(learned)} faqs")
    return learned


def learn_from_customers(company_id: int) -> list[dict]:
    """Learn from customer conversations and memories."""
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT id, content FROM conversations
        WHERE company_id = ? AND role = 'user'
        ORDER BY created_at DESC LIMIT 30
        """,
        (company_id,),
    )
    learned = []

    for row in cursor.fetchall():
        content = row["content"]
        if len(content) < 5:
            continue
        entry = uni_repo.save_knowledge_entry(
            company_id, "customer",
            f"Customer inquiry #{row['id']}",
            content[:500],
            source_id=str(row["id"]),
            summary=content[:150],
        )
        learned.append(entry)

    memories = mem_repo.list_memory(company_id)
    for mem in memories[:20]:
        entry = uni_repo.save_knowledge_entry(
            company_id, "customer",
            f"Memory: {mem.get('contact_key', 'unknown')}",
            mem.get("content", ""),
            source_id=str(mem.get("id", "")),
            summary=mem.get("content", "")[:150],
        )
        learned.append(entry)

    uni_repo.log_universe_action(company_id, "knowledge.learn_customers", details=f"{len(learned)} items")
    return learned


def generate_automatic_summary(company_id: int, summary_type: str = "daily") -> dict:
    """Generate AI-powered summary from accumulated knowledge."""
    entries = uni_repo.list_knowledge_entries(company_id, limit=30)
    if not entries:
        learn_from_faqs(company_id)
        learn_from_customers(company_id)
        entries = uni_repo.list_knowledge_entries(company_id, limit=30)

    snippets = [f"- {e.get('title', '')}: {e.get('summary', e.get('content', ''))[:100]}" for e in entries[:15]]
    context = "\n".join(snippets) or "No knowledge entries yet."

    prompt = (
        f"Create a concise {summary_type} business knowledge summary (3-5 bullet points) "
        f"based on these learned items:\n{context}\n\n"
        "Focus on actionable insights for the business team."
    )
    try:
        content = generate_sync(prompt, company_id)["reply"]
    except Exception:
        content = f"Summary of {len(entries)} knowledge items across document, FAQ, and customer sources."

    summary = uni_repo.save_summary(company_id, summary_type, f"{summary_type.title()} Knowledge Summary", content)
    uni_repo.log_universe_action(company_id, "knowledge.auto_summary", details=summary_type)
    return summary


def run_full_learning(company_id: int) -> dict:
    docs = learn_from_documents(company_id)
    faqs = learn_from_faqs(company_id)
    customers = learn_from_customers(company_id)
    summary = generate_automatic_summary(company_id, "comprehensive")

    return {
        "documents_learned": len(docs),
        "faqs_learned": len(faqs),
        "customers_learned": len(customers),
        "summary": summary,
        "total_entries": len(uni_repo.list_knowledge_entries(company_id)),
    }


def knowledge_overview(company_id: int) -> dict:
    entries = uni_repo.list_knowledge_entries(company_id)
    summaries = uni_repo.list_summaries(company_id)
    shared = uni_repo.list_shared_knowledge(company_id, 10)

    by_source: dict[str, int] = {}
    for e in entries:
        src = e.get("source_type", "unknown")
        by_source[src] = by_source.get(src, 0) + 1

    return {
        "total_entries": len(entries),
        "by_source": by_source,
        "recent_entries": entries[:10],
        "summaries": summaries[:5],
        "shared_knowledge": shared,
    }

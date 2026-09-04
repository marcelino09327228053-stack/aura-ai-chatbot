"""Long-term memory — customer, company, employee, knowledge."""

from app.os import repository as os_repo

MEMORY_TYPES = ("customer", "company", "employee", "knowledge")


def store(company_id: int, memory_type: str, subject_key: str, summary: str) -> dict:
    if memory_type not in MEMORY_TYPES:
        raise ValueError(f"Invalid memory type: {memory_type}")
    return os_repo.add_long_term_memory(company_id, memory_type, subject_key, summary)


def recall(company_id: int, memory_type: str | None = None, limit: int = 20) -> list[dict]:
    return os_repo.list_long_term_memory(company_id, memory_type=memory_type, limit=limit)


def get_context_block(company_id: int, memory_type: str, subject_key: str, limit: int = 5) -> str:
    memories = os_repo.list_long_term_memory(company_id, memory_type=memory_type, limit=limit)
    relevant = [m for m in memories if m["subject_key"] == subject_key or subject_key == "default"]
    if not relevant:
        return ""
    lines = [f"- {m['summary']}" for m in relevant[:limit]]
    return f"{memory_type.title()} memory:\n" + "\n".join(lines)


def usage_summary(company_id: int) -> dict:
    counts = os_repo.count_long_term_memory(company_id)
    total = sum(counts.values())
    return {"total": total, "by_type": counts}

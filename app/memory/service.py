"""
Memory service — bridges short-term agent memory and Aura OS long-term memory.
"""

from app.agents import repository as agent_repo


class MemoryService:
    def enabled(self) -> bool:
        return True

    def add_summary(self, company_id: int, user_id: str, summary: str) -> dict:
        result = agent_repo.add_memory(company_id, user_id, summary)
        try:
            from app.os.memory import service as os_memory
            os_memory.store(company_id, "customer", user_id, summary)
        except Exception:
            pass
        return result

    def get_context(self, company_id: int, user_id: str = "default", limit: int = 5) -> str:
        from app.agents.context_engine import get_memory_context
        ctx = get_memory_context(company_id, user_id, limit)
        try:
            from app.os.memory import service as os_memory
            ltm = os_memory.get_context_block(company_id, "customer", user_id, limit=3)
            if ltm:
                ctx = ctx + "\n" + ltm if ctx else ltm
        except Exception:
            pass
        return ctx

    def count(self, company_id: int) -> int:
        return agent_repo.count_memories(company_id)

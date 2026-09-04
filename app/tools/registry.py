"""
Tool registry (placeholder).

Phase 7C will register read-only tools:
  faq.search, database.search, documents.read, reports.generate, etc.
"""


class ToolRegistry:
    """No-op stub until tool runtime is implemented."""

    def execute(self, business_id, agent_id, name, args):
        raise NotImplementedError("Tools are not enabled yet.")

"""Plugin context — permission-gated API for sandboxed plugins."""

from app.database import company_repository, conversation_repository
from app.database.faq_repository import list_faqs
from app.modules.inventory import repository as inventory_repo
from app.modules.reports import service as reports_service
from app.plugins.sdk.manifest import ALL_PERMISSIONS


class PluginContext:
    """Isolated API surface exposed to plugins based on granted permissions."""

    def __init__(self, company_id: int, permissions: list[str], plugin_id: int):
        self.company_id = company_id
        self.plugin_id = plugin_id
        self._permissions = set(permissions)

    def _check(self, permission: str) -> None:
        if permission not in self._permissions:
            raise PermissionError(f"Plugin lacks permission: {permission}")
        if permission not in ALL_PERMISSIONS:
            raise PermissionError(f"Unknown permission: {permission}")

    def read_faq(self) -> list[dict]:
        self._check("read_faq")
        return list_faqs(self.company_id)

    def read_company_profile(self) -> dict:
        self._check("read_company_profile")
        company = company_repository.get_company(self.company_id)
        if not company:
            return {"company_name": "", "company_profile": ""}
        return {
            "company_name": company["company_name"],
            "company_profile": company["company_profile"],
        }

    def read_conversations(self, session_id: str | None = None, limit: int = 20) -> list[dict]:
        self._check("read_conversations")
        if session_id:
            return conversation_repository.list_messages(self.company_id, session_id, limit=limit)
        from app.database.connection import get_connection
        cursor = get_connection().cursor()
        cursor.execute(
            """
            SELECT session_id, role, content, created_at
            FROM conversations WHERE company_id = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (self.company_id, limit),
        )
        return [dict(r) for r in cursor.fetchall()]

    def generate_reports(self, report_type: str = "daily") -> dict:
        self._check("generate_reports")
        if report_type == "weekly":
            return reports_service.monthly_summary(self.company_id)
        return reports_service.daily_summary(self.company_id)

    def access_inventory(self) -> list[dict]:
        self._check("access_inventory")
        return inventory_repo.list_products(self.company_id)

"""Audit service."""

from app.infrastructure.audit import repository as audit_repo


def record(action: str, company_id: int | None = None, user_id: int | None = None) -> None:
    audit_repo.log_action(action, company_id=company_id, user_id=user_id)


def get_logs(company_id: int | None = None, limit: int = 50) -> list[dict]:
    return audit_repo.list_audit_logs(company_id=company_id, limit=limit)

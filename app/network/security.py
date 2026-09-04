"""Aura Network security — encryption, access control, tenant isolation."""

from fastapi import HTTPException

from app.cloud.security import decrypt_value, encrypt_value
from app.infrastructure.audit import service as audit_service
from app.infrastructure.team import service as team_service
from app.database import company_repository
from app.network.governance.policies import enforce_tenant_isolation


def require_network_admin(company_id: int, user_id: int) -> None:
    company = company_repository.get_company(company_id)
    owner_id = company["owner_id"] if company else None
    if not team_service.check_permission(company_id, user_id, owner_id, "manage_team"):
        raise HTTPException(status_code=403, detail="Network admin permission required.")


def secure_sync_payload(company_id: int, payload: str) -> str:
    audit_service.record(f"network.encrypt_sync:{company_id}", company_id, None)
    return encrypt_value(payload)


def verify_tenant_access(requester_company_id: int, target_company_id: int) -> None:
    if not enforce_tenant_isolation(requester_company_id, target_company_id):
        audit_service.record(
            f"network.tenant_violation:{target_company_id}",
            requester_company_id,
            None,
        )
        raise HTTPException(status_code=403, detail="Tenant isolation — access denied.")


def decrypt_sync_payload(encrypted: str) -> str:
    return decrypt_value(encrypted)

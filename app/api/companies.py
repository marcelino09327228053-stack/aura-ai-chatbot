"""Company management API routes."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import (
    CompanyCreateRequest,
    CompanyProfileRestoreRequest,
    CompanyProfileVersionUpdateRequest,
    CompanyUpdateRequest,
)
from app.core.deps import require_auth
from app.database import company_profile_version_repository, company_repository, subscription_repository
from app.services import auth_service

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("")
def list_companies(ctx=Depends(require_auth)):
    return company_repository.list_companies_by_owner(ctx.user_id)


@router.post("", status_code=201)
def create_company(body: CompanyCreateRequest, ctx=Depends(require_auth)):
    return auth_service.create_company_for_user(ctx.user_id, body.company_name)


@router.get("/{company_id}")
def get_company(company_id: int, ctx=Depends(require_auth)):
    if not company_repository.user_owns_company(ctx.user_id, company_id):
        raise HTTPException(status_code=403, detail="Access denied.")
    company = company_repository.get_company(company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found.")
    return company


@router.put("/{company_id}")
def update_company(company_id: int, body: CompanyUpdateRequest, ctx=Depends(require_auth)):
    if not company_repository.user_owns_company(ctx.user_id, company_id):
        raise HTTPException(status_code=403, detail="Access denied.")
    existing = company_repository.get_company(company_id)
    if (
        body.company_profile is not None
        and body.company_profile != existing["company_profile"]
        and existing["company_profile"].strip()
    ):
        company_profile_version_repository.add_version(
            company_id,
            existing["company_profile"],
            existing.get("company_profile_source", ""),
            existing["company_name"],
        )
    company = company_repository.update_company(
        company_id,
        company_name=body.company_name,
        company_profile=body.company_profile,
        company_profile_source=body.company_profile_source,
    )
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found.")
    return company


@router.get("/{company_id}/profile-versions")
def list_profile_versions(company_id: int, ctx=Depends(require_auth)):
    if not company_repository.user_owns_company(ctx.user_id, company_id):
        raise HTTPException(status_code=403, detail="Access denied.")
    return company_profile_version_repository.list_versions(company_id)


@router.patch("/{company_id}/profile-versions/{version_id}")
def rename_profile_version(
    company_id: int,
    version_id: int,
    body: CompanyProfileVersionUpdateRequest,
    ctx=Depends(require_auth),
):
    if not company_repository.user_owns_company(ctx.user_id, company_id):
        raise HTTPException(status_code=403, detail="Access denied.")
    version_name = body.version_name.strip()
    if not version_name:
        raise HTTPException(status_code=400, detail="Version name is required.")
    version = company_profile_version_repository.rename_version(
        company_id, version_id, version_name[:100]
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Profile version not found.")
    return version


@router.post("/{company_id}/profile-versions/restore")
def restore_profile_version(company_id: int, body: CompanyProfileRestoreRequest, ctx=Depends(require_auth)):
    if not company_repository.user_owns_company(ctx.user_id, company_id):
        raise HTTPException(status_code=403, detail="Access denied.")
    version = company_profile_version_repository.get_version(company_id, body.version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Profile version not found.")
    current = company_repository.get_company(company_id)
    company_profile_version_repository.add_version(
        company_id,
        current["company_profile"],
        current.get("company_profile_source", ""),
        current["company_name"],
    )
    return company_repository.update_company(
        company_id,
        company_profile=version["company_profile"],
        company_profile_source=version["company_profile_source"],
    )


@router.delete("/{company_id}/profile-versions/{version_id}")
def delete_profile_version(company_id: int, version_id: int, ctx=Depends(require_auth)):
    if not company_repository.user_owns_company(ctx.user_id, company_id):
        raise HTTPException(status_code=403, detail="Access denied.")
    if not company_profile_version_repository.delete_version(company_id, version_id):
        raise HTTPException(status_code=404, detail="Profile version not found.")
    return {"deleted": True, "version_id": version_id}

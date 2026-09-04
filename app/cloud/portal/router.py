"""Customer portal API routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.cloud.analytics import service as analytics_service
from app.cloud.api_gateway import repository as gateway_repo
from app.cloud.billing import service as billing_service
from app.cloud.billing.plans import list_plans
from app.cloud.marketplace import service as marketplace_service
from app.cloud.security import require_cloud_permission
from app.cloud.white_label import repository as white_label_repo
from app.core.deps import require_auth
from app.database import company_repository, user_repository
from app.plugins.registry import repository as plugin_repo

router = APIRouter(prefix="/cloud/portal", tags=["cloud-portal"])


class SubscribeRequest(BaseModel):
    plan: str
    cycle: str = "monthly"


class BrandingUpdate(BaseModel):
    logo_url: str = ""
    custom_domain: str = ""
    brand_name: str = ""
    theme: dict = {}


class ApiKeyCreate(BaseModel):
    name: str
    scopes: str = "read,write"
    rate_limit: int = 60


class CompanySettingsUpdate(BaseModel):
    company_name: str | None = None
    company_profile: str | None = None


class ReviewCreate(BaseModel):
    extension_key: str
    rating: int = 5
    review_text: str = ""


@router.get("")
def portal_dashboard(ctx=Depends(require_auth)):
    user = user_repository.get_user_by_id(ctx.user_id)
    company = company_repository.get_company(ctx.company_id)
    return {
        "user": {"id": user["id"], "email": user["email"]},
        "company": company,
        "billing": billing_service.get_billing_summary(ctx.company_id),
        "analytics": analytics_service.full_dashboard(ctx.company_id),
        "branding": white_label_repo.get_branding(ctx.company_id),
        "api_keys": gateway_repo.list_api_keys(ctx.company_id),
        "plugins": plugin_repo.list_plugins(ctx.company_id),
    }


@router.get("/account")
def account_settings(ctx=Depends(require_auth)):
    user = user_repository.get_user_by_id(ctx.user_id)
    return {"user": user}


@router.put("/company")
def update_company_settings(body: CompanySettingsUpdate, ctx=Depends(require_auth)):
    require_cloud_permission(ctx.company_id, ctx.user_id, "manage_settings")
    updated = company_repository.update_company(
        ctx.company_id,
        company_name=body.company_name,
        company_profile=body.company_profile,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Company not found.")
    return updated


@router.get("/subscription")
def subscription_management(ctx=Depends(require_auth)):
    return billing_service.get_billing_summary(ctx.company_id)


@router.get("/plans")
def billing_plans():
    return list_plans()


@router.post("/subscribe")
def subscribe(body: SubscribeRequest, ctx=Depends(require_auth)):
    require_cloud_permission(ctx.company_id, ctx.user_id, "manage_billing")
    try:
        return billing_service.subscribe(ctx.company_id, body.plan, body.cycle, ctx.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api-keys")
def list_portal_api_keys(ctx=Depends(require_auth)):
    return gateway_repo.list_api_keys(ctx.company_id)


@router.post("/api-keys", status_code=201)
def create_portal_api_key(body: ApiKeyCreate, ctx=Depends(require_auth)):
    require_cloud_permission(ctx.company_id, ctx.user_id, "manage_settings")
    return gateway_repo.create_api_key(
        ctx.company_id, body.name, body.scopes, body.rate_limit
    )


@router.delete("/api-keys/{key_id}")
def revoke_portal_api_key(key_id: int, ctx=Depends(require_auth)):
    require_cloud_permission(ctx.company_id, ctx.user_id, "manage_settings")
    gateway_repo.revoke_api_key(ctx.company_id, key_id)
    return {"ok": True}


@router.get("/branding")
def get_branding(ctx=Depends(require_auth)):
    return white_label_repo.get_branding(ctx.company_id)


@router.put("/branding")
def update_branding(body: BrandingUpdate, ctx=Depends(require_auth)):
    require_cloud_permission(ctx.company_id, ctx.user_id, "manage_settings")
    return white_label_repo.update_branding(
        ctx.company_id,
        logo_url=body.logo_url,
        custom_domain=body.custom_domain,
        brand_name=body.brand_name,
        theme=body.theme,
    )


@router.get("/marketplace")
def marketplace_catalog(ctx=Depends(require_auth)):
    return marketplace_service.list_extensions()


@router.post("/marketplace/reviews", status_code=201)
def submit_review(body: ReviewCreate, ctx=Depends(require_auth)):
    return marketplace_service.add_review(
        ctx.company_id, ctx.user_id, body.extension_key, body.rating, body.review_text
    )

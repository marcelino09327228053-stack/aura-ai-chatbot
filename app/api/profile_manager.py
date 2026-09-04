"""Company Profile Manager API routes."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import (
    AIResponseStyleRequest,
    CompanyProfileReviewRequest,
    CompanyProfileTestRequest,
    CompanyProfileWebsiteImportRequest,
)
from app.services.response_style_service import get_response_style, save_response_style
from app.core.deps import require_auth
from app.services.company_profile_manager import review_company_profile, test_company_profile
from app.services.website_profile_importer import import_public_website_profile

router = APIRouter(prefix="/profile-manager", tags=["profile-manager"])


@router.get("/response-style")
def read_response_style(ctx=Depends(require_auth)):
    return get_response_style(ctx.company_id)


@router.put("/response-style")
def update_response_style(body: AIResponseStyleRequest, ctx=Depends(require_auth)):
    try:
        return save_response_style(ctx.company_id, body.style, body.custom_instructions)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/import-website")
async def import_website_profile(
    body: CompanyProfileWebsiteImportRequest, ctx=Depends(require_auth)
):
    try:
        return await asyncio.to_thread(import_public_website_profile, body.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/review")
async def review_profile(body: CompanyProfileReviewRequest, ctx=Depends(require_auth)):
    draft = body.draft_profile.strip()
    if not draft:
        raise HTTPException(status_code=400, detail="Company profile is empty.")
    try:
        return await asyncio.to_thread(
            review_company_profile,
            draft,
            ctx.company_id,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="The selected AI provider is temporarily unavailable. Please try again.",
        ) from exc


@router.post("/test")
async def test_profile_answer(body: CompanyProfileTestRequest, ctx=Depends(require_auth)):
    try:
        return await asyncio.to_thread(
            test_company_profile, body.profile, body.question, ctx.company_id
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="The selected AI provider is temporarily unavailable. Please try again.",
        ) from exc

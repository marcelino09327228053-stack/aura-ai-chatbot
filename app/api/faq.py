"""FAQ CRUD and generation API routes."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.schemas import FaqCreate, FaqUpdate, GenerateFaqRequest
from app.core.deps import get_auth_context, require_auth
from app.database import faq_repository
from app.services.faq_generator import generate_faq_items

router = APIRouter(tags=["faq"])


@router.get("/faq")
def list_faqs(
    q: str | None = Query(default=None),
    ctx=Depends(require_auth),
):
    return faq_repository.list_faqs(ctx.company_id, search=q)


@router.post("/faq", status_code=201)
def create_faq(body: FaqCreate, ctx=Depends(require_auth)):
    row = faq_repository.create_faq(ctx.company_id, body.question, body.answer)
    if row is None:
        raise HTTPException(status_code=409, detail="FAQ with this question already exists.")
    return row


@router.put("/faq/{faq_id}")
def update_faq(faq_id: int, body: FaqUpdate, ctx=Depends(require_auth)):
    row = faq_repository.update_faq(
        faq_id, ctx.company_id, body.question, body.answer
    )
    if row is None:
        existing = faq_repository.get_faq(faq_id, ctx.company_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="FAQ not found.")
        raise HTTPException(status_code=409, detail="FAQ with this question already exists.")
    return row


@router.delete("/faq/{faq_id}")
def delete_faq(faq_id: int, ctx=Depends(require_auth)):
    if not faq_repository.delete_faq(faq_id, ctx.company_id):
        raise HTTPException(status_code=404, detail="FAQ not found.")
    return {"ok": True}


@router.post("/generate-faq")
async def generate_faq(body: GenerateFaqRequest, ctx=Depends(require_auth)):
    profile = body.companyProfile.strip()
    if not profile:
        raise HTTPException(
            status_code=400,
            detail="Company profile is empty. Add content in the dashboard first.",
        )

    try:
        generated = await asyncio.to_thread(generate_faq_items, profile, ctx.company_id)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=503 if isinstance(exc, RuntimeError) else 400,
            detail=str(exc),
        ) from exc

    created = faq_repository.bulk_create_faqs(ctx.company_id, generated)

    return [
        {"question": item["question"], "answer": item["answer"]}
        for item in created
    ]

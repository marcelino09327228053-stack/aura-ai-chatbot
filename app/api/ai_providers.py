"""Customer-owned AI provider connection API."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import AIProviderConnectRequest, AIProviderModelRequest
from app.core.deps import require_auth
from app.database import ai_provider_repository
from app.services import ai_service

router = APIRouter(prefix="/ai/providers", tags=["ai-providers"])


def _validate_provider(provider: str) -> str:
    provider = provider.lower()
    if provider not in ai_service.PROVIDERS:
        raise HTTPException(status_code=404, detail="Unknown AI provider.")
    return provider


@router.get("")
async def list_ai_providers(ctx=Depends(require_auth)):
    return {"providers": ai_service.get_provider_status(ctx.company_id)}


@router.post("/{provider}/connect")
async def connect_ai_provider(
    provider: str,
    body: AIProviderConnectRequest,
    ctx=Depends(require_auth),
):
    provider = _validate_provider(provider)
    api_key = body.api_key.strip()
    if len(api_key) < 8:
        raise HTTPException(status_code=400, detail="Enter a valid API key.")
    try:
        await asyncio.to_thread(
            ai_service.generate_reply,
            "Reply with only the word CONNECTED.",
            provider,
            None,
            api_key,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Connection test failed: {str(exc)[:220]}",
        ) from exc
    saved = ai_provider_repository.save_key(ctx.company_id, provider, api_key)
    return {
        "connected": True,
        "provider": provider,
        "key_suffix": saved["key_suffix"],
    }


@router.put("/{provider}/model")
async def select_ai_provider_model(
    provider: str,
    body: AIProviderModelRequest,
    ctx=Depends(require_auth),
):
    provider = _validate_provider(provider)
    try:
        model = ai_service.save_selected_model(
            ctx.company_id, provider, body.model.strip()
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"provider": provider, "model": model}


@router.delete("/{provider}")
async def disconnect_ai_provider(provider: str, ctx=Depends(require_auth)):
    provider = _validate_provider(provider)
    return {
        "disconnected": ai_provider_repository.delete_key(ctx.company_id, provider),
        "provider": provider,
    }

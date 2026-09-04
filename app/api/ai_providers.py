"""Safe status API for server-managed AI Gateway providers."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import AIProviderConnectRequest, AIProviderModelRequest
from app.core.deps import require_auth
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
    del body, ctx
    _validate_provider(provider)
    raise HTTPException(
        status_code=403,
        detail="AI providers are managed by the server. Customer API keys are not accepted.",
    )


@router.put("/{provider}/model")
async def select_ai_provider_model(
    provider: str,
    body: AIProviderModelRequest,
    ctx=Depends(require_auth),
):
    del body, ctx
    _validate_provider(provider)
    raise HTTPException(
        status_code=403,
        detail="Provider and model selection is controlled by the AI Gateway.",
    )


@router.delete("/{provider}")
async def disconnect_ai_provider(provider: str, ctx=Depends(require_auth)):
    del ctx
    _validate_provider(provider)
    raise HTTPException(
        status_code=403,
        detail="Server-managed AI providers cannot be disconnected by customers.",
    )

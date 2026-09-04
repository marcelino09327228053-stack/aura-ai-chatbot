"""Authenticated development/staging Test Center API."""
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from app.api.schemas import LiveProviderTestRequest, LoadTestRequest
from app.core.deps import require_auth
from app.services import test_center_service
from scripts.load_test_ai_gateway import run_load

router = APIRouter(prefix="/testing", tags=["test-center"])

@router.get("/status")
def test_status(ctx=Depends(require_auth)):
    return test_center_service.diagnostics(ctx.company_id)

@router.post("/automated-tests")
async def automated_tests(ctx=Depends(require_auth)):
    del ctx
    return await asyncio.to_thread(test_center_service.run_automated_tests)

@router.post("/load-test")
async def load_test(body: LoadTestRequest, ctx=Depends(require_auth)):
    del ctx
    test_center_service.ensure_available()
    if not 1 <= body.requests <= 500 or not 1 <= body.customers <= 100:
        raise HTTPException(status_code=400, detail="Load test size is outside the safe web limit.")
    if not 1 <= body.global_limit <= 100 or not 1 <= body.customer_limit <= 20:
        raise HTTPException(status_code=400, detail="Concurrency value is outside the safe web limit.")
    return await run_load(body.requests, body.customers, min(max(body.service_ms, 1), 100),
                          body.global_limit, body.customer_limit)

@router.post("/provider-test")
async def provider_test(body: LiveProviderTestRequest, ctx=Depends(require_auth)):
    del ctx
    return await asyncio.to_thread(test_center_service.run_live_provider_test,
                                   body.confirm_billable)

"""Production subscription payment webhook endpoint."""
from fastapi import APIRouter, Header, Request
from app.services.payment_webhook_service import process_event

router = APIRouter(prefix="/webhooks/subscription", tags=["subscription-webhooks"])

@router.post("/payment")
async def subscription_payment(request: Request,
                               x_payment_signature: str | None = Header(default=None)):
    raw = await request.body()
    if len(raw) > 64 * 1024:
        from fastapi import HTTPException
        raise HTTPException(status_code=413, detail="Payment event is too large.")
    return process_event(raw, x_payment_signature)

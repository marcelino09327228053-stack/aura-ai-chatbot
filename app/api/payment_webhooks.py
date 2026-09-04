"""Production subscription payment webhook endpoint."""
from fastapi import APIRouter, Header, Request
from app.services.payment_webhook_service import process_event

router = APIRouter(prefix="/webhooks/subscription", tags=["subscription-webhooks"])

@router.post("/payment")
async def subscription_payment(request: Request,
                               x_payment_signature: str | None = Header(default=None)):
    return process_event(await request.body(), x_payment_signature)

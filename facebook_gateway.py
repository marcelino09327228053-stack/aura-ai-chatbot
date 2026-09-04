"""Minimal public gateway for Meta webhooks; does not expose the main dashboard."""

from fastapi import FastAPI

from app.api.facebook_messenger import router as facebook_messenger_router
from app.database.connection import init_db


def create_facebook_gateway() -> FastAPI:
    gateway = FastAPI(
        title="MB Future Tech AI Chatbot Facebook Messenger Gateway",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @gateway.get("/health")
    async def health():
        return {"status": "ok", "service": "facebook-messenger-webhook"}

    gateway.include_router(facebook_messenger_router)
    init_db()
    return gateway


app = create_facebook_gateway()

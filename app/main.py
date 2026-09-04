"""
FastAPI application factory.

Wires together:
  - CORS middleware
  - Static file mount (/static)
  - API routers (app/api/)
  - Database initialization on startup
"""

import importlib
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.agents.router import router as agents_router
from app.api.auth import router as auth_router
from app.infrastructure.monitoring.middleware import MonitoringMiddleware
from app.infrastructure.router import router as infrastructure_router
from app.cloud.api_gateway.v1_router import router as api_v1_router
from app.cloud.portal.router import router as cloud_portal_router
from app.network.router import router as network_router
from app.intelligence.router import router as intelligence_router
global_router = importlib.import_module("app.global.router").router
from app.enterprise.router import router as enterprise_router
from app.corporation.router import router as corporation_router
from app.economy.router import router as economy_router
from app.commerce.router import router as commerce_router
from app.ecosystem.router import router as ecosystem_router
from app.universe.router import router as universe_router
from app.civilization.router import router as civilization_router
from app.os.router import router as os_router
from app.plugins.router import router as plugins_router
from app.api.chat import router as chat_router
from app.api.ai_providers import router as ai_providers_router
from app.api.companies import router as companies_router
from app.api.conversations import router as conversations_router
from app.api.faq import router as faq_router
from app.api.profile_manager import router as profile_manager_router
from app.api.subscriptions import router as subscriptions_router
from app.api.widget import router as widget_router
from app.api.knowledge import router as knowledge_router
from app.api.facebook_messenger import router as facebook_messenger_router
from app.core.config import get_cors_origins
from app.core.middleware import SecurityHeadersMiddleware
from app.database.connection import init_db
from app.modules import register_modules


def create_app() -> FastAPI:
    application = FastAPI()

    os.makedirs("static", exist_ok=True)
    application.mount("/static", StaticFiles(directory="static"), name="static")

    application.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(MonitoringMiddleware)

    @application.get("/health", tags=["system"])
    async def health():
        try:
            connection = __import__(
                "app.database.connection", fromlist=["get_connection"]
            ).get_connection()
            connection.cursor().execute("SELECT 1")
            database = "ok"
        except Exception:
            database = "error"
        return {
            "status": "ok" if database == "ok" else "degraded",
            "database": database,
        }

    @application.get("/")
    async def root():
        return FileResponse(
            "index.html",
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    @application.get("/login")
    async def login_page():
        return FileResponse("login.html")

    @application.get("/register")
    async def register_page():
        return FileResponse("register.html")

    @application.get("/dashboard")
    async def dashboard_page():
        return FileResponse("dashboard.html")

    @application.get("/analytics-reports")
    async def analytics_reports_page():
        return FileResponse("analytics.html")

    @application.get("/subscription")
    async def subscription_page():
        return FileResponse("subscription.html")

    @application.get("/account")
    async def account_page():
        return FileResponse("account.html")

    @application.get("/plugins")
    async def plugins_page():
        return FileResponse("plugins.html")

    @application.get("/widget")
    async def widget_page():
        return FileResponse("widget.html")

    @application.get("/support")
    async def support_page():
        return FileResponse("support.html")

    @application.get("/team")
    async def team_page():
        return FileResponse("team.html")

    @application.get("/crm")
    async def crm_page():
        return FileResponse("crm.html")

    @application.get("/knowledge")
    async def knowledge_page():
        return FileResponse("knowledge.html")

    @application.get("/infrastructure")
    async def infrastructure_page():
        return FileResponse("infrastructure.html")

    @application.get("/portal")
    async def portal_page():
        return FileResponse("portal.html")

    @application.get("/os")
    async def os_page():
        return FileResponse("os.html")

    @application.get("/network")
    async def network_page():
        return FileResponse("network.html")

    @application.get("/intelligence")
    async def intelligence_page():
        return FileResponse("intelligence.html")

    @application.get("/global")
    async def global_page():
        return FileResponse("global.html")

    @application.get("/enterprise")
    async def enterprise_page():
        return FileResponse("enterprise.html")

    @application.get("/corporation")
    async def corporation_page():
        return FileResponse("corporation.html")

    @application.get("/economy")
    async def economy_page():
        return FileResponse("economy.html")

    @application.get("/commerce")
    async def commerce_page():
        return FileResponse("commerce.html")

    @application.get("/ecosystem")
    async def ecosystem_page():
        return FileResponse("ecosystem.html")

    @application.get("/universe")
    async def universe_page():
        return FileResponse("universe.html")

    @application.get("/civilization")
    async def civilization_page():
        return FileResponse("civilization.html")

    application.include_router(auth_router)
    application.include_router(companies_router)
    application.include_router(subscriptions_router)
    application.include_router(chat_router)
    application.include_router(ai_providers_router)
    application.include_router(conversations_router)
    application.include_router(faq_router)
    application.include_router(profile_manager_router)
    application.include_router(widget_router)
    application.include_router(knowledge_router)
    application.include_router(facebook_messenger_router)
    application.include_router(agents_router)
    application.include_router(plugins_router)
    application.include_router(infrastructure_router)
    application.include_router(cloud_portal_router)
    application.include_router(api_v1_router)
    application.include_router(os_router)
    application.include_router(network_router)
    application.include_router(intelligence_router)
    application.include_router(global_router)
    application.include_router(enterprise_router)
    application.include_router(corporation_router)
    application.include_router(economy_router)
    application.include_router(commerce_router)
    application.include_router(ecosystem_router)
    application.include_router(universe_router)
    application.include_router(civilization_router)

    register_modules(application)

    init_db()

    return application


app = create_app()

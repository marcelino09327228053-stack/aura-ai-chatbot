"""Authenticated widget management and token-scoped public chat endpoints."""

import re
import time
from collections import defaultdict, deque
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.agents.registry import route_message
from app.core.deps import require_auth
from app.database import company_repository
from app.database import conversation_repository
from app.database import widget_repository
from app.database.faq_repository import find_faq_answer

router = APIRouter(tags=["widget"])
_rate_buckets: dict[str, deque[float]] = defaultdict(deque)
_RATE_WINDOW_SECONDS = 60
_RATE_MAX_MESSAGES = 20


class WidgetUpdate(BaseModel):
    enabled: bool = True
    title: str = Field(default="Chat with us", min_length=1, max_length=80)
    welcome_message: str = Field(
        default="Hello! How can we help you today?", min_length=1, max_length=300
    )
    primary_color: str = "#7c3aed"
    position: str = "right"
    allowed_domains: list[str] = Field(default_factory=list, max_length=50)


class PublicWidgetMessage(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None
    language: str = "english"


def _validate_appearance(body: WidgetUpdate) -> None:
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", body.primary_color):
        raise HTTPException(status_code=422, detail="primary_color must be a six-digit hex color.")
    if body.position not in {"left", "right"}:
        raise HTTPException(status_code=422, detail="position must be left or right.")
    for domain in body.allowed_domains:
        normalized = domain.strip().lower()
        if not normalized or "/" in normalized or ":" in normalized or " " in normalized:
            raise HTTPException(
                status_code=422,
                detail="allowed_domains entries must be hostnames such as example.com.",
            )


def _request_origin(request: Request) -> str:
    return request.headers.get("origin") or request.headers.get("referer", "")


def _enforce_origin(settings: dict, request: Request) -> str:
    origin = _request_origin(request)
    allowed = {item.strip().lower() for item in settings["allowed_domains"] if item.strip()}
    if not allowed:
        return origin
    hostname = (urlparse(origin).hostname or "").lower()
    if hostname not in allowed:
        raise HTTPException(status_code=403, detail="This domain is not allowed to use the widget.")
    return origin


def _enforce_rate_limit(public_token: str, request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    key = f"{public_token}:{client}"
    now = time.monotonic()
    bucket = _rate_buckets[key]
    while bucket and bucket[0] <= now - _RATE_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= _RATE_MAX_MESSAGES:
        raise HTTPException(status_code=429, detail="Too many messages. Please wait a moment.")
    bucket.append(now)


@router.get("/widget/settings")
def get_widget_settings(ctx=Depends(require_auth)):
    return widget_repository.get_or_create(ctx.company_id)


@router.put("/widget/settings")
def update_widget_settings(body: WidgetUpdate, ctx=Depends(require_auth)):
    _validate_appearance(body)
    return widget_repository.update(ctx.company_id, body.model_dump())


@router.post("/widget/token/rotate")
def rotate_widget_token(ctx=Depends(require_auth)):
    return widget_repository.rotate_token(ctx.company_id)


@router.get("/widget/public/{public_token}/config")
def public_widget_config(public_token: str, request: Request):
    settings = widget_repository.get_by_token(public_token)
    if settings is None or not settings["enabled"]:
        raise HTTPException(status_code=404, detail="Widget not found.")
    origin = _enforce_origin(settings, request)
    widget_repository.record_event(settings["company_id"], "widget_loaded", origin=origin)
    company = company_repository.get_company(settings["company_id"])
    return {
        "company_name": company["company_name"],
        "title": settings["title"],
        "welcome_message": settings["welcome_message"],
        "primary_color": settings["primary_color"],
        "position": settings["position"],
    }


@router.post("/widget/public/{public_token}/chat")
async def public_widget_chat(public_token: str, body: PublicWidgetMessage, request: Request):
    settings = widget_repository.get_by_token(public_token)
    if settings is None or not settings["enabled"]:
        raise HTTPException(status_code=404, detail="Widget not found.")
    origin = _enforce_origin(settings, request)
    _enforce_rate_limit(public_token, request)
    company = company_repository.get_company(settings["company_id"])
    session_id = body.session_id or conversation_repository.new_session_id()
    support = conversation_repository.ensure_support_conversation(
        settings["company_id"], session_id
    )
    if support["mode"] == "human":
        conversation_repository.add_message(
            settings["company_id"], session_id, "user", body.text.strip()
        )
        widget_repository.record_event(
            settings["company_id"],
            "question",
            session_id=session_id,
            question=body.text.strip(),
            answer_source="human_queue",
            origin=origin,
        )
        return {
            "reply": "A support agent will reply shortly.",
            "session_id": session_id,
            "status": "waiting_for_agent",
        }
    existing_answer = find_faq_answer(body.text.strip(), settings["company_id"])
    result = await route_message(
        text=body.text.strip(),
        company_id=settings["company_id"],
        company_profile=company.get("company_profile", ""),
        language=body.language,
        session_id=session_id,
        user_id=f"widget:{body.session_id or 'new'}",
    )
    session_id = result.get("session_id", session_id)
    widget_repository.record_event(
        settings["company_id"],
        "question",
        session_id=session_id,
        question=body.text.strip(),
        answer_source="faq" if existing_answer else "ai",
        origin=origin,
    )
    if not body.session_id:
        widget_repository.record_event(
            settings["company_id"], "conversation_started", session_id=session_id, origin=origin
        )
    providers = result.get("provider_responses", [])
    if not existing_answer and (not providers or not any(item.get("ok") for item in providers)):
        widget_repository.record_event(
            settings["company_id"],
            "unanswered",
            session_id=session_id,
            question=body.text.strip(),
            origin=origin,
        )
    return result


@router.get("/widget/analytics")
def widget_analytics(
    days: int = Query(default=30, ge=1, le=365),
    ctx=Depends(require_auth),
):
    return widget_repository.get_analytics(ctx.company_id, days)

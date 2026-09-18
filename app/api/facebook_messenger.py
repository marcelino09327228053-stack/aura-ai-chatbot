"""Meta webhook endpoints for the Facebook Page Messenger channel."""

import json
import os

import asyncio
import base64
import hashlib
import hmac
import secrets
import time
from urllib.parse import urlencode

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from dotenv import load_dotenv

from app.services import facebook_messenger_service
from app.api.schemas import FacebookConnectRequest
from app.core.deps import require_auth
from app.database import facebook_connection_repository

load_dotenv(".env.facebook", override=False)

router = APIRouter(prefix="/webhooks/facebook", tags=["facebook-messenger"])

_OAUTH_TTL = 10 * 60


def _oauth_config() -> tuple[str, str]:
    return (
        os.getenv("FACEBOOK_APP_ID", "").strip(),
        os.getenv("FACEBOOK_APP_SECRET", "").strip(),
    )


def _sign_state(company_id: int, user_id: int, redirect_uri: str) -> str:
    payload = json.dumps({
        "company_id": company_id,
        "user_id": user_id,
        "redirect_uri": redirect_uri,
        "nonce": secrets.token_urlsafe(18),
        "expires": int(time.time()) + _OAUTH_TTL,
    }, separators=(",", ":")).encode()
    encoded = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    signature = hmac.new(
        os.getenv("SECRET_KEY", "facebook-oauth-dev").encode(), encoded.encode(), hashlib.sha256
    ).hexdigest()
    return f"{encoded}.{signature}"


def _read_state(state: str) -> dict:
    encoded, separator, supplied = state.partition(".")
    expected = hmac.new(
        os.getenv("SECRET_KEY", "facebook-oauth-dev").encode(), encoded.encode(), hashlib.sha256
    ).hexdigest()
    if separator != "." or not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=400, detail="Invalid Facebook login state.")
    padding = "=" * (-len(encoded) % 4)
    data = json.loads(base64.urlsafe_b64decode(encoded + padding))
    if int(data.get("expires", 0)) < int(time.time()):
        raise HTTPException(status_code=400, detail="Facebook login expired. Please try again.")
    return data


@router.get("/connection")
async def connection_status(ctx=Depends(require_auth)):
    app_id, app_secret = _oauth_config()
    connection = facebook_connection_repository.get_for_company(ctx.company_id)
    if not connection:
        return {"connected": False, "oauth_available": bool(app_id and app_secret)}
    return {
        "connected": True,
        "page_id": connection["page_id"],
        "page_name": connection["page_name"],
        "verify_token": connection["verify_token"],
        "oauth_available": bool(app_id and app_secret),
    }


@router.get("/oauth/start")
async def start_facebook_oauth(request: Request, ctx=Depends(require_auth)):
    app_id, app_secret = _oauth_config()
    if not app_id or not app_secret:
        raise HTTPException(
            status_code=503,
            detail="Facebook one-click login needs FACEBOOK_APP_ID in the server configuration.",
        )
    redirect_uri = os.getenv("FACEBOOK_OAUTH_REDIRECT_URI", "").strip()
    if not redirect_uri:
        redirect_uri = str(request.base_url).rstrip("/") + "/webhooks/facebook/oauth/callback"
    state = _sign_state(ctx.company_id, ctx.user_id, redirect_uri)
    query = urlencode({
        "client_id": app_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "response_type": "code",
        "scope": "pages_show_list,pages_messaging,pages_manage_metadata",
    })
    return {"authorization_url": f"https://www.facebook.com/dialog/oauth?{query}"}


@router.get("/oauth/callback", response_class=HTMLResponse)
async def facebook_oauth_callback(code: str = "", state: str = "", error: str = ""):
    if error:
        return HTMLResponse("<h2>Facebook connection was cancelled.</h2><script>setTimeout(close,1200)</script>")
    state_data = _read_state(state)
    app_id, app_secret = _oauth_config()
    try:
        user_token = await asyncio.to_thread(
            facebook_messenger_service.exchange_oauth_code,
            code,
            state_data["redirect_uri"],
            app_id,
            app_secret,
        )
        pages = await asyncio.to_thread(
            facebook_messenger_service.list_user_pages, user_token, app_secret
        )
    except Exception as exc:
        safe_error = json.dumps(str(exc)[:220])
        return HTMLResponse(f"<h2>Facebook connection failed.</h2><p id='e'></p><script>e.textContent={safe_error}</script>", status_code=400)
    session_id = secrets.token_urlsafe(24)
    facebook_connection_repository.save_oauth_session(
        session_id,
        int(state_data["company_id"]),
        int(state_data["user_id"]),
        pages,
        int(time.time()) + _OAUTH_TTL,
    )
    session_json = json.dumps(session_id)
    return HTMLResponse(
        "<h2>Facebook login complete.</h2><p>You can close this window.</p>"
        f"<script>if(opener)opener.postMessage({{type:'facebook-oauth-ready',session:{session_json}}},'*');setTimeout(close,700)</script>"
    )


def _oauth_session(session_id: str, ctx) -> dict:
    session = facebook_connection_repository.get_oauth_session(session_id)
    if (
        not session
        or session["expires_at"] < time.time()
        or session["company_id"] != ctx.company_id
        or session["user_id"] != ctx.user_id
    ):
        raise HTTPException(status_code=400, detail="Facebook login session expired.")
    return session


@router.get("/oauth/pages")
async def oauth_pages(session: str, ctx=Depends(require_auth)):
    data = _oauth_session(session, ctx)
    return {"pages": [
        {"page_id": page["page_id"], "page_name": page["page_name"]}
        for page in data["pages"]
    ]}


@router.post("/oauth/complete/{page_id}")
async def complete_facebook_oauth(page_id: str, session: str, ctx=Depends(require_auth)):
    data = _oauth_session(session, ctx)
    page = next((item for item in data["pages"] if item["page_id"] == page_id), None)
    if not page:
        raise HTTPException(status_code=404, detail="Facebook Page was not found.")
    _, app_secret = _oauth_config()
    try:
        verified = await asyncio.to_thread(
            facebook_messenger_service.connect_page,
            page["page_token"],
            app_secret,
            page["page_id"],
            page["page_name"],
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)[:260]) from exc
    saved = facebook_connection_repository.save(
        ctx.company_id, verified["page_id"], verified["page_name"], page["page_token"], app_secret
    )
    facebook_connection_repository.delete_oauth_session(session)
    return {"connected": True, "page_id": saved["page_id"], "page_name": saved["page_name"], "verify_token": saved["verify_token"]}


@router.post("/connection")
async def connect_page(body: FacebookConnectRequest, ctx=Depends(require_auth)):
    page_token = body.page_access_token.strip()
    app_secret = body.app_secret.strip()
    if len(page_token) < 20 or len(app_secret) < 8:
        raise HTTPException(status_code=400, detail="Enter a valid Page Access Token and App Secret.")
    try:
        page = await asyncio.to_thread(
            facebook_messenger_service.connect_page, page_token, app_secret
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)[:260]) from exc
    saved = facebook_connection_repository.save(
        ctx.company_id, page["page_id"], page["page_name"], page_token, app_secret
    )
    return {
        "connected": True,
        "page_id": saved["page_id"],
        "page_name": saved["page_name"],
        "verify_token": saved["verify_token"],
    }


@router.delete("/connection")
async def disconnect_page(ctx=Depends(require_auth)):
    return {"disconnected": facebook_connection_repository.delete(ctx.company_id)}


@router.get("")
async def verify_webhook(
    mode: str | None = Query(default=None, alias="hub.mode"),
    verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    expected = os.getenv("FACEBOOK_VERIFY_TOKEN", "").strip()
    token_matches = bool(expected and verify_token == expected)
    if verify_token and not token_matches:
        token_matches = facebook_connection_repository.verify_token_exists(verify_token)
    if token_matches and mode == "subscribe" and challenge:
        return PlainTextResponse(challenge)
    raise HTTPException(status_code=403, detail="Facebook webhook verification failed.")


@router.post("")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    try:
        payload = json.loads(body)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid Facebook payload.") from exc
    page_id = str(((payload.get("entry") or [{}])[0]).get("id", ""))
    connection = facebook_connection_repository.get_for_page(page_id) if page_id else None
    if not facebook_messenger_service.is_valid_signature(
        body,
        request.headers.get("x-hub-signature-256"),
        connection.get("app_secret") if connection else None,
    ):
        raise HTTPException(status_code=403, detail="Invalid Facebook signature.")
    if payload.get("object") != "page":
        raise HTTPException(status_code=400, detail="Unsupported Facebook object.")
    background_tasks.add_task(facebook_messenger_service.process_webhook, payload)
    return {"status": "received"}

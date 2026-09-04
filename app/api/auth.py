"""Authentication API routes."""

from pathlib import Path
import asyncio
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    RequestLoginCodeRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SelectCompanyRequest,
    VerifyLoginCodeRequest,
    AccountUpdateRequest,
    EmailChangeRequest,
    EmailChangeVerifyRequest,
)
from app.core.deps import get_auth_context, require_auth
from app.database import company_repository, subscription_repository
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

_GOOGLE_STATE_TTL = 10 * 60


def _google_config() -> tuple[str, str]:
    return (
        os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip(),
        os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip(),
    )


def _sign_google_state(nonce: str) -> str:
    payload = json.dumps(
        {"nonce": nonce, "expires": int(time.time()) + _GOOGLE_STATE_TTL},
        separators=(",", ":"),
    ).encode()
    encoded = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    signature = hmac.new(
        os.getenv("SECRET_KEY", "aura-dev-secret-change-in-production").encode(),
        encoded.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{encoded}.{signature}"


def _read_google_state(state: str) -> dict:
    encoded, separator, supplied = state.partition(".")
    expected = hmac.new(
        os.getenv("SECRET_KEY", "aura-dev-secret-change-in-production").encode(),
        encoded.encode(),
        hashlib.sha256,
    ).hexdigest()
    if separator != "." or not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=400, detail="Invalid Google login state.")
    try:
        padding = "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(encoded + padding))
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid Google login state.") from exc
    if int(payload.get("expires", 0)) < int(time.time()):
        raise HTTPException(status_code=400, detail="Google login expired. Please try again.")
    return payload


def _post_google_token(code: str, redirect_uri: str, client_id: str, client_secret: str) -> dict:
    body = urlencode({
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }).encode()
    request = UrlRequest(
        "https://oauth2.googleapis.com/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read())


def _get_google_userinfo(access_token: str) -> dict:
    request = UrlRequest(
        "https://openidconnect.googleapis.com/v1/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read())


def _google_callback_uri(request: Request) -> str:
    configured = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "").strip()
    return configured or str(request.base_url).rstrip("/") + "/auth/google/callback"


@router.get("/google/status")
def google_status():
    client_id, client_secret = _google_config()
    return {"available": bool(client_id and client_secret)}


@router.get("/google/start")
def google_start(request: Request):
    client_id, client_secret = _google_config()
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=503,
            detail="Google sign-in needs GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET.",
        )
    nonce = secrets.token_urlsafe(24)
    state = _sign_google_state(nonce)
    query = urlencode({
        "client_id": client_id,
        "redirect_uri": _google_callback_uri(request),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    })
    response = RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{query}")
    response.set_cookie(
        "mb_google_oauth_nonce",
        nonce,
        max_age=_GOOGLE_STATE_TTL,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
    )
    return response


@router.get("/google/callback", response_class=HTMLResponse)
async def google_callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
):
    if error:
        return RedirectResponse("/login?google_error=cancelled")
    payload = _read_google_state(state)
    cookie_nonce = request.cookies.get("mb_google_oauth_nonce", "")
    if not cookie_nonce or not hmac.compare_digest(payload.get("nonce", ""), cookie_nonce):
        raise HTTPException(status_code=400, detail="Google login session could not be verified.")
    client_id, client_secret = _google_config()
    if not client_id or not client_secret:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured.")
    try:
        token_data = await asyncio.to_thread(
            _post_google_token,
            code,
            _google_callback_uri(request),
            client_id,
            client_secret,
        )
        userinfo = await asyncio.to_thread(
            _get_google_userinfo, token_data.get("access_token", "")
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Google sign-in failed.") from exc
    if not userinfo.get("sub") or not userinfo.get("email") or not userinfo.get("email_verified"):
        raise HTTPException(status_code=400, detail="Google did not provide a verified email address.")
    result = auth_service.login_with_verified_identity(
        "google",
        str(userinfo["sub"]),
        str(userinfo["email"]),
        str(userinfo.get("name", "")),
        str(userinfo.get("picture", "")),
    )
    safe_result = json.dumps({
        "token": result["token"],
        "company_id": result["company"]["id"],
    })
    response = HTMLResponse(
        "<!doctype html><meta charset='utf-8'><title>Google sign-in complete</title>"
        "<script>const result=" + safe_result + ";"
        "localStorage.setItem('aura_token',result.token);"
        "localStorage.setItem('aura_company_id',String(result.company_id));"
        "location.replace('/');</script>"
    )
    response.delete_cookie("mb_google_oauth_nonce")
    return response


@router.post("/request-code")
def request_code(body: RequestLoginCodeRequest):
    return auth_service.request_login_code(body.email)


@router.post("/verify-code")
def verify_code(body: VerifyLoginCodeRequest):
    return auth_service.verify_login_code(body.email, body.code, body.company_name)


@router.post("/register")
def register(body: RegisterRequest):
    return auth_service.register_user(body.email, body.password, body.company_name)


@router.post("/login")
def login(body: LoginRequest):
    return auth_service.login_user(body.email, body.password)


@router.post("/logout")
def logout():
    """Logout is handled client-side by removing the JWT."""
    return {"message": "Logged out successfully."}


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest):
    return auth_service.request_password_reset(body.email)


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest):
    return auth_service.reset_password(body.token, body.new_password)


@router.get("/me")
def me(ctx=Depends(require_auth)):
    from app.database import user_repository

    profile = user_repository.get_user_by_id(ctx.user_id)
    companies = company_repository.list_companies_by_owner(ctx.user_id)
    company = company_repository.get_company(ctx.company_id)
    subscription = subscription_repository.get_subscription_by_company(ctx.company_id)

    return {
        "user": profile,
        "company": company,
        "companies": companies,
        "subscription": subscription,
    }


@router.put("/account")
def update_account(body: AccountUpdateRequest, ctx=Depends(require_auth)):
    from app.database import user_repository

    if len(body.full_name.strip()) > 100:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Name is too long.")
    return {"user": user_repository.update_profile(ctx.user_id, body.full_name)}


@router.post("/account/email/request")
def request_email_change(body: EmailChangeRequest, ctx=Depends(require_auth)):
    from app.database import user_repository

    existing = user_repository.get_user_by_email(body.new_email)
    if existing and existing["id"] != ctx.user_id:
        raise HTTPException(status_code=409, detail="Email is already in use.")
    return auth_service.request_login_code(body.new_email)


@router.post("/account/email/verify")
def verify_email_change(body: EmailChangeVerifyRequest, ctx=Depends(require_auth)):
    from app.database import user_repository

    existing = user_repository.get_user_by_email(body.new_email)
    if existing and existing["id"] != ctx.user_id:
        raise HTTPException(status_code=409, detail="Email is already in use.")
    auth_service.verify_confirmation_code(body.new_email, body.code)
    return {"user": user_repository.update_email(ctx.user_id, body.new_email)}


@router.post("/account/photo")
async def upload_account_photo(
    photo: UploadFile = File(...),
    ctx=Depends(require_auth),
):
    from PIL import Image, UnidentifiedImageError
    from app.database import user_repository

    if photo.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="Use a JPG, PNG or WebP image.")
    content = await photo.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Profile image must be 5 MB or smaller.")
    upload_dir = Path("static/profile-images")
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"user-{ctx.user_id}-{secrets.token_hex(6)}.webp"
    target = upload_dir / filename
    try:
        from io import BytesIO
        image = Image.open(BytesIO(content))
        image.verify()
        image = Image.open(BytesIO(content)).convert("RGB")
        image.thumbnail((512, 512))
        image.save(target, "WEBP", quality=86)
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="Invalid image file.")
    path = f"/static/profile-images/{filename}"
    return {"user": user_repository.update_profile_image(ctx.user_id, path)}


@router.post("/select-company")
def select_company(body: SelectCompanyRequest, ctx=Depends(require_auth)):
    return auth_service.select_company(ctx.user_id, body.company_id)

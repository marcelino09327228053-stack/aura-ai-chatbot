"""Facebook Messenger transport for Aura's existing chat pipeline."""

import asyncio
import hashlib
import hmac
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv

from app.database import company_repository
from app.database import facebook_connection_repository
from app.services.ai_observability import emit
from app.services.chat_service import handle_chat
from app.services.spam_protection import check_message

load_dotenv(".env.facebook", override=False)

_processed_messages: dict[str, float] = {}
_DEDUP_TTL_SECONDS = 60 * 60


def is_valid_signature(body: bytes, signature_header: str | None, app_secret: str | None = None) -> bool:
    """Validate Meta's X-Hub-Signature-256 HMAC without leaking secrets."""
    app_secret = (app_secret or os.getenv("FACEBOOK_APP_SECRET", "")).strip()
    if not app_secret or not signature_header:
        return False
    algorithm, separator, supplied_digest = signature_header.partition("=")
    if separator != "=" or algorithm.lower() != "sha256" or not supplied_digest:
        return False
    expected = hmac.new(
        app_secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, supplied_digest)


def _claim_message(message_id: str) -> bool:
    """Return False for recently processed webhook retries."""
    now = time.monotonic()
    expired = [key for key, seen_at in _processed_messages.items()
               if now - seen_at > _DEDUP_TTL_SECONDS]
    for key in expired:
        _processed_messages.pop(key, None)
    if message_id in _processed_messages:
        return False
    _processed_messages[message_id] = now
    return True


def _configured_providers() -> list[str]:
    configured = os.getenv("FACEBOOK_AI_PROVIDERS", "gemini")
    providers = [item.strip().lower() for item in configured.split(",") if item.strip()]
    return providers or ["gemini"]


def _message_chunks(text: str, limit: int = 1900) -> list[str]:
    """Split long AI responses below Messenger's text-message limit."""
    text = text.strip()
    if not text:
        return ["MB Future Tech AI Chatbot could not generate a response. Please try again."]
    chunks: list[str] = []
    while len(text) > limit:
        split_at = max(text.rfind("\n", 0, limit), text.rfind(" ", 0, limit))
        if split_at < limit // 2:
            split_at = limit
        chunks.append(text[:split_at].strip())
        text = text[split_at:].strip()
    if text:
        chunks.append(text)
    return chunks


def _graph_request(
    path: str,
    page_token: str,
    method: str = "GET",
    data: dict | None = None,
    app_secret: str | None = None,
) -> dict:
    graph_version = os.getenv("FACEBOOK_GRAPH_API_VERSION", "v23.0").strip()
    query_values = {"access_token": page_token}
    if app_secret:
        query_values["appsecret_proof"] = hmac.new(
            app_secret.encode("utf-8"), page_token.encode("utf-8"), hashlib.sha256
        ).hexdigest()
    query = urlencode(query_values)
    payload = urlencode(data or {}).encode("utf-8") if method != "GET" else None
    request = Request(
        f"https://graph.facebook.com/{graph_version}/{path}?{query}",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method=method,
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Facebook connection failed ({exc.code}): {detail[:240]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach Facebook: {exc.reason}") from exc


def connect_page(
    page_token: str,
    app_secret: str,
    known_page_id: str | None = None,
    known_page_name: str | None = None,
) -> dict:
    """Validate a Page token and subscribe the app to supported message events."""
    if known_page_id:
        page_id = str(known_page_id).strip()
        page_name = str(known_page_name or "Facebook Page")
    else:
        page = _graph_request("me", page_token, app_secret=app_secret)
        page_id = str(page.get("id", "")).strip()
        page_name = str(page.get("name", "Facebook Page"))
    if not page_id:
        raise RuntimeError("Facebook did not return a valid Page ID.")
    _graph_request(
        f"{page_id}/subscribed_apps",
        page_token,
        method="POST",
        data={"subscribed_fields": "messages,messaging_postbacks"},
        app_secret=app_secret,
    )
    return {"page_id": page_id, "page_name": page_name}


def exchange_oauth_code(code: str, redirect_uri: str, app_id: str, app_secret: str) -> str:
    query = urlencode({
        "client_id": app_id,
        "client_secret": app_secret,
        "redirect_uri": redirect_uri,
        "code": code,
    })
    request = Request(
        f"https://graph.facebook.com/{os.getenv('FACEBOOK_GRAPH_API_VERSION', 'v23.0')}/oauth/access_token?{query}",
        method="GET",
    )
    try:
        with urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Facebook login failed ({exc.code}): {detail[:240]}") from exc
    token = str(data.get("access_token", ""))
    if not token:
        raise RuntimeError("Facebook did not return an access token.")
    return token


def list_user_pages(user_token: str, app_secret: str) -> list[dict]:
    data = _graph_request(
        "me/accounts",
        user_token,
        app_secret=app_secret,
    )
    pages = []
    for page in data.get("data", []):
        token = str(page.get("access_token", ""))
        page_id = str(page.get("id", ""))
        if token and page_id:
            pages.append({
                "page_id": page_id,
                "page_name": str(page.get("name", "Facebook Page")),
                "page_token": token,
            })
    return pages


def _send_text_sync(recipient_id: str, text: str, page_token: str | None = None) -> None:
    page_token = (page_token or os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "")).strip()
    if not page_token:
        raise RuntimeError("FACEBOOK_PAGE_ACCESS_TOKEN is not configured.")
    graph_version = os.getenv("FACEBOOK_GRAPH_API_VERSION", "v23.0").strip()
    query = urlencode({"access_token": page_token})
    url = f"https://graph.facebook.com/{graph_version}/me/messages?{query}"
    payload = json.dumps({
        "recipient": {"id": recipient_id},
        "messaging_type": "RESPONSE",
        "message": {"text": text},
    }).encode("utf-8")
    request = Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Facebook Send API failed ({exc.code}): {detail[:240]}"
        ) from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach Facebook Send API: {exc.reason}") from exc


async def send_text(recipient_id: str, text: str, page_token: str | None = None) -> None:
    for chunk in _message_chunks(text):
        await asyncio.to_thread(_send_text_sync, recipient_id, chunk, page_token)


async def process_webhook(payload: dict) -> None:
    """Process supported Page message events after the webhook is acknowledged."""
    if payload.get("object") != "page":
        emit("facebook_webhook_skipped", reason="unsupported_object")
        return
    # External customer channels follow each customer's message language.
    # The website/dashboard language selector remains an independent manual override.
    language = "auto"

    entries = payload.get("entry", [])
    emit("facebook_webhook_processing", entry_count=len(entries))
    for entry in entries:
        page_id = str(entry.get("id", "page"))
        connection = facebook_connection_repository.get_for_page(page_id)
        company_id = int(connection["company_id"]) if connection else int(os.getenv("FACEBOOK_COMPANY_ID", "1"))
        page_token = connection.get("page_token") if connection else None
        company = company_repository.get_company(company_id)
        if not company:
            emit(
                "facebook_webhook_entry_skipped",
                company_id=company_id,
                connection_found=bool(connection),
                reason="company_not_found",
            )
            continue
        events = entry.get("messaging", [])
        emit(
            "facebook_webhook_entry",
            company_id=company_id,
            connection_found=bool(connection),
            event_count=len(events),
        )
        for event in events:
            try:
                message = event.get("message") or {}
                sender_id = str((event.get("sender") or {}).get("id", ""))
                message_id = str(message.get("mid", ""))
                text = message.get("text")
                if not sender_id or not message_id or not isinstance(text, str):
                    emit("facebook_message_skipped", company_id=company_id, reason="unsupported_message")
                    continue
                if message.get("is_echo"):
                    emit("facebook_message_skipped", company_id=company_id, reason="echo")
                    continue
                if not _claim_message(message_id):
                    emit("facebook_message_skipped", company_id=company_id, reason="duplicate")
                    continue
                spam = check_message(company_id, "facebook", sender_id, text)
                if spam["blocked"]:
                    emit(
                        "facebook_message_skipped",
                        company_id=company_id,
                        reason="spam_blocked",
                        new_block=bool(spam["new_block"]),
                    )
                    if spam["new_block"]:
                        warning = (
                            "Too many repeated messages were detected. Please wait 15 minutes "
                            "before sending another message."
                        )
                        if page_token:
                            await send_text(sender_id, warning, page_token)
                        else:
                            await send_text(sender_id, warning)
                    continue
                emit("facebook_message_received", company_id=company_id)
                result = await handle_chat(
                    text=text.strip(),
                    company_id=company_id,
                    company_profile=company.get("company_profile", ""),
                    language=language,
                    session_id=f"facebook:{page_id}:{sender_id}",
                    providers=_configured_providers(),
                )
                reply = result.get("reply", "")
                emit("facebook_ai_result", company_id=company_id, reply_length=len(reply))
                if page_token:
                    await send_text(sender_id, reply, page_token)
                else:
                    await send_text(sender_id, reply)
                emit("facebook_reply_sent", company_id=company_id)
            except Exception as exc:
                emit(
                    "facebook_processing_failed",
                    company_id=company_id,
                    error_type=type(exc).__name__,
                    error=str(exc)[:240],
                )
                raise

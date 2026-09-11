"""Referral capture, attribution and agent-facing application logic."""
import hashlib
import hmac
import os
import secrets
import time
from pathlib import Path

from fastapi import HTTPException

from app.core.config import SECRET_KEY
from app.referrals import repository

COOKIE_NAME = "mb_referral"
COOKIE_MAX_AGE = 30 * 24 * 60 * 60
PRIVATE_ID_DIR = Path(os.getenv("REFERRAL_PRIVATE_ID_DIR", ".private/referral-ids"))
PRIVATE_PROFILE_DIR = Path(os.getenv("REFERRAL_PRIVATE_PROFILE_DIR", ".private/referral-profiles"))
ALLOWED_ID_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "application/pdf": ".pdf"}
MAX_ID_BYTES = 8 * 1024 * 1024
ALLOWED_PROFILE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAX_PROFILE_BYTES = 3 * 1024 * 1024


def _safe_agent(agent: dict) -> dict:
    allowed=("id","user_id","referral_code","status","payout_eligible","created_at","approved_at",
             "suspended_at","submitted_at","reviewed_at","full_name","application_email",
             "mobile_number","address_location","id_type","payout_method","profile_bio")
    return {key:agent.get(key) for key in allowed}


def _signature(value: str) -> str:
    return hmac.new(SECRET_KEY.encode(), value.encode(), hashlib.sha256).hexdigest()


def capture_token(code: str) -> tuple[str, dict]:
    agent = repository.get_agent_by_code(code, active_only=True)
    if not agent: raise HTTPException(status_code=404, detail="Referral link is invalid or inactive.")
    issued = str(int(time.time())); nonce = hashlib.sha256(f"{issued}:{code}:{time.time_ns()}".encode()).hexdigest()[:24]
    value = f"{agent['id']}:{issued}:{nonce}"
    token = f"{value}:{_signature(value)}"
    repository.record_click(agent["id"], nonce)
    return token, agent


def agent_id_from_token(token: str | None) -> int | None:
    try:
        agent_id, issued, nonce, signature = (token or "").split(":", 3)
        value = f"{agent_id}:{issued}:{nonce}"
        if not hmac.compare_digest(_signature(value), signature): return None
        if int(time.time()) - int(issued) > COOKIE_MAX_AGE: return None
        agent = repository.get_agent(int(agent_id), active_only=True)
        return int(agent_id) if agent else None
    except (ValueError, TypeError, KeyError, AttributeError):
        return None


def apply(user_id: int) -> dict:
    agent, created = repository.apply_for_agent(user_id)
    return {"agent": _safe_agent(agent), "created": created}


def store_identity_document(filename: str, content_type: str, content: bytes) -> dict:
    if content_type not in ALLOWED_ID_TYPES: raise HTTPException(400,"ID must be a JPG, PNG, or PDF.")
    if not content or len(content)>MAX_ID_BYTES: raise HTTPException(400,"ID document must be between 1 byte and 8 MB.")
    signatures={"image/jpeg":content.startswith(b"\xff\xd8\xff"),"image/png":content.startswith(b"\x89PNG\r\n\x1a\n"),"application/pdf":content.startswith(b"%PDF-")}
    if not signatures[content_type]:raise HTTPException(400,"ID document content does not match its file type.")
    PRIVATE_ID_DIR.mkdir(parents=True,exist_ok=True)
    storage_name=secrets.token_hex(24)+ALLOWED_ID_TYPES[content_type]
    target=PRIVATE_ID_DIR/storage_name
    with open(target,"xb") as handle:handle.write(content)
    return {"storage_name":storage_name,"original_name":Path(filename or "identity-document").name[:160],
            "content_type":content_type,"sha256":hashlib.sha256(content).hexdigest()}


def submit_application(user_id: int, values: dict, upload: dict) -> dict:
    required=("full_name","email","mobile_number","address_location","id_type","payout_method","account_holder_name","account_number")
    if any(not str(values.get(k,"")).strip() for k in required):raise HTTPException(400,"Complete all required application fields.")
    if values["payout_method"] not in {"gcash","maya","bank_transfer"}:raise HTTPException(400,"Unsupported payout method.")
    if values["payout_method"]=="bank_transfer" and not values.get("bank_name","").strip():raise HTTPException(400,"Bank name is required.")
    document=store_identity_document(upload["filename"],upload["content_type"],upload["content"])
    try:return _safe_agent(repository.save_application(user_id,{k:str(v).strip() for k,v in values.items()},document))
    except Exception:
        try:(PRIVATE_ID_DIR/document["storage_name"]).unlink(missing_ok=True)
        except OSError:pass
        raise


def own_document(user_id: int) -> tuple[Path,str,str]:
    agent=repository.get_agent_by_user(user_id)
    if not agent or not agent.get("id_storage_name"):raise HTTPException(404,"Identity document not found.")
    path=(PRIVATE_ID_DIR/agent["id_storage_name"]).resolve();root=PRIVATE_ID_DIR.resolve()
    if root not in path.parents or not path.is_file():raise HTTPException(404,"Identity document not found.")
    return path,agent["id_content_type"],agent["id_original_name"]


def update_profile(user_id: int, values: dict, upload: dict | None) -> dict:
    agent = repository.get_agent_by_user(user_id)
    if not agent or agent.get("status") != "approved":
        raise HTTPException(403, "An approved agent account is required.")
    full_name = str(values.get("full_name", "")).strip()
    if not full_name or len(full_name) > 100:
        raise HTTPException(400, "Full name is required and must be 100 characters or fewer.")
    mobile = str(values.get("mobile_number", "")).strip()[:40]
    location = str(values.get("address_location", "")).strip()[:180]
    bio = str(values.get("profile_bio", "")).strip()[:280]
    photo = None
    if upload and upload.get("content"):
        content_type = upload.get("content_type", "")
        content = upload["content"]
        if content_type not in ALLOWED_PROFILE_TYPES:
            raise HTTPException(400, "Profile picture must be a JPG, PNG, or WebP image.")
        if len(content) > MAX_PROFILE_BYTES:
            raise HTTPException(400, "Profile picture must not exceed 3 MB.")
        signatures = {"image/jpeg": content.startswith(b"\xff\xd8\xff"),
                      "image/png": content.startswith(b"\x89PNG\r\n\x1a\n"),
                      "image/webp": content.startswith(b"RIFF") and content[8:12] == b"WEBP"}
        if not signatures[content_type]:
            raise HTTPException(400, "Profile picture content does not match its file type.")
        PRIVATE_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        photo = {"storage_name": secrets.token_hex(24) + ALLOWED_PROFILE_TYPES[content_type],
                 "content_type": content_type}
        with open(PRIVATE_PROFILE_DIR / photo["storage_name"], "xb") as handle:
            handle.write(content)
    old_name = agent.get("profile_storage_name", "")
    try:
        updated = repository.update_profile(user_id, full_name, mobile, location, bio, photo)
    except Exception:
        if photo:
            (PRIVATE_PROFILE_DIR / photo["storage_name"]).unlink(missing_ok=True)
        raise
    if photo and old_name:
        (PRIVATE_PROFILE_DIR / old_name).unlink(missing_ok=True)
    return _safe_agent(updated)


def own_profile_photo(user_id: int) -> tuple[Path, str]:
    agent = repository.get_agent_by_user(user_id)
    if not agent or not agent.get("profile_storage_name"):
        raise HTTPException(404, "Profile picture not found.")
    path = (PRIVATE_PROFILE_DIR / agent["profile_storage_name"]).resolve()
    root = PRIVATE_PROFILE_DIR.resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(404, "Profile picture not found.")
    return path, agent["profile_content_type"]


def owner_document(agent_id: int) -> tuple[Path,str,str]:
    agent=repository.get_agent(agent_id)
    if not agent or not agent.get("id_storage_name"):raise HTTPException(404,"Identity document not found.")
    path=(PRIVATE_ID_DIR/agent["id_storage_name"]).resolve();root=PRIVATE_ID_DIR.resolve()
    if root not in path.parents or not path.is_file():raise HTTPException(404,"Identity document not found.")
    return path,agent["id_content_type"],agent["id_original_name"]


def public_dashboard(user_id: int, base_url: str) -> dict:
    data = repository.dashboard_for_user(user_id)
    if not data: return {"agent": None}
    data["agent"]=_safe_agent(data["agent"])
    data["agent"]["has_profile_photo"] = bool(repository.get_agent_by_user(user_id).get("profile_storage_name"))
    code = data["agent"]["referral_code"]
    data["referral_link"] = f"{base_url.rstrip('/')}/register?ref={code}"
    return data

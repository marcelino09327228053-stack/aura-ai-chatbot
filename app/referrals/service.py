"""Referral capture, attribution and agent-facing application logic."""
import hashlib
import hmac
import time

from fastapi import HTTPException

from app.core.config import SECRET_KEY
from app.referrals import repository

COOKIE_NAME = "mb_referral"
COOKIE_MAX_AGE = 30 * 24 * 60 * 60


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
    return {"agent": agent, "created": created}


def public_dashboard(user_id: int, base_url: str) -> dict:
    data = repository.dashboard_for_user(user_id)
    if not data: return {"agent": None}
    code = data["agent"]["referral_code"]
    data["referral_link"] = f"{base_url.rstrip('/')}/register?ref={code}"
    return data

"""Plugin platform security — API keys and permission enforcement."""

import secrets

from fastapi import Header, HTTPException

from app.core.security import hash_token
from app.plugins.registry import repository as plugin_repo


def generate_api_key() -> tuple[str, str, str]:
    """Return (raw_key, key_hash, key_prefix)."""
    raw = f"aura_pk_{secrets.token_urlsafe(32)}"
    return raw, hash_token(raw), raw[:12]


def create_company_api_key(company_id: int, name: str) -> dict:
    raw, key_hash, prefix = generate_api_key()
    row = plugin_repo.create_api_key(company_id, name, key_hash, prefix)
    row["key"] = raw
    return row


def resolve_api_key(x_plugin_api_key: str | None) -> dict | None:
    if not x_plugin_api_key:
        return None
    key_hash = hash_token(x_plugin_api_key)
    record = plugin_repo.get_api_key_by_hash(key_hash)
    if record:
        plugin_repo.touch_api_key(record["id"])
    return record


def require_plugin_api_key(
    x_plugin_api_key: str | None = Header(default=None, alias="X-Plugin-API-Key"),
) -> dict:
    record = resolve_api_key(x_plugin_api_key)
    if not record:
        raise HTTPException(status_code=401, detail="Valid X-Plugin-API-Key header required.")
    return record


def check_plugin_permission(plugin: dict, permission: str) -> None:
    granted = plugin.get("manifest", {}).get("permissions", [])
    if permission not in granted:
        raise HTTPException(
            status_code=403,
            detail=f"Plugin does not have permission: {permission}",
        )

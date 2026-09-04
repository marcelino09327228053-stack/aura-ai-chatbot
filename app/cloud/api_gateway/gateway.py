"""API Gateway — rate limiting, usage tracking, access control."""

import time
from collections import defaultdict

from fastapi import Header, HTTPException

from app.cloud.api_gateway import repository as gateway_repo
from app.core.security import hash_token
from app.infrastructure.audit import service as audit_service

_rate_buckets: dict[str, list[float]] = defaultdict(list)


def resolve_api_key(x_api_key: str | None) -> dict | None:
    if not x_api_key:
        return None
    return gateway_repo.get_key_by_hash(hash_token(x_api_key))


def check_rate_limit(api_key: dict) -> None:
    key_id = str(api_key["id"])
    limit = api_key.get("rate_limit", 60)
    now = time.time()
    window = _rate_buckets[key_id]
    window[:] = [t for t in window if now - t < 60]
    if len(window) >= limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")
    window.append(now)


def check_scope(api_key: dict, required: str) -> None:
    scopes = set(s.strip() for s in api_key.get("scopes", "").split(",") if s.strip())
    if required not in scopes and "admin" not in scopes:
        raise HTTPException(status_code=403, detail=f"Missing scope: {required}")


def require_cloud_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    required_scope: str = "read",
) -> dict:
    record = resolve_api_key(x_api_key)
    if not record:
        raise HTTPException(status_code=401, detail="Valid X-API-Key header required.")
    check_rate_limit(record)
    check_scope(record, required_scope)
    gateway_repo.touch_api_key(record["id"])
    return record


def track_request(api_key: dict, endpoint: str, method: str) -> None:
    gateway_repo.log_usage(api_key["company_id"], api_key["id"], endpoint, method)
    audit_service.record(f"api.{method}:{endpoint}", api_key["company_id"], None)

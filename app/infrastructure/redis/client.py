"""Redis client with in-memory fallback."""

import json
import os
import time
from typing import Any

_redis_client = None
_memory_store: dict[str, tuple[Any, float | None]] = {}


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


def is_redis_available() -> bool:
    return get_client() is not None


def get_client():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if os.getenv("REDIS_ENABLED", "false").lower() not in ("1", "true", "yes"):
        return None
    try:
        import redis
        _redis_client = redis.from_url(_redis_url(), decode_responses=True)
        _redis_client.ping()
        return _redis_client
    except Exception:
        _redis_client = None
        return None


def set_value(key: str, value: Any, ttl_seconds: int | None = None) -> None:
    client = get_client()
    payload = json.dumps(value)
    if client:
        if ttl_seconds:
            client.setex(key, ttl_seconds, payload)
        else:
            client.set(key, payload)
        return
    expires = time.time() + ttl_seconds if ttl_seconds else None
    _memory_store[key] = (payload, expires)


def get_value(key: str) -> Any | None:
    client = get_client()
    if client:
        raw = client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    entry = _memory_store.get(key)
    if not entry:
        return None
    payload, expires = entry
    if expires and time.time() > expires:
        del _memory_store[key]
        return None
    return json.loads(payload)


def delete_value(key: str) -> None:
    client = get_client()
    if client:
        client.delete(key)
        return
    _memory_store.pop(key, None)

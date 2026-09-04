"""API response cache backed by Redis (or memory fallback)."""

import hashlib
import json

from app.infrastructure.redis.client import delete_value, get_value, set_value

DEFAULT_TTL = 300


def cache_key(prefix: str, *parts) -> str:
    raw = ":".join(str(p) for p in parts)
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"api:{prefix}:{digest}"


def get_cached(prefix: str, *parts):
    return get_value(cache_key(prefix, *parts))


def set_cached(prefix: str, data, *parts, ttl: int = DEFAULT_TTL) -> None:
    set_value(cache_key(prefix, *parts), data, ttl_seconds=ttl)


def invalidate(prefix: str, *parts) -> None:
    delete_value(cache_key(prefix, *parts))


def cached_response(prefix: str, builder, *parts, ttl: int = DEFAULT_TTL):
    """Return cached value or call builder() and cache result."""
    hit = get_cached(prefix, *parts)
    if hit is not None:
        return hit
    result = builder()
    set_cached(prefix, result, *parts, ttl=ttl)
    return result

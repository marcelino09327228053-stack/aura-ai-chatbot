"""Session cache backed by Redis (or memory fallback)."""

from app.infrastructure.redis.client import delete_value, get_value, set_value

SESSION_TTL = 86400


def session_key(session_id: str) -> str:
    return f"session:{session_id}"


def save_session(session_id: str, data: dict) -> None:
    set_value(session_key(session_id), data, ttl_seconds=SESSION_TTL)


def load_session(session_id: str) -> dict | None:
    return get_value(session_key(session_id))


def clear_session(session_id: str) -> None:
    delete_value(session_key(session_id))

"""Secret-safe structured events and in-process Gateway counters."""

from collections import Counter
import json
import logging
import threading

logger = logging.getLogger("aura.ai_gateway")
_metrics = Counter()
_lock = threading.Lock()


def emit(event: str, **fields) -> None:
    blocked_fragments = ("key", "password", "secret", "token", "authorization", "prompt", "response")
    safe = {
        key: value for key, value in fields.items()
        if not any(fragment in key.lower() for fragment in blocked_fragments)
    }
    with _lock:
        _metrics[event] += 1
    logger.info("ai_gateway_event %s", json.dumps({"event": event, **safe}, default=str, sort_keys=True))


def metrics_snapshot() -> dict:
    with _lock: return dict(_metrics)


def reset_metrics() -> None:
    with _lock: _metrics.clear()

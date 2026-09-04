"""Secret-safe structured events and in-process Gateway counters."""

from collections import Counter
import json
import logging
import threading

logger = logging.getLogger("aura.ai_gateway")
_metrics = Counter()
_gauges = {}
_lock = threading.Lock()


def emit(event: str, **fields) -> None:
    blocked_fragments = ("key", "password", "secret", "token", "authorization", "prompt", "response")
    safe = {
        key: value for key, value in fields.items()
        if not any(fragment in key.lower() for fragment in blocked_fragments)
    }
    with _lock:
        _metrics[event] += 1
        if "latency_ms" in safe:
            _metrics["request_latency_ms_count"] += 1
            _metrics["request_latency_ms_sum"] += float(safe["latency_ms"])
        if "queue_wait_ms" in safe:
            _metrics["queue_wait_ms_count"] += 1
            _metrics["queue_wait_ms_sum"] += float(safe["queue_wait_ms"])
        if "queue_size" in safe:
            _gauges["queue_size"] = float(safe["queue_size"])
    logger.info("ai_gateway_event %s", json.dumps({"event": event, **safe}, default=str, sort_keys=True))


def metrics_snapshot() -> dict:
    with _lock: return {"counters": dict(_metrics), "gauges": dict(_gauges)}


def prometheus_text() -> str:
    """Render dependency-free Prometheus exposition format."""
    snapshot = metrics_snapshot()
    lines = ["# HELP aura_ai_gateway_events_total AI Gateway structured event totals.",
             "# TYPE aura_ai_gateway_events_total counter"]
    reserved = {"request_latency_ms_count", "request_latency_ms_sum", "queue_wait_ms_count", "queue_wait_ms_sum"}
    for event, value in sorted(snapshot["counters"].items()):
        if event not in reserved:
            lines.append(f'aura_ai_gateway_events_total{{event="{event}"}} {value}')
    for name in ("request_latency_ms", "queue_wait_ms"):
        lines.extend([f"# TYPE aura_ai_gateway_{name} summary",
                      f"aura_ai_gateway_{name}_count {snapshot['counters'].get(name + '_count', 0)}",
                      f"aura_ai_gateway_{name}_sum {snapshot['counters'].get(name + '_sum', 0)}"])
    lines.extend(["# TYPE aura_ai_gateway_queue_size gauge",
                  f"aura_ai_gateway_queue_size {snapshot['gauges'].get('queue_size', 0)}"])
    return "\n".join(lines) + "\n"


def reset_metrics() -> None:
    with _lock:
        _metrics.clear()
        _gauges.clear()

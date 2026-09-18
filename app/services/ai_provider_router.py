"""Authorized provider routing and temporary health state."""

from dataclasses import dataclass
import math
import threading
import time
import json

from app.core.config import AI_GATEWAY_PROVIDER_COOLDOWN_SECONDS, AI_GATEWAY_PROVIDER_ORDER, AI_MODEL_COSTS_USD
from app.services import ai_service
from app.infrastructure.redis.client import get_client


@dataclass(frozen=True)
class RouteCandidate:
    provider: str
    model: str
    priority: int
    pricing: dict | None
    capability_tier: str = "balanced"


class ProviderHealthRegistry:
    def __init__(self):
        self._lock = threading.Lock()
        self._health: dict[str, dict] = {}

    def reset(self):
        with self._lock:
            self._health.clear()

    def mark_healthy(self, provider: str):
        with self._lock:
            self._health[provider] = {"state": "healthy", "reason": None, "until": 0.0}
        client = get_client()
        if client:
            try:
                client.delete(f"aura:ai:provider-health:{provider}")
            except Exception:
                pass

    def mark_cooldown(self, provider: str, reason: str, seconds: float | None = None,
                      state: str = "cooldown"):
        duration = max(0.0, seconds if seconds is not None else AI_GATEWAY_PROVIDER_COOLDOWN_SECONDS)
        with self._lock:
            self._health[provider] = {"state": state, "reason": reason, "until": time.monotonic() + duration}
        client = get_client()
        if client:
            try:
                client.setex(
                    f"aura:ai:provider-health:{provider}",
                    max(1, math.ceil(duration)),
                    json.dumps({"state": state, "reason": reason}),
                )
            except Exception:
                pass

    def status(self, provider: str) -> dict:
        client = get_client()
        if client:
            try:
                raw = client.get(f"aura:ai:provider-health:{provider}")
                if raw:
                    value = json.loads(raw)
                    return {
                        **value,
                        "cooldown_remaining": max(
                            0.0,
                            float(client.ttl(f"aura:ai:provider-health:{provider}")),
                        ),
                    }
            except Exception:
                pass
        with self._lock:
            value = dict(self._health.get(provider, {"state": "healthy", "reason": None, "until": 0.0}))
        remaining = max(0.0, value["until"] - time.monotonic())
        if value["state"] != "healthy" and remaining <= 0:
            self.mark_healthy(provider)
            return {"state": "healthy", "reason": None, "cooldown_remaining": 0.0}
        return {"state": value["state"], "reason": value["reason"], "cooldown_remaining": remaining}

    def snapshot(self) -> dict:
        return {provider: self.status(provider) for provider in ai_service.PROVIDERS}


provider_health = ProviderHealthRegistry()


def _valid_pricing(pricing: object) -> bool:
    """Return True only for a complete, non-negative metering configuration."""
    if not isinstance(pricing, dict):
        return False
    try:
        input_rate = float(pricing["input_per_million"])
        output_rate = float(pricing["output_per_million"])
    except (KeyError, TypeError, ValueError):
        return False
    return math.isfinite(input_rate) and math.isfinite(output_rate) and input_rate >= 0 and output_rate >= 0


def route_candidates(capability_tier: str = "balanced") -> list[RouteCandidate]:
    """Return providers that are callable, healthy, and safe to meter.

    A provider without a valid pricing entry must never be called: a successful
    response from it cannot be charged correctly and previously turned into a
    misleading provider failure after the provider had already done the work.
    """
    candidates = []
    seen = set()
    for priority, provider in enumerate(AI_GATEWAY_PROVIDER_ORDER):
        if provider in seen:
            continue
        seen.add(provider)
        config = ai_service.PROVIDERS.get(provider)
        if not config or not ai_service.get_server_api_key(provider):
            continue
        if provider_health.status(provider)["state"] != "healthy":
            continue
        model = ai_service.get_server_model(provider)
        pricing = AI_MODEL_COSTS_USD.get(model)
        if not _valid_pricing(pricing):
            continue
        candidates.append(RouteCandidate(provider, model, priority, pricing, capability_tier))
    return candidates

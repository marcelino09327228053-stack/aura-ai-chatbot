"""Authorized provider routing and temporary health state."""

from dataclasses import dataclass
import math
import os
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
        with self._lock: self._health.clear()

    def mark_healthy(self, provider: str):
        with self._lock: self._health[provider] = {"state": "healthy", "reason": None, "until": 0.0}
        client = get_client()
        if client:
            try: client.delete(f"aura:ai:provider-health:{provider}")
            except Exception: pass

    def mark_cooldown(self, provider: str, reason: str, seconds: float | None = None,
                      state: str = "cooldown"):
        duration = max(0.0, seconds if seconds is not None else AI_GATEWAY_PROVIDER_COOLDOWN_SECONDS)
        with self._lock:
            self._health[provider] = {"state": state, "reason": reason, "until": time.monotonic() + duration}
        client = get_client()
        if client:
            try:
                client.setex(f"aura:ai:provider-health:{provider}", max(1, math.ceil(duration)),
                             json.dumps({"state": state, "reason": reason}))
            except Exception: pass

    def status(self, provider: str) -> dict:
        client = get_client()
        if client:
            try:
                raw = client.get(f"aura:ai:provider-health:{provider}")
                if raw:
                    value = json.loads(raw)
                    return {**value, "cooldown_remaining": float(client.ttl(f"aura:ai:provider-health:{provider}"))}
            except Exception: pass
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


def route_candidates(capability_tier: str = "balanced") -> list[RouteCandidate]:
    candidates = []
    for priority, provider in enumerate(AI_GATEWAY_PROVIDER_ORDER):
        config = ai_service.PROVIDERS.get(provider)
        if not config or not os.getenv(config["key_env"], "").strip():
            continue
        if provider_health.status(provider)["state"] != "healthy":
            continue
        model = ai_service.get_server_model(provider)
        candidates.append(RouteCandidate(provider, model, priority, AI_MODEL_COSTS_USD.get(model), capability_tier))
    return candidates

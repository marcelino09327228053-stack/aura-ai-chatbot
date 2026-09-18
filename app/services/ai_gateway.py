"""Central managed AI Gateway with queueing, routing, retries, and metering."""

import asyncio
import math
import random
import time
import uuid

from fastapi import HTTPException

from app.core.config import (
    AI_GATEWAY_MAX_RETRIES,
    AI_GATEWAY_PROVIDER_COOLDOWN_SECONDS,
    AI_GATEWAY_RETRY_BASE_SECONDS,
    AI_GATEWAY_RETRY_JITTER_SECONDS,
    AI_GATEWAY_RETRY_MAX_SECONDS,
    AI_GATEWAY_USD_TO_ALLOWANCE_RATE,
    AI_GATEWAY_ENFORCE_SUBSCRIPTION,
    AI_GATEWAY_DEMO_DAILY_REQUEST_LIMIT,
    AI_MODEL_COSTS_USD,
)
from app.database import ai_gateway_repository, ai_usage_repository
from app.services import ai_service, subscription_service
from app.services.ai_observability import emit
from app.services.ai_provider_router import provider_health, route_candidates
from app.services.ai_traffic import get_traffic_manager


def _provider_cost(model: str, input_tokens: int, output_tokens: int) -> float | None:
    pricing = AI_MODEL_COSTS_USD.get(model)
    if not isinstance(pricing, dict):
        return None
    try:
        input_rate = float(pricing.get("input_per_million", 0))
        output_rate = float(pricing.get("output_per_million", 0))
    except (TypeError, ValueError):
        return None
    return round(input_tokens / 1_000_000 * input_rate + output_tokens / 1_000_000 * output_rate, 8)


def _allowance_charge_minor(provider_cost_usd: float) -> int:
    from app.referrals.repository import current_pricing
    markup_bps = max(0, int(current_pricing().get("ai_usage_markup_bps", 0)))
    multiplier = 1 + (markup_bps / 10_000)
    return max(0, math.ceil(provider_cost_usd * AI_GATEWAY_USD_TO_ALLOWANCE_RATE * 100 * multiplier))


def _error_status(exc: Exception) -> int | None:
    current = exc
    for _ in range(4):
        for name in ("status_code", "code"):
            value = getattr(current, name, None)
            try:
                if value is not None: return int(value)
            except (TypeError, ValueError):
                pass
        current = getattr(current, "__cause__", None)
        if current is None: break
    return None


def _safe_error_reason(exc: Exception) -> str:
    """Return a short diagnostic category without exposing provider secrets."""
    text = str(exc).lower()
    if "provider_usage_unavailable" in text:
        return "usage_unavailable"
    if "provider_cost_unconfigured" in text:
        return "cost_unconfigured"
    if "quota" in text or "insufficient_quota" in text or "resource_exhausted" in text:
        return "quota_exhausted"
    if "billing" in text or "credit" in text:
        return "billing_or_credit"
    if "model" in text and ("not found" in text or "does not exist" in text or "unsupported" in text):
        return "model_unavailable"
    if "api key" in text or "apikey" in text or "authentication" in text or "unauthorized" in text:
        return "authentication_failed"
    if "timeout" in text or "timed out" in text:
        return "timeout"
    return type(exc).__name__.lower()


def _retry_after(exc: Exception) -> float | None:
    value = getattr(exc, "retry_after", None)
    if value is not None:
        try: return max(0.0, float(value))
        except (TypeError, ValueError): pass
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None) or getattr(exc, "headers", None)
    if headers:
        value = headers.get("Retry-After") or headers.get("retry-after")
        try: return max(0.0, float(value))
        except (TypeError, ValueError): pass
    return None


def _backoff(retry_index: int) -> float:
    base = min(AI_GATEWAY_RETRY_MAX_SECONDS, AI_GATEWAY_RETRY_BASE_SECONDS * (2 ** retry_index))
    return min(AI_GATEWAY_RETRY_MAX_SECONDS, base + random.uniform(0, AI_GATEWAY_RETRY_JITTER_SECONDS))


async def _call_provider(prompt: str, provider: str, model: str):
    return await asyncio.to_thread(ai_service.generate_reply, prompt, provider, model, None)


async def generate(prompt: str, company_id: int, user_id: int | None,
                   request_id: str | None = None, capability_tier: str = "balanced") -> dict:
    request_started = time.monotonic()
    request_id = (request_id or str(uuid.uuid4())).strip()
    if not request_id or len(request_id) > 128:
        raise HTTPException(status_code=400, detail="Invalid AI request ID.")
    record, created = ai_gateway_repository.begin_request(request_id, company_id, user_id)
    if not created:
        if record["company_id"] != company_id or record.get("user_id") != user_id:
            raise HTTPException(status_code=409, detail="AI request ID is already in use.")
        if record["status"] == "success":
            emit("duplicate_replay", request_id=request_id, company_id=company_id)
            return {**record, "reply": record["response_text"], "idempotent_replay": True}
        raise HTTPException(status_code=409, detail="AI request has already been submitted.")

    subscription = None
    if AI_GATEWAY_ENFORCE_SUBSCRIPTION:
        try:
            subscription = subscription_service.prepare_gateway_access(company_id)
        except HTTPException:
            ai_gateway_repository.fail_request(request_id, "subscription_denied", 0)
            emit("subscription_denied", request_id=request_id, company_id=company_id)
            raise
    else:
        if ai_gateway_repository.count_successful_requests_today(company_id) >= AI_GATEWAY_DEMO_DAILY_REQUEST_LIMIT:
            ai_gateway_repository.fail_request(request_id, "demo_limit_exhausted", 0)
            emit("demo_limit_exhausted", request_id=request_id, company_id=company_id)
            raise HTTPException(
                status_code=429,
                detail="The daily portfolio AI demo limit has been reached. Please try again tomorrow.",
            )
        emit("demo_access", request_id=request_id, company_id=company_id)

    traffic = get_traffic_manager()
    emit("queue_enter", request_id=request_id, company_id=company_id, **traffic.snapshot())
    try:
        async with traffic.slot(company_id):
            emit("queue_exit", request_id=request_id, company_id=company_id,
                 queue_wait_ms=round((time.monotonic() - request_started) * 1000, 2), **traffic.snapshot())
            candidates = route_candidates(capability_tier)
            emit("route_candidates", request_id=request_id, company_id=company_id,
                 candidate_count=len(candidates), providers=[c.provider for c in candidates],
                 models=[c.model for c in candidates])
            if not candidates:
                ai_gateway_repository.fail_request(request_id, "providers_unavailable", 0)
                emit("all_providers_unavailable", request_id=request_id, company_id=company_id)
                raise HTTPException(status_code=503, detail="AI service is temporarily unavailable. Please try again shortly.")

            attempts = 0
            last_error = "provider_error"
            last_provider = last_model = ""
            for route_index, candidate in enumerate(candidates):
                provider, model = candidate.provider, candidate.model
                last_provider, last_model = provider, model
                if route_index:
                    emit("fallback", request_id=request_id, company_id=company_id, provider=provider, model=model)
                emit("provider_selected", request_id=request_id, company_id=company_id,
                     provider=provider, model=model, priority=candidate.priority,
                     capability_tier=candidate.capability_tier)
                for retry_index in range(AI_GATEWAY_MAX_RETRIES + 1):
                    attempts += 1
                    try:
                        answer = await _call_provider(prompt, provider, model)
                        reply = str(answer)
                        input_tokens = int(getattr(answer, "input_tokens", 0) or 0)
                        output_tokens = int(getattr(answer, "output_tokens", 0) or 0)
                        if input_tokens + output_tokens <= 0:
                            raise RuntimeError("provider_usage_unavailable")
                        cost = _provider_cost(model, input_tokens, output_tokens)
                        if cost is None:
                            raise RuntimeError("provider_cost_unconfigured")
                        charge_minor = _allowance_charge_minor(cost)
                        if subscription is not None and charge_minor > subscription["remaining_ai_credit_minor"]:
                            ai_gateway_repository.fail_request(request_id, "allowance_exhausted", attempts, provider, model)
                            emit("allowance_exhausted", request_id=request_id, company_id=company_id)
                            raise HTTPException(status_code=402, detail="Monthly AI allowance is exhausted.")
                        if subscription is None:
                            completed = ai_gateway_repository.finalize_demo_success(
                                request_id, company_id, provider, model, reply, input_tokens,
                                output_tokens, cost, attempts
                            )
                        else:
                            completed = ai_gateway_repository.finalize_metered_success(
                                request_id, company_id, provider, model, reply, input_tokens,
                                output_tokens, cost, charge_minor, attempts
                            )
                        if completed is None:
                            ai_gateway_repository.fail_request(request_id, "allowance_exhausted", attempts, provider, model)
                            emit("allowance_exhausted", request_id=request_id, company_id=company_id)
                            raise HTTPException(status_code=402, detail="Monthly AI allowance is exhausted.")
                        provider_health.mark_healthy(provider)
                        emit("request_success", request_id=request_id, company_id=company_id,
                             provider=provider, model=model, retries=attempts - 1,
                             latency_ms=round((time.monotonic() - request_started) * 1000, 2))
                        return {**completed, "reply": reply, "idempotent_replay": False}
                    except HTTPException:
                        raise
                    except Exception as exc:
                        status = _error_status(exc)
                        is_rate_limit = status == 429
                        reason = _safe_error_reason(exc)
                        last_error = "provider_rate_limited" if is_rate_limit else reason
                        emit("provider_429" if is_rate_limit else "provider_failure",
                             request_id=request_id, company_id=company_id, provider=provider,
                             model=model, retry=retry_index, status_code=status,
                             error_type=type(exc).__name__, reason=reason)
                        if is_rate_limit:
                            delay = _retry_after(exc)
                            delay = delay if delay is not None else _backoff(retry_index)
                            provider_health.mark_cooldown(provider, "rate_limited", delay, "rate_limited")
                            if route_index + 1 < len(candidates):
                                break
                        elif retry_index >= AI_GATEWAY_MAX_RETRIES:
                            provider_health.mark_cooldown(provider, "temporarily_unavailable",
                                AI_GATEWAY_PROVIDER_COOLDOWN_SECONDS, "temporarily_unavailable")
                        if retry_index < AI_GATEWAY_MAX_RETRIES:
                            delay = _retry_after(exc) if is_rate_limit else _backoff(retry_index)
                            emit("provider_retry", request_id=request_id, provider=provider,
                                 retry=retry_index + 1, delay_seconds=round(delay, 3))
                            await asyncio.sleep(delay)
                            provider_health.mark_healthy(provider)
                            continue
                        break

            ai_gateway_repository.fail_request(request_id, last_error, attempts, last_provider, last_model)
            ai_usage_repository.record_usage(company_id, last_provider, last_model,
                status="failed", request_id=request_id)
            emit("request_failed", request_id=request_id, company_id=company_id,
                 provider=last_provider, model=last_model, reason=last_error,
                 retries=max(0, attempts - 1), latency_ms=round((time.monotonic() - request_started) * 1000, 2))
            raise HTTPException(status_code=503, detail="AI service is temporarily unavailable. Please try again shortly.")
    except HTTPException as exc:
        if exc.status_code in (429, 503) and ai_gateway_repository.get_request(request_id)["status"] == "pending":
            ai_gateway_repository.fail_request(request_id, "queue_rejected", 0)
        raise


def generate_sync(prompt: str, company_id: int, user_id: int | None = None,
                  request_id: str | None = None) -> dict:
    return asyncio.run(generate(prompt, company_id, user_id, request_id))

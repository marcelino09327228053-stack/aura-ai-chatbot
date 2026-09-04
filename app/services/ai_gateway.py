"""Central server-side AI Gateway with subscription and idempotency controls."""

import asyncio
import math
import os
import uuid

from fastapi import HTTPException

from app.core.config import (
    AI_GATEWAY_MAX_RETRIES,
    AI_GATEWAY_PROVIDER_ORDER,
    AI_GATEWAY_USD_TO_ALLOWANCE_RATE,
    AI_MODEL_COSTS_USD,
)
from app.database import ai_gateway_repository, ai_usage_repository, subscription_repository
from app.services import ai_service, subscription_service


def _provider_cost(model: str, input_tokens: int, output_tokens: int) -> float | None:
    pricing = AI_MODEL_COSTS_USD.get(model)
    if not isinstance(pricing, dict):
        return None
    try:
        input_rate = float(pricing.get("input_per_million", 0))
        output_rate = float(pricing.get("output_per_million", 0))
    except (TypeError, ValueError):
        return None
    return round(
        (input_tokens / 1_000_000 * input_rate)
        + (output_tokens / 1_000_000 * output_rate),
        8,
    )


def _allowance_charge_minor(provider_cost_usd: float) -> int:
    """Convert actual provider cost to allowance-currency minor units."""
    return max(0, math.ceil(provider_cost_usd * AI_GATEWAY_USD_TO_ALLOWANCE_RATE * 100))


def _configured_provider_order() -> list[str]:
    result = []
    for provider in AI_GATEWAY_PROVIDER_ORDER:
        config = ai_service.PROVIDERS.get(provider)
        if config and os.getenv(config["key_env"], "").strip():
            result.append(provider)
    return result


async def generate(
    prompt: str,
    company_id: int,
    user_id: int | None,
    request_id: str | None = None,
) -> dict:
    request_id = (request_id or str(uuid.uuid4())).strip()
    if not request_id or len(request_id) > 128:
        raise HTTPException(status_code=400, detail="Invalid AI request ID.")

    record, created = ai_gateway_repository.begin_request(request_id, company_id, user_id)
    if not created:
        if record["company_id"] != company_id or record.get("user_id") != user_id:
            raise HTTPException(status_code=409, detail="AI request ID is already in use.")
        if record["status"] == "success":
            return {**record, "reply": record["response_text"], "idempotent_replay": True}
        raise HTTPException(status_code=409, detail="AI request has already been submitted.")

    try:
        subscription = subscription_service.prepare_gateway_access(company_id)
    except HTTPException as exc:
        ai_gateway_repository.fail_request(request_id, "subscription_denied", 0)
        raise exc

    providers = _configured_provider_order()
    if not providers:
        ai_gateway_repository.fail_request(request_id, "no_provider_configured", 0)
        raise HTTPException(status_code=503, detail="No server AI provider is configured.")

    attempts = 0
    last_error = "provider_error"
    last_provider = ""
    last_model = ""
    for provider in providers:
        model = ai_service.get_server_model(provider)
        last_provider, last_model = provider, model
        for _ in range(AI_GATEWAY_MAX_RETRIES + 1):
            attempts += 1
            try:
                answer = await asyncio.to_thread(
                    ai_service.generate_reply, prompt, provider, model, None
                )
                reply = str(answer)
                input_tokens = int(getattr(answer, "input_tokens", 0) or 0)
                output_tokens = int(getattr(answer, "output_tokens", 0) or 0)
                if input_tokens + output_tokens <= 0:
                    ai_gateway_repository.fail_request(
                        request_id, "provider_usage_unavailable", attempts, provider, model
                    )
                    raise HTTPException(
                        status_code=503,
                        detail="The provider did not return billable token usage.",
                    )
                cost = _provider_cost(model, input_tokens, output_tokens)
                if cost is None:
                    ai_gateway_repository.fail_request(
                        request_id, "provider_cost_unconfigured", attempts, provider, model
                    )
                    raise HTTPException(
                        status_code=503,
                        detail="AI cost configuration is missing for the selected model.",
                    )
                charge_minor = _allowance_charge_minor(cost)
                if charge_minor > subscription["remaining_allowance_minor"] or not subscription_repository.deduct_allowance(company_id, charge_minor):
                    ai_gateway_repository.fail_request(
                        request_id, "allowance_exhausted", attempts, provider, model
                    )
                    raise HTTPException(status_code=402, detail="Monthly AI allowance is exhausted.")
                ai_usage_repository.record_usage(
                    company_id=company_id,
                    provider=provider,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    estimated_cost=cost,
                    status="success",
                    request_id=request_id,
                    allowance_deducted_minor=charge_minor,
                )
                completed = ai_gateway_repository.complete_request(
                    request_id,
                    provider,
                    model,
                    reply,
                    input_tokens,
                    output_tokens,
                    cost,
                    charge_minor,
                    attempts,
                )
                return {**completed, "reply": reply, "idempotent_replay": False}
            except HTTPException:
                raise
            except Exception as exc:
                last_error = type(exc).__name__.lower()
        # Only providers explicitly ordered by the operator are authorized fallbacks.

    ai_gateway_repository.fail_request(
        request_id, last_error, attempts, last_provider, last_model
    )
    ai_usage_repository.record_usage(
        company_id=company_id,
        provider=last_provider,
        model=last_model,
        status="failed",
        request_id=request_id,
    )
    raise HTTPException(status_code=503, detail="AI providers are temporarily unavailable.")


def generate_sync(
    prompt: str,
    company_id: int,
    user_id: int | None = None,
    request_id: str | None = None,
) -> dict:
    """Thread-friendly adapter for existing synchronous service modules."""
    return asyncio.run(generate(prompt, company_id, user_id, request_id))

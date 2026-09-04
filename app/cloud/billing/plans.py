"""Configurable cloud billing catalog; no production prices are embedded."""

import json
import os

try:
    PLAN_PRICING = json.loads(os.getenv("SUBSCRIPTION_PRICING_JSON", "{}"))
except json.JSONDecodeError:
    PLAN_PRICING = {}

TRIAL_DAYS = 14


def get_amount(plan: str, cycle: str) -> float:
    if cycle == "trial":
        return 0.0
    pricing = PLAN_PRICING.get(plan.lower())
    if not isinstance(pricing, dict) or pricing.get(cycle) is None:
        raise RuntimeError("Subscription pricing is not configured.")
    return float(pricing[cycle])


def list_plans() -> list[dict]:
    result = []
    for plan, prices in PLAN_PRICING.items():
        result.append({
            "plan": plan,
            "monthly": prices.get("monthly"),
            "annual": prices.get("annual"),
            "trial_days": TRIAL_DAYS if plan == "pro" else 0,
        })
    return result

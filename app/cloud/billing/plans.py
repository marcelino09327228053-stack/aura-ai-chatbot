"""Cloud billing plans and pricing."""

PLAN_PRICING = {
    "free": {"monthly": 0.0, "annual": 0.0},
    "pro": {"monthly": 29.0, "annual": 290.0},
    "enterprise": {"monthly": 99.0, "annual": 990.0},
}

TRIAL_DAYS = 14


def get_amount(plan: str, cycle: str) -> float:
    if cycle == "trial":
        return 0.0
    pricing = PLAN_PRICING.get(plan.lower(), PLAN_PRICING["free"])
    return pricing.get(cycle, pricing["monthly"])


def list_plans() -> list[dict]:
    result = []
    for plan, prices in PLAN_PRICING.items():
        result.append({
            "plan": plan,
            "monthly": prices["monthly"],
            "annual": prices["annual"],
            "trial_days": TRIAL_DAYS if plan == "pro" else 0,
        })
    return result

"""Internal economic system — rewards, incentives, performance metrics."""

from __future__ import annotations

from app.civilization import repository as civ_repo

INCENTIVE_RULES = [
    {"metric": "customer_satisfaction", "threshold": 80, "reward": 50, "reason": "High CSAT"},
    {"metric": "sales_quota", "threshold": 100, "reward": 100, "reason": "Quota achieved"},
    {"metric": "training_completion", "threshold": 100, "reward": 25, "reason": "Training completed"},
    {"metric": "innovation_score", "threshold": 70, "reward": 75, "reason": "Innovation contribution"},
]


def ensure_treasury(company_id: int) -> dict:
    return civ_repo.get_or_create_account(company_id, "treasury", "treasury")


def reward_member(company_id: int, account_key: str, amount: float, reason: str,
                  reward_type: str = "incentive") -> dict:
    reward = civ_repo.grant_reward(company_id, account_key, amount, reason, reward_type)
    civ_repo.log_civ_action(company_id, "economy.reward", details=f"{account_key}:{amount}")
    return reward


def apply_incentives(company_id: int, account_key: str, metrics: dict[str, float]) -> list[dict]:
    """Grant rewards when performance metrics meet incentive thresholds."""
    granted = []
    for rule in INCENTIVE_RULES:
        value = metrics.get(rule["metric"], 0)
        civ_repo.record_performance(company_id, account_key, rule["metric"], value)
        if value >= rule["threshold"]:
            granted.append(reward_member(
                company_id, account_key, rule["reward"], rule["reason"], "incentive",
            ))
    return granted


def economy_summary(company_id: int) -> dict:
    ensure_treasury(company_id)
    accounts = civ_repo.list_accounts(company_id)
    rewards = civ_repo.list_rewards(company_id)
    performance = civ_repo.list_performance(company_id)
    total_balance = sum(a.get("balance", 0) for a in accounts)
    total_rewards = sum(r.get("amount", 0) for r in rewards)

    return {
        "accounts": accounts,
        "recent_rewards": rewards[:15],
        "performance": performance[:20],
        "incentive_rules": INCENTIVE_RULES,
        "totals": {
            "accounts": len(accounts),
            "total_balance": round(total_balance, 2),
            "rewards_issued": len(rewards),
            "rewards_value": round(total_rewards, 2),
            "metrics_recorded": len(performance),
        },
    }

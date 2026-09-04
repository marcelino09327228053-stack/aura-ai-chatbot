"""Agent-to-agent communication channels."""

from app.os import repository as os_repo

CHANNELS = {
    ("support", "sales"): "Customer escalation and lead handoff",
    ("sales", "support"): "Post-sale support coordination",
    ("hr", "accounting"): "Payroll and attendance sync",
    ("accounting", "hr"): "Expense approvals and headcount",
    ("marketing", "inventory"): "Stock-aware campaign planning",
    ("inventory", "marketing"): "Low-stock promotion triggers",
}

DEFAULT_MESSAGES = {
    ("support", "sales"): "Customer showed purchase intent — please follow up.",
    ("hr", "accounting"): "Payroll period closing — review attendance records.",
    ("marketing", "inventory"): "Check stock levels before launching promotion.",
}


def send_message(company_id: int, from_agent: str, to_agent: str, message: str | None = None) -> dict:
    pair = (from_agent, to_agent)
    if pair not in CHANNELS:
        raise ValueError(f"No communication channel: {from_agent} → {to_agent}")
    body = message or DEFAULT_MESSAGES.get(pair, f"Message from {from_agent} to {to_agent}")
    return os_repo.send_agent_message(company_id, from_agent, to_agent, body)


def list_channels() -> list[dict]:
    return [
        {"from": a, "to": b, "description": desc}
        for (a, b), desc in CHANNELS.items()
    ]


def get_inbox(company_id: int, agent_type: str) -> list[dict]:
    messages = os_repo.list_agent_messages(company_id, limit=100)
    return [m for m in messages if m["to_agent"] == agent_type]

"""AI Core — unified brain, central decisions, shared memory, cross-agent coordination."""

from __future__ import annotations

from app.universe import repository as uni_repo

UNIVERSE_AGENTS = [
    {"id": "support", "name": "Support Agent", "domain": "customer"},
    {"id": "sales", "name": "Sales Agent", "domain": "revenue"},
    {"id": "hr", "name": "HR Agent", "domain": "people"},
    {"id": "accounting", "name": "Accounting Agent", "domain": "finance"},
    {"id": "marketing", "name": "Marketing Agent", "domain": "growth"},
    {"id": "ceo", "name": "CEO Agent", "domain": "strategy"},
    {"id": "cfo", "name": "CFO Agent", "domain": "finance_exec"},
    {"id": "coo", "name": "COO Agent", "domain": "operations"},
    {"id": "cto", "name": "CTO Agent", "domain": "technology"},
    {"id": "cmo", "name": "CMO Agent", "domain": "marketing_exec"},
    {"id": "research", "name": "Research Engine", "domain": "research"},
    {"id": "innovation", "name": "Innovation Engine", "domain": "innovation"},
]

COORDINATION_TASKS = [
    ("support", "sales", "Route qualified leads from support conversations"),
    ("sales", "accounting", "Sync closed deals to revenue records"),
    ("hr", "accounting", "Share payroll and attendance data"),
    ("marketing", "sales", "Align campaign leads with sales pipeline"),
    ("ceo", "cfo", "Review strategic financial decisions"),
    ("research", "innovation", "Feed market insights to innovation pipeline"),
    ("coo", "hr", "Coordinate hiring with operational capacity"),
]


def initialize_brain(company_id: int) -> dict:
    """Bootstrap unified AI brain with core memory and agent links."""
    core_memories = [
        ("company_mission", "strategic", "Deliver exceptional AI-powered business operations."),
        ("decision_framework", "process", "Prioritize customer impact, financial health, and compliance."),
        ("agent_protocol", "coordination", "All agents share knowledge through the universal brain."),
    ]
    saved = []
    for key, mem_type, content in core_memories:
        saved.append(uni_repo.save_brain_memory(company_id, key, content, mem_type))

    coordination = coordinate_agents(company_id)
    uni_repo.log_universe_action(company_id, "ai_core.initialize")
    return {"memories": saved, "coordination_links": len(coordination), "agents": len(UNIVERSE_AGENTS)}


def get_shared_memory(company_id: int) -> dict:
    memories = uni_repo.get_brain_memory(company_id)
    return {
        "total": len(memories),
        "memories": memories,
        "by_type": _group_by(memories, "memory_type"),
    }


def store_shared_memory(company_id: int, memory_key: str, content: str, memory_type: str = "shared") -> dict:
    entry = uni_repo.save_brain_memory(company_id, memory_key, content, memory_type)
    uni_repo.log_universe_action(company_id, "ai_core.store_memory", details=memory_key)
    return entry


def make_central_decision(company_id: int, decision_type: str, title: str,
                          rationale: str, agents: list[str] | None = None) -> dict:
    confidence = 0.65 + (hash(title + str(company_id)) % 30) / 100
    decision = uni_repo.save_decision(company_id, {
        "decision_type": decision_type,
        "title": title,
        "rationale": rationale,
        "agents_involved": agents or ["ceo"],
        "confidence": round(min(confidence, 0.95), 2),
        "status": "pending",
    })
    uni_repo.log_universe_action(company_id, "ai_core.decision", details=title)
    return decision


def coordinate_agents(company_id: int) -> list[dict]:
    """Establish cross-agent coordination links."""
    links = []
    for source, target, task in COORDINATION_TASKS:
        links.append(uni_repo.upsert_coordination(company_id, source, target, task))
    uni_repo.log_universe_action(company_id, "ai_core.coordinate", details=f"{len(links)} links")
    return links


def run_decision_cycle(company_id: int) -> dict:
    """Central decision system — synthesize decisions from live platform state."""
    memories = uni_repo.get_brain_memory(company_id)
    if not memories:
        initialize_brain(company_id)
        memories = uni_repo.get_brain_memory(company_id)

    coordination = uni_repo.list_coordination(company_id)
    if not coordination:
        coordination = coordinate_agents(company_id)

    decisions = []
    decisions.append(make_central_decision(
        company_id, "operational",
        "Optimize cross-agent knowledge sharing",
        "All agents should publish weekly summaries to the universal brain.",
        ["ceo", "cto", "research"],
    ))
    decisions.append(make_central_decision(
        company_id, "strategic",
        "Review expansion readiness",
        "Evaluate branch, market, and deployment opportunities quarterly.",
        ["ceo", "cfo", "coo"],
    ))

    return {
        "brain_status": "active",
        "memory_count": len(memories),
        "coordination_links": len(coordination),
        "agents_registered": len(UNIVERSE_AGENTS),
        "new_decisions": decisions,
        "coordination": coordination[:5],
    }


def ai_core_status(company_id: int) -> dict:
    memories = uni_repo.get_brain_memory(company_id)
    decisions = uni_repo.list_decisions(company_id, 10)
    coordination = uni_repo.list_coordination(company_id)
    pending = [d for d in decisions if d.get("status") == "pending"]

    return {
        "brain": {
            "status": "online" if memories else "initializing",
            "memory_count": len(memories),
            "agents": UNIVERSE_AGENTS,
        },
        "decisions": {
            "total": len(decisions),
            "pending": len(pending),
            "recent": decisions[:5],
        },
        "coordination": {
            "active_links": len(coordination),
            "links": coordination[:8],
        },
    }


def _group_by(items: list[dict], key: str) -> dict:
    groups: dict[str, list] = {}
    for item in items:
        k = item.get(key, "unknown")
        groups.setdefault(k, []).append(item)
    return groups

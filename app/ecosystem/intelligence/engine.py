"""
Intelligence hub — connect agents, share knowledge, monitor performance, coordinate decisions.
"""

from __future__ import annotations

from app.ecosystem import repository as eco_repo


# Canonical agent registry for the ecosystem hub
ECOSYSTEM_AGENTS = [
    {"agent_id": "support", "agent_name": "Support Agent", "domain": "customer_support"},
    {"agent_id": "sales", "agent_name": "Sales Agent", "domain": "sales"},
    {"agent_id": "hr", "agent_name": "HR Agent", "domain": "human_resources"},
    {"agent_id": "accounting", "agent_name": "Accounting Agent", "domain": "finance"},
    {"agent_id": "marketing", "agent_name": "Marketing Agent", "domain": "marketing"},
    {"agent_id": "ceo", "agent_name": "CEO Agent", "domain": "strategy"},
    {"agent_id": "cfo", "agent_name": "CFO Agent", "domain": "finance_executive"},
    {"agent_id": "research", "agent_name": "Research Engine", "domain": "research"},
    {"agent_id": "innovation", "agent_name": "Innovation Engine", "domain": "innovation"},
]


def connect_all_agents(company_id: int) -> list[dict]:
    """Register / refresh all ecosystem agents for the company."""
    linked = []
    for agent in ECOSYSTEM_AGENTS:
        # Slight variance in performance for demo realism
        score = 0.7 + (hash(agent["agent_id"] + str(company_id)) % 25) / 100
        linked.append(eco_repo.upsert_agent_link(
            company_id,
            agent["agent_id"],
            agent["agent_name"],
            agent["domain"],
            round(min(score, 0.95), 2),
        ))
    eco_repo.log_ecosystem_action(company_id, "intelligence.connect_agents", details=f"{len(linked)} agents")
    return linked


def share_knowledge(company_id: int, source_agent: str, topic: str, content: str) -> dict:
    entry = eco_repo.save_knowledge(company_id, source_agent, topic, content, shared=True)
    eco_repo.create_notification(
        company_id,
        f"Knowledge shared: {topic}",
        f"From {source_agent}: {content[:120]}",
        "low",
        source_agent,
    )
    eco_repo.log_ecosystem_action(company_id, "intelligence.share_knowledge", details=topic)
    return entry


def monitor_performance(company_id: int) -> dict:
    agents = eco_repo.list_agent_links(company_id)
    if not agents:
        agents = connect_all_agents(company_id)

    avg = sum(a.get("performance_score", 0) for a in agents) / max(len(agents), 1)
    active = [a for a in agents if a.get("status") == "active"]
    underperforming = [a for a in agents if a.get("performance_score", 0) < 0.75]

    return {
        "agent_count": len(agents),
        "active_count": len(active),
        "average_performance": round(avg, 3),
        "underperforming": underperforming,
        "agents": agents,
        "health": "excellent" if avg >= 0.85 else "good" if avg >= 0.75 else "needs_attention",
    }


def coordinate_decisions(company_id: int) -> dict:
    """Coordinate cross-agent decisions from shared knowledge + agent status."""
    knowledge = eco_repo.list_knowledge(company_id, limit=10)
    performance = monitor_performance(company_id)
    research = eco_repo.list_research(company_id)[:3]
    innovations = eco_repo.list_innovations(company_id)[:3]

    decisions = []
    if innovations:
        decisions.append({
            "decision": f"Prioritize innovation: {innovations[0].get('title')}",
            "owners": ["innovation", "ceo"],
            "confidence": innovations[0].get("impact_score", 0.7),
        })
    if research:
        decisions.append({
            "decision": f"Act on research: {research[0].get('title')}",
            "owners": ["research", "ceo", "marketing"],
            "confidence": 0.75,
        })
    if performance["underperforming"]:
        names = ", ".join(a["agent_name"] for a in performance["underperforming"][:3])
        decisions.append({
            "decision": f"Review underperforming agents: {names}",
            "owners": ["ceo"],
            "confidence": 0.7,
        })
    decisions.append({
        "decision": "Publish weekly ecosystem briefing to all agents",
        "owners": ["automation", "research"],
        "confidence": 0.85,
    })

    eco_repo.log_ecosystem_action(company_id, "intelligence.coordinate")
    return {
        "decisions": decisions,
        "knowledge_items": len(knowledge),
        "agent_health": performance["health"],
        "shared_knowledge": knowledge[:5],
    }


def ecosystem_status(company_id: int) -> dict:
    """Full ecosystem status for GET /ecosystem/status."""
    eco_repo.log_ecosystem_action(company_id, "status.view")
    performance = monitor_performance(company_id)
    jobs = eco_repo.list_automation_jobs(company_id, limit=10)
    notifications = eco_repo.list_notifications(company_id, unread_only=True)
    simulations = eco_repo.list_simulations(company_id, limit=5)
    research = eco_repo.list_research(company_id)[:5]
    innovations = eco_repo.list_innovations(company_id)[:5]
    knowledge = eco_repo.list_knowledge(company_id, limit=5)

    return {
        "status": "operational",
        "agents": performance,
        "automation_jobs": {
            "recent": jobs,
            "completed": len([j for j in jobs if j.get("status") == "completed"]),
            "pending": len([j for j in jobs if j.get("status") == "pending"]),
        },
        "unread_notifications": len(notifications),
        "notifications": notifications[:10],
        "recent_simulations": len(simulations),
        "research_count": len(research),
        "innovation_count": len(innovations),
        "knowledge_count": len(knowledge),
        "modules": {
            "research": "active",
            "innovation": "active",
            "simulations": "active",
            "automation": "active",
            "intelligence": "active",
        },
    }

"""Collaboration — team, company, shared projects, shared knowledge."""

from __future__ import annotations

from app.universe import repository as uni_repo


def create_team_project(company_id: int, title: str, description: str, members: list[str]) -> dict:
    project = uni_repo.create_project(company_id, {
        "project_type": "team",
        "title": title,
        "description": description,
        "members": members,
    })
    uni_repo.log_universe_action(company_id, "collaboration.team_project", details=title)
    return project


def create_company_collaboration(company_id: int, title: str, partner_company: str,
                                 description: str = "") -> dict:
    project = uni_repo.create_project(company_id, {
        "project_type": "company",
        "title": title,
        "description": description or f"Collaboration with {partner_company}",
        "members": [partner_company],
    })
    uni_repo.log_universe_action(company_id, "collaboration.company", details=partner_company)
    return project


def share_project_knowledge(company_id: int, project_id: int, topic: str, content: str,
                            shared_with: str = "all") -> dict:
    entry = uni_repo.save_shared_knowledge(company_id, topic, content, project_id, shared_with)
    uni_repo.log_universe_action(company_id, "collaboration.share_knowledge", details=topic)
    return entry


def collaboration_summary(company_id: int) -> dict:
    team_projects = uni_repo.list_projects(company_id, "team")
    company_projects = uni_repo.list_projects(company_id, "company")
    shared = uni_repo.list_shared_knowledge(company_id, 20)

    return {
        "team_projects": team_projects,
        "company_collaborations": company_projects,
        "shared_knowledge": shared,
        "totals": {
            "team": len(team_projects),
            "company": len(company_projects),
            "knowledge_items": len(shared),
        },
    }


def ensure_default_projects(company_id: int) -> list[dict]:
    """Seed starter collaboration projects if none exist."""
    existing = uni_repo.list_projects(company_id)
    if existing:
        return existing

    defaults = [
        ("team", "Q1 Growth Initiative", "Cross-functional growth planning", ["sales", "marketing", "ceo"]),
        ("team", "Customer Success Sprint", "Improve support response and satisfaction", ["support", "sales"]),
        ("company", "Partner Network Alliance", "Shared marketplace and logistics", ["partner_network"]),
    ]
    created = []
    for ptype, title, desc, members in defaults:
        created.append(uni_repo.create_project(company_id, {
            "project_type": ptype,
            "title": title,
            "description": desc,
            "members": members,
        }))
    return created

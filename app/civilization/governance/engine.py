"""Civilization governance — constitutions, voting, policies, decision tracking."""

from __future__ import annotations

from app.civilization import repository as civ_repo

DEFAULT_ARTICLES = [
    "All members have equal voice in company-wide votes.",
    "Policies require majority approval before enforcement.",
    "AI agents operate under ratified constitution constraints.",
    "Audit trails are mandatory for all governance actions.",
    "Expansion and resource allocation require policy compliance.",
]

DEFAULT_POLICIES = [
    {
        "title": "Member Participation Policy",
        "category": "governance",
        "content": "All full-time members may propose and vote on civilization-level policies.",
    },
    {
        "title": "Research Ethics Policy",
        "category": "research",
        "content": "AI experiments must document risks, data isolation, and rollback plans.",
    },
    {
        "title": "Resource Allocation Policy",
        "category": "economy",
        "content": "Internal rewards and incentives must map to measurable performance metrics.",
    },
]

GLOBAL_PERMISSIONS = {
    "owner": ["constitution", "vote", "policy", "decision", "admin"],
    "admin": ["vote", "policy", "decision", "admin"],
    "manager": ["vote", "decision"],
    "employee": ["vote"],
    "guest": [],
}


def ensure_constitution(company_id: int) -> dict:
    existing = civ_repo.list_constitutions(company_id)
    if existing:
        return existing[0]
    return civ_repo.save_constitution(
        company_id,
        "Aura Company Constitution",
        DEFAULT_ARTICLES,
        version="1.0",
    )


def ensure_default_policies(company_id: int) -> list[dict]:
    existing = civ_repo.list_policies(company_id)
    if existing:
        return existing
    return [
        civ_repo.create_policy(company_id, p["title"], p["category"], p["content"])
        for p in DEFAULT_POLICIES
    ]


def create_policy(company_id: int, title: str, category: str, content: str, user_id: int | None = None) -> dict:
    policy = civ_repo.create_policy(company_id, title, category, content)
    decision = civ_repo.record_decision(
        company_id,
        f"Policy adopted: {title}",
        "policy",
        f"Category={category}",
    )
    civ_repo.log_civ_action(company_id, "governance.policy_create", user_id, title)
    return {"policy": policy, "decision": decision}


def open_vote(company_id: int, title: str, description: str, options: list[str],
              created_by: int | None = None) -> dict:
    if len(options) < 2:
        options = ["Approve", "Reject"]
    vote = civ_repo.create_vote(company_id, title, description, options, created_by)
    civ_repo.log_civ_action(company_id, "governance.vote_open", created_by, title)
    return vote


def cast_and_track(company_id: int, vote_id: int, option: str, user_id: int | None = None) -> dict | None:
    result = civ_repo.cast_vote(company_id, vote_id, option)
    if result:
        civ_repo.log_civ_action(company_id, "governance.vote_cast", user_id, f"{vote_id}:{option}")
    return result


def close_and_record(company_id: int, vote_id: int, user_id: int | None = None) -> dict | None:
    vote = civ_repo.close_vote(company_id, vote_id)
    if not vote:
        return None
    results = vote.get("results") or {}
    winner = max(results, key=results.get) if results else "undecided"
    decision = civ_repo.record_decision(
        company_id,
        f"Vote closed: {vote.get('title')}",
        "vote",
        f"Winner={winner}; Results={results}",
        vote_id=vote_id,
    )
    civ_repo.log_civ_action(company_id, "governance.vote_close", user_id, str(vote_id))
    return {"vote": vote, "decision": decision, "winner": winner}


def check_permission(role: str, action: str) -> bool:
    return action in GLOBAL_PERMISSIONS.get(role, [])


def governance_summary(company_id: int) -> dict:
    constitution = ensure_constitution(company_id)
    policies = ensure_default_policies(company_id)
    votes = civ_repo.list_votes(company_id)
    decisions = civ_repo.list_decisions(company_id)
    open_votes = [v for v in votes if v.get("status") == "open"]

    return {
        "constitution": constitution,
        "policies": policies,
        "votes": votes[:10],
        "open_votes": len(open_votes),
        "decisions": decisions[:10],
        "permissions": GLOBAL_PERMISSIONS,
        "totals": {
            "policies": len(policies),
            "votes": len(votes),
            "decisions": len(decisions),
            "ratified": bool(constitution.get("ratified")),
        },
    }

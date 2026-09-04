"""Governance — policies, approvals, roles, security rules."""

from __future__ import annotations

from app.universe import repository as uni_repo

UNIVERSE_ROLES = {
    "owner": {
        "label": "Platform Owner",
        "can_approve": True,
        "can_create_policy": True,
        "can_manage_expansion": True,
        "can_view_all_knowledge": True,
        "can_configure_security": True,
        "approval_limit": float("inf"),
    },
    "admin": {
        "label": "Administrator",
        "can_approve": True,
        "can_create_policy": True,
        "can_manage_expansion": True,
        "can_view_all_knowledge": True,
        "can_configure_security": True,
        "approval_limit": 500_000,
    },
    "manager": {
        "label": "Manager",
        "can_approve": False,
        "can_create_policy": False,
        "can_manage_expansion": False,
        "can_view_all_knowledge": True,
        "can_configure_security": False,
        "approval_limit": 50_000,
    },
    "employee": {
        "label": "Employee",
        "can_approve": False,
        "can_create_policy": False,
        "can_manage_expansion": False,
        "can_view_all_knowledge": False,
        "can_configure_security": False,
        "approval_limit": 10_000,
    },
    "guest": {
        "label": "Guest",
        "can_approve": False,
        "can_create_policy": False,
        "can_manage_expansion": False,
        "can_view_all_knowledge": False,
        "can_configure_security": False,
        "approval_limit": 0,
    },
}

DEFAULT_POLICIES = [
    {
        "title": "Universal Data Access Policy",
        "category": "security",
        "content": (
            "All knowledge and collaboration data is encrypted at rest. "
            "Access is scoped by role and company isolation. "
            "Cross-company sharing requires explicit approval."
        ),
    },
    {
        "title": "Expansion Approval Policy",
        "category": "expansion",
        "content": (
            "New branches require manager approval. "
            "New companies and global deployments require admin or owner approval. "
            "Market expansion plans must include risk assessment."
        ),
    },
    {
        "title": "AI Decision Governance",
        "category": "ai",
        "content": (
            "Central AI decisions above 80% confidence are auto-queued for review. "
            "All agent coordination changes are logged. "
            "Shared memory updates require audit trail."
        ),
    },
]

DEFAULT_SECURITY_RULES = [
    ("e2e_encryption", "encryption", {"algorithm": "AES-256", "scope": "all_sensitive_data"}),
    ("tenant_isolation", "access", {"mode": "strict", "cross_tenant": False}),
    ("audit_all_actions", "audit", {"retention_days": 365, "immutable": True}),
    ("role_based_access", "access", {"enforce_rbac": True, "default_role": "employee"}),
]


def ensure_default_policies(company_id: int) -> list[dict]:
    existing = uni_repo.list_policies(company_id)
    if existing:
        return existing
    created = []
    for policy in DEFAULT_POLICIES:
        created.append(uni_repo.create_policy(company_id, policy))
    return created


def ensure_security_rules(company_id: int) -> list[dict]:
    existing = uni_repo.list_security_rules(company_id)
    if existing:
        return existing
    created = []
    for name, rule_type, config in DEFAULT_SECURITY_RULES:
        created.append(uni_repo.save_security_rule(company_id, name, rule_type, config))
    return created


def get_role_permissions(role: str) -> dict:
    return UNIVERSE_ROLES.get(role, UNIVERSE_ROLES["guest"])


def submit_approval(company_id: int, approval_type: str, title: str, details: str,
                    requester_id: int | None = None) -> dict:
    approval = uni_repo.create_approval(company_id, {
        "approval_type": approval_type,
        "title": title,
        "details": details,
        "requester_id": requester_id,
    })
    uni_repo.log_universe_action(company_id, "governance.submit_approval", details=title)
    return approval


def decide_approval(company_id: int, approval_id: int, approved: bool, decided_by: int) -> dict | None:
    status = "approved" if approved else "rejected"
    result = uni_repo.decide_approval(company_id, approval_id, status, decided_by)
    if result:
        uni_repo.log_universe_action(company_id, f"governance.{status}", details=str(approval_id))
    return result


def governance_summary(company_id: int) -> dict:
    policies = ensure_default_policies(company_id)
    rules = ensure_security_rules(company_id)
    approvals = uni_repo.list_approvals(company_id)
    pending = [a for a in approvals if a.get("status") == "pending"]

    return {
        "policies": policies,
        "security_rules": rules,
        "roles": UNIVERSE_ROLES,
        "approvals": {
            "total": len(approvals),
            "pending": len(pending),
            "recent": approvals[:10],
        },
    }

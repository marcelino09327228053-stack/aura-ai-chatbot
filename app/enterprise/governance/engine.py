"""
Governance engine — approval workflows, policy management, role-based controls.
"""

from __future__ import annotations

from app.enterprise import repository as ent_repo

# ── Role permission matrix ────────────────────────────────────────────────────

ENTERPRISE_ROLES = {
    "owner": {
        "label": "Owner / CEO",
        "can_approve": True,
        "can_create_policy": True,
        "can_view_financials": True,
        "can_manage_team": True,
        "can_submit_approvals": True,
        "approval_limit": float("inf"),
    },
    "admin": {
        "label": "Administrator",
        "can_approve": True,
        "can_create_policy": True,
        "can_view_financials": True,
        "can_manage_team": True,
        "can_submit_approvals": True,
        "approval_limit": 100_000,
    },
    "manager": {
        "label": "Manager",
        "can_approve": False,
        "can_create_policy": False,
        "can_view_financials": True,
        "can_manage_team": True,
        "can_submit_approvals": True,
        "approval_limit": 25_000,
    },
    "employee": {
        "label": "Employee",
        "can_approve": False,
        "can_create_policy": False,
        "can_view_financials": False,
        "can_manage_team": False,
        "can_submit_approvals": True,
        "approval_limit": 5_000,
    },
    "guest": {
        "label": "Guest / Viewer",
        "can_approve": False,
        "can_create_policy": False,
        "can_view_financials": False,
        "can_manage_team": False,
        "can_submit_approvals": False,
        "approval_limit": 0,
    },
}

# Default company policy templates
DEFAULT_POLICIES = [
    {
        "title": "Expense Approval Policy",
        "category": "financial",
        "content": (
            "All expenses above ₱5,000 require manager approval before processing. "
            "Expenses above ₱25,000 require admin approval. "
            "Expenses above ₱100,000 require owner approval. "
            "All receipts must be submitted within 5 business days."
        ),
        "version": "1.0",
    },
    {
        "title": "Data Privacy Policy",
        "category": "compliance",
        "content": (
            "All customer data must be handled in accordance with the Data Privacy Act of 2012. "
            "Personal information shall not be shared with third parties without explicit consent. "
            "Data breaches must be reported to the Data Protection Officer within 72 hours."
        ),
        "version": "1.0",
    },
    {
        "title": "Code of Conduct",
        "category": "hr",
        "content": (
            "All employees are expected to conduct themselves professionally and ethically. "
            "Harassment, discrimination, and conflicts of interest are strictly prohibited. "
            "Violations must be reported to HR immediately."
        ),
        "version": "1.0",
    },
    {
        "title": "Remote Work Policy",
        "category": "operations",
        "content": (
            "Employees working remotely must maintain regular check-ins with their team lead. "
            "Core hours are 9 AM – 5 PM in the company's local timezone. "
            "All company data must be accessed via secured, approved devices only."
        ),
        "version": "1.0",
    },
]


def ensure_default_policies(company_id: int) -> list[dict]:
    """Seed default policies for a company if none exist."""
    existing = ent_repo.list_policies(company_id)
    if existing:
        return existing
    created = []
    for p in DEFAULT_POLICIES:
        created.append(ent_repo.create_policy(company_id, p))
    return created


def get_role_permissions(role: str) -> dict:
    return ENTERPRISE_ROLES.get(role, ENTERPRISE_ROLES["guest"])


def check_approval_permission(role: str, amount: float) -> tuple[bool, str]:
    perms = ENTERPRISE_ROLES.get(role, ENTERPRISE_ROLES["guest"])
    if not perms["can_approve"]:
        return False, f"Role '{role}' cannot approve requests"
    if amount > perms["approval_limit"]:
        return False, f"Amount ₱{amount:,.0f} exceeds {role} approval limit of ₱{perms['approval_limit']:,.0f}"
    return True, "Approved"


def submit_approval_request(company_id: int, data: dict, user_id: int, user_role: str) -> dict:
    perms = ENTERPRISE_ROLES.get(user_role, ENTERPRISE_ROLES["guest"])
    if not perms["can_submit_approvals"]:
        raise PermissionError(f"Role '{user_role}' cannot submit approval requests")
    request = ent_repo.create_approval_request(company_id, data, user_id)
    ent_repo.log_enterprise_action(
        company_id, "approval.submitted", user_id,
        "approval", request["id"],
        f"Type: {data.get('request_type')}, Amount: {data.get('amount', 0)}"
    )
    return request


def decide_on_approval(company_id: int, approval_id: int, decision: str,
                        note: str, user_id: int, user_role: str, amount: float = 0) -> dict:
    can_approve, reason = check_approval_permission(user_role, amount)
    if not can_approve:
        raise PermissionError(reason)
    if decision not in ("approved", "rejected"):
        raise ValueError("Decision must be 'approved' or 'rejected'")
    result = ent_repo.decide_approval(approval_id, company_id, decision, note)
    ent_repo.log_enterprise_action(
        company_id, f"approval.{decision}", user_id,
        "approval", approval_id, note[:100]
    )
    return result


def governance_summary(company_id: int) -> dict:
    pending = ent_repo.list_approvals(company_id, status="pending")
    policies = ent_repo.list_policies(company_id)
    recent_audit = ent_repo.list_audit_log(company_id, limit=10)

    return {
        "pending_approvals": len(pending),
        "active_policies": len(policies),
        "recent_actions": len(recent_audit),
        "approvals": pending[:5],
        "policies": policies[:5],
        "audit_log": recent_audit[:5],
        "roles": [
            {"role": k, "label": v["label"], "approval_limit": v["approval_limit"]}
            for k, v in ENTERPRISE_ROLES.items()
        ],
    }

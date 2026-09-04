"""
Contract management — templates, electronic approval, renewals, legal archive.
"""

from __future__ import annotations
from datetime import datetime, timedelta

from app.commerce import repository as commerce_repo


CONTRACT_TEMPLATES = {
    "service": {
        "title": "Service Agreement",
        "content": (
            "This Service Agreement is entered into between the Provider and the Client.\n\n"
            "1. Scope of Services\n"
            "2. Payment Terms\n"
            "3. Term and Termination\n"
            "4. Confidentiality\n"
            "5. Limitation of Liability\n"
            "6. Governing Law\n"
        ),
    },
    "sales": {
        "title": "Sales Contract",
        "content": (
            "This Sales Contract covers the sale of goods/services.\n\n"
            "1. Product/Service Description\n"
            "2. Price and Payment\n"
            "3. Delivery Terms\n"
            "4. Warranty\n"
            "5. Returns and Refunds\n"
            "6. Dispute Resolution\n"
        ),
    },
    "supplier": {
        "title": "Supplier Agreement",
        "content": (
            "This Supplier Agreement governs the supply relationship.\n\n"
            "1. Supply Obligations\n"
            "2. Pricing and Volume\n"
            "3. Quality Standards\n"
            "4. Delivery Schedule\n"
            "5. Payment Terms (Net 30)\n"
            "6. Termination\n"
        ),
    },
    "nda": {
        "title": "Non-Disclosure Agreement",
        "content": (
            "This NDA protects confidential information shared between parties.\n\n"
            "1. Definition of Confidential Information\n"
            "2. Obligations of Receiving Party\n"
            "3. Exclusions\n"
            "4. Term (2 years)\n"
            "5. Remedies\n"
        ),
    },
}


def create_from_template(
    company_id: int,
    template_type: str,
    parties: list[str],
    renewal_months: int = 12,
    custom_title: str = "",
    user_id: int | None = None,
) -> dict:
    template = CONTRACT_TEMPLATES.get(template_type)
    if not template:
        raise ValueError(f"Unknown template. Choose: {list(CONTRACT_TEMPLATES)}")

    renewal = (datetime.utcnow() + timedelta(days=30 * renewal_months)).strftime("%Y-%m-%d")
    contract = commerce_repo.create_contract(company_id, {
        "title": custom_title or template["title"],
        "template_type": template_type,
        "parties": parties,
        "content": template["content"],
        "status": "draft",
        "renewal_date": renewal,
    })
    commerce_repo.log_commerce_action(
        company_id, "contract.create", user_id, contract.get("title", "")
    )
    return contract


def electronic_approve(company_id: int, contract_id: int, user_id: int) -> dict:
    contract = commerce_repo.approve_contract(company_id, contract_id, user_id)
    if not contract:
        raise ValueError("Contract not found")
    commerce_repo.log_commerce_action(
        company_id, "contract.approve", user_id, f"id={contract_id}"
    )
    return contract


def renewal_reminders(company_id: int, days_ahead: int = 60) -> list[dict]:
    contracts = commerce_repo.list_contracts(company_id, archived=False)
    reminders = []
    today = datetime.utcnow().date()
    cutoff = today + timedelta(days=days_ahead)

    for c in contracts:
        renewal = c.get("renewal_date") or ""
        if not renewal:
            continue
        try:
            renew_date = datetime.strptime(renewal[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        if today <= renew_date <= cutoff:
            days_left = (renew_date - today).days
            reminders.append({
                **c,
                "days_until_renewal": days_left,
                "urgency": "high" if days_left <= 14 else "medium" if days_left <= 30 else "low",
            })

    return sorted(reminders, key=lambda r: r["days_until_renewal"])


def legal_archive(company_id: int, contract_id: int, user_id: int | None = None) -> dict:
    contract = commerce_repo.archive_contract(company_id, contract_id)
    if not contract:
        raise ValueError("Contract not found")
    commerce_repo.log_commerce_action(
        company_id, "contract.archive", user_id, f"id={contract_id}"
    )
    return contract


def contract_summary(company_id: int) -> dict:
    active = commerce_repo.list_contracts(company_id, archived=False)
    archived = commerce_repo.list_contracts(company_id, archived=True)
    reminders = renewal_reminders(company_id)

    return {
        "active_contracts": len(active),
        "archived_contracts": len(archived),
        "pending_approval": len([c for c in active if c.get("status") == "draft"]),
        "approved": len([c for c in active if c.get("status") == "approved"]),
        "renewals_due": len(reminders),
        "upcoming_renewals": reminders[:5],
        "templates": list(CONTRACT_TEMPLATES.keys()),
    }

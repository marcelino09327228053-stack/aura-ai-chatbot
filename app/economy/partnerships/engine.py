"""
Partnership system — suppliers, partner companies, joint projects, collaboration.
"""

from __future__ import annotations

from app.economy import repository as econ_repo
from app.modules.inventory import repository as inventory_repo


def add_supplier(company_id: int, name: str, contact: str = "", rating: float = 0, notes: str = "") -> dict:
    partner = econ_repo.save_partner(company_id, {
        "partner_type": "supplier",
        "name": name,
        "contact": contact,
        "rating": rating,
        "notes": notes,
    })
    econ_repo.log_economy_action(company_id, "partnership.supplier.add", details=name)
    return partner


def add_partner_company(company_id: int, name: str, contact: str = "", notes: str = "") -> dict:
    partner = econ_repo.save_partner(company_id, {
        "partner_type": "company",
        "name": name,
        "contact": contact,
        "notes": notes,
    })
    econ_repo.log_economy_action(company_id, "partnership.company.add", details=name)
    return partner


def create_joint_project(company_id: int, data: dict) -> dict:
    project = econ_repo.save_joint_project(company_id, data)
    econ_repo.log_economy_action(company_id, "partnership.project.create", details=data.get("title", ""))
    return project


def supplier_management_summary(company_id: int) -> dict:
    """Supplier overview with inventory linkage."""
    suppliers = econ_repo.list_partners(company_id, "supplier")
    products = inventory_repo.list_products(company_id)
    low_stock = [p for p in products if p.get("stock", 0) < 5]

    return {
        "total_suppliers": len(suppliers),
        "active_suppliers": len([s for s in suppliers if s.get("status") == "active"]),
        "top_rated": sorted(suppliers, key=lambda s: s.get("rating", 0), reverse=True)[:3],
        "low_stock_items": len(low_stock),
        "reorder_alerts": [
            {"product": p["name"], "stock": p["stock"]}
            for p in low_stock[:5]
        ],
        "recommendation": (
            "Contact suppliers for restock" if low_stock
            else "Inventory levels healthy"
        ),
    }


def collaboration_tools(company_id: int) -> dict:
    """Collaboration status across partners and projects."""
    partners = econ_repo.list_partners(company_id)
    projects = econ_repo.list_joint_projects(company_id)
    active_projects = [p for p in projects if p.get("status") in ("planning", "active")]

    return {
        "total_partners": len(partners),
        "by_type": {
            "suppliers": len([p for p in partners if p.get("partner_type") == "supplier"]),
            "companies": len([p for p in partners if p.get("partner_type") == "company"]),
        },
        "active_projects": len(active_projects),
        "projects": active_projects[:5],
        "collaboration_score": min(100, len(partners) * 10 + len(active_projects) * 15),
        "suggestions": [
            "Document partner agreements in writing",
            "Schedule quarterly partner review meetings",
            "Track joint project milestones weekly",
        ],
    }

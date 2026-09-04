"""
Innovation engine — product/service ideas, workflow improvements, technology recommendations.
"""

from __future__ import annotations

from app.ecosystem import repository as eco_repo
from app.modules.accounting import repository as accounting_repo
from app.modules.crm import repository as crm_repo
from app.modules.inventory import repository as inventory_repo
from app.modules.hr import repository as hr_repo


def suggest_products(company_id: int) -> list[dict]:
    products = inventory_repo.list_products(company_id)
    customers = crm_repo.count_customers(company_id)
    suggestions = []

    if not products:
        suggestions.append({
            "category": "product",
            "title": "Launch starter product catalogue",
            "description": "Add 5–10 core SKUs to enable sales tracking and marketplace listings.",
            "impact_score": 0.9,
            "effort_score": 0.4,
        })
    else:
        avg_price = sum(p.get("price", 0) for p in products) / len(products)
        if avg_price < 500:
            suggestions.append({
                "category": "product",
                "title": "Introduce premium product tier",
                "description": f"Average price is ₱{avg_price:.0f}. A premium line can lift margins.",
                "impact_score": 0.85,
                "effort_score": 0.55,
            })
        suggestions.append({
            "category": "product",
            "title": "Bundle complementary products",
            "description": "Create 2–3 product bundles to increase average order value.",
            "impact_score": 0.75,
            "effort_score": 0.35,
        })

    if customers > 20:
        suggestions.append({
            "category": "product",
            "title": "Customer-requested product line",
            "description": "Survey top customers for unmet needs and ship an MVP in 60 days.",
            "impact_score": 0.8,
            "effort_score": 0.6,
        })

    return [_persist(company_id, s) for s in suggestions]


def suggest_services(company_id: int) -> list[dict]:
    summary = accounting_repo.get_summary(company_id)
    income = summary.get("income", 0)
    suggestions = [
        {
            "category": "service",
            "title": "Subscription maintenance / retainer service",
            "description": "Recurring service contracts improve cash-flow predictability.",
            "impact_score": 0.88,
            "effort_score": 0.5,
        },
        {
            "category": "service",
            "title": "Consulting / advisory package",
            "description": "Monetize expertise with fixed-scope advisory offerings.",
            "impact_score": 0.7,
            "effort_score": 0.4,
        },
    ]
    if income > 100_000:
        suggestions.append({
            "category": "service",
            "title": "White-label / partner delivery service",
            "description": "Partner with complementary firms to expand capacity without hiring.",
            "impact_score": 0.78,
            "effort_score": 0.65,
        })
    return [_persist(company_id, s) for s in suggestions]


def improve_workflows(company_id: int) -> list[dict]:
    leads = crm_repo.list_leads(company_id)
    employees = hr_repo.list_employees(company_id)
    open_leads = [l for l in leads if l.get("status") in ("new", "contacted")]

    suggestions = [
        {
            "category": "workflow",
            "title": "Automate lead follow-up sequences",
            "description": f"{len(open_leads)} leads in pipeline — automate first touch within 24h.",
            "impact_score": 0.82,
            "effort_score": 0.45,
        },
        {
            "category": "workflow",
            "title": "Standardize order-to-delivery SOP",
            "description": "Document checkout → fulfillment → delivery as a repeatable workflow.",
            "impact_score": 0.7,
            "effort_score": 0.35,
        },
    ]
    if employees:
        suggestions.append({
            "category": "workflow",
            "title": "Daily standup + weekly KPI review",
            "description": "Short rituals improve alignment with low overhead.",
            "impact_score": 0.6,
            "effort_score": 0.2,
        })
    return [_persist(company_id, s) for s in suggestions]


def recommend_technologies(company_id: int) -> list[dict]:
    suggestions = [
        {
            "category": "technology",
            "title": "Enable AI Support Agent for 24/7 coverage",
            "description": "Reduce response time and free staff for complex cases.",
            "impact_score": 0.9,
            "effort_score": 0.3,
        },
        {
            "category": "technology",
            "title": "Adopt inventory sync + low-stock alerts",
            "description": "Prevent stockouts with automated monitoring.",
            "impact_score": 0.75,
            "effort_score": 0.25,
        },
        {
            "category": "technology",
            "title": "CRM segmentation for personalized campaigns",
            "description": "Use customer data to target offers and improve conversion.",
            "impact_score": 0.8,
            "effort_score": 0.4,
        },
    ]
    return [_persist(company_id, s) for s in suggestions]


def _persist(company_id: int, data: dict) -> dict:
    return eco_repo.save_innovation(company_id, data)


def run_all_innovations(company_id: int) -> dict:
    eco_repo.log_ecosystem_action(company_id, "innovation.run_all")
    result = {
        "products": suggest_products(company_id),
        "services": suggest_services(company_id),
        "workflows": improve_workflows(company_id),
        "technologies": recommend_technologies(company_id),
    }
    all_items = [i for group in result.values() for i in group]
    top = sorted(all_items, key=lambda x: x.get("impact_score", 0), reverse=True)[:3]
    eco_repo.save_knowledge(
        company_id, "innovation", "top_innovations",
        "; ".join(t.get("title", "") for t in top),
    )
    eco_repo.create_notification(
        company_id,
        "New innovation suggestions ready",
        f"{len(all_items)} ideas generated. Top: {top[0]['title'] if top else 'n/a'}",
        "medium",
        "innovation",
    )
    return {**result, "top_priorities": top, "total": len(all_items)}

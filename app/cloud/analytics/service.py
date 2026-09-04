"""Cloud analytics — AI usage, growth, revenue, response stats."""

from app.cloud.billing import repository as billing_repo
from app.database import usage_repository
from app.infrastructure.database import get_connection
from app.modules.crm import repository as crm_repo


def ai_usage(company_id: int) -> dict:
    return {
        "messages_today": usage_repository.count_messages_today(company_id),
        "usage_summary": usage_repository.get_usage_summary(company_id),
    }


def customer_growth(company_id: int) -> dict:
    customers = crm_repo.count_customers(company_id)
    leads = len(crm_repo.list_leads(company_id))
    return {
        "total_customers": customers,
        "total_leads": leads,
        "growth_rate": round((leads / max(customers, 1)) * 100, 1),
    }


def revenue_reports(company_id: int) -> dict:
    payments = billing_repo.list_payment_history(company_id)
    total = sum(p["amount"] for p in payments if p["status"] == "completed")
    billing = billing_repo.list_billing(company_id)
    return {
        "total_revenue": total,
        "billing_records": len(billing),
        "recent_payments": payments[:10],
    }


def response_statistics(company_id: int) -> dict:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT role, COUNT(*) as count
        FROM conversations WHERE company_id = ?
        GROUP BY role
        """,
        (company_id,),
    )
    by_role = {r["role"]: r["count"] for r in cursor.fetchall()}
    total = sum(by_role.values())
    return {
        "total_messages": total,
        "by_role": by_role,
        "assistant_ratio": round(by_role.get("assistant", 0) / max(total, 1) * 100, 1),
    }


def full_dashboard(company_id: int) -> dict:
    return {
        "ai_usage": ai_usage(company_id),
        "customer_growth": customer_growth(company_id),
        "revenue": revenue_reports(company_id),
        "responses": response_statistics(company_id),
    }

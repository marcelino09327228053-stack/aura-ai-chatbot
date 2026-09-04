"""Network analytics — global trends, business insights, AI performance."""

from app.database import usage_repository
from app.infrastructure.database import get_connection
from app.network import repository as net_repo


def global_trends() -> dict:
    members = net_repo.list_members()
    sync_logs = net_repo.list_sync_log(limit=200)
    by_type: dict[str, int] = {}
    for log in sync_logs:
        by_type[log["sync_type"]] = by_type.get(log["sync_type"], 0) + 1
    return {
        "network_members": len(members),
        "total_syncs": len(sync_logs),
        "sync_by_type": by_type,
        "federated_updates": len(net_repo.list_federated_updates()),
        "shared_resources": len(net_repo.list_shared_resources()),
    }


def business_insights(company_id: int | None = None) -> dict:
    cursor = get_connection().cursor()
    if company_id:
        cursor.execute("SELECT COUNT(*) FROM companies WHERE id = ?", (company_id,))
    else:
        cursor.execute("SELECT COUNT(*) FROM companies")
    companies = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM network_memberships WHERE left_at IS NULL")
    networked = cursor.fetchone()[0]

    return {
        "total_companies": companies,
        "networked_companies": networked,
        "network_adoption_rate": round(networked / max(companies, 1) * 100, 1),
    }


def ai_performance(company_id: int | None = None) -> dict:
    runs = net_repo.list_agent_runs(company_id, limit=100)
    by_mode: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for run in runs:
        by_mode[run["execution_mode"]] = by_mode.get(run["execution_mode"], 0) + 1
        by_status[run["status"]] = by_status.get(run["status"], 0) + 1

    messages = usage_repository.count_messages_today(company_id) if company_id else 0
    return {
        "agent_runs": len(runs),
        "by_execution_mode": by_mode,
        "by_status": by_status,
        "messages_today": messages,
    }


def full_analytics(company_id: int | None = None) -> dict:
    return {
        "global_trends": global_trends(),
        "business_insights": business_insights(company_id),
        "ai_performance": ai_performance(company_id),
    }

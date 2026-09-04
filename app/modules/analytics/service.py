"""Analytics KPIs, charts, and dashboard widgets."""

from app.database import usage_repository
from app.modules.accounting import repository as accounting_repo
from app.modules.crm import repository as crm_repo
from app.modules.hr import repository as hr_repo
from app.modules.inventory import repository as inventory_repo


def get_kpis(company_id: int) -> dict:
    summary = accounting_repo.get_summary(company_id)
    return {
        "revenue": summary["income"],
        "expenses": summary["expenses"],
        "profit": summary["profit"],
        "customers": crm_repo.count_customers(company_id),
        "employees": hr_repo.count_employees(company_id),
        "inventory_units": inventory_repo.total_stock_units(company_id),
        "messages_today": usage_repository.count_messages_today(company_id),
    }


def get_charts(company_id: int) -> dict:
    """Chart-ready series for simple frontend rendering."""
    summary = accounting_repo.get_summary(company_id)
    daily = accounting_repo.get_daily_report(company_id)
    return {
        "revenue_vs_expenses": {
            "labels": ["Income", "Expenses", "Profit"],
            "values": [summary["income"], summary["expenses"], summary["profit"]],
        },
        "daily_breakdown": {
            "labels": ["Today Income", "Today Expenses", "Today Profit"],
            "values": [daily["income"], daily["expenses"], daily["profit"]],
        },
    }


def get_growth_metrics(company_id: int) -> dict:
    customers = crm_repo.count_customers(company_id)
    employees = hr_repo.count_employees(company_id)
    products = len(inventory_repo.list_products(company_id))
    return {
        "customer_count": customers,
        "employee_count": employees,
        "product_count": products,
        "messages_today": usage_repository.count_messages_today(company_id),
    }


def get_customer_statistics(company_id: int) -> dict:
    customers = crm_repo.list_customers(company_id)
    leads = crm_repo.list_leads(company_id)
    return {
        "total_customers": len(customers),
        "total_leads": len(leads),
        "leads_by_status": _count_by_field(leads, "status"),
    }


def get_dashboard_widgets(company_id: int) -> dict:
    kpis = get_kpis(company_id)
    return {
        "revenue": {"label": "Revenue", "value": kpis["revenue"]},
        "expenses": {"label": "Expenses", "value": kpis["expenses"]},
        "customers": {"label": "Customers", "value": kpis["customers"]},
        "employees": {"label": "Employees", "value": kpis["employees"]},
        "inventory": {"label": "Inventory Units", "value": kpis["inventory_units"]},
    }


def _count_by_field(rows: list[dict], field: str) -> dict:
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get(field, "unknown"))
        counts[key] = counts.get(key, 0) + 1
    return counts

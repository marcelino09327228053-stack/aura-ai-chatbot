"""
Automation engine — reporting, task delegation, workflow optimization, notifications.
"""

from __future__ import annotations

from app.ecosystem import repository as eco_repo
from app.modules.accounting import repository as accounting_repo
from app.modules.crm import repository as crm_repo


def automatic_reporting(company_id: int, user_id: int | None = None) -> dict:
    """Generate and store an automatic business report."""
    job = eco_repo.create_automation_job(company_id, "reporting", "Automatic Business Report", {})
    summary = accounting_repo.get_summary(company_id)
    customers = crm_repo.count_customers(company_id)
    leads = crm_repo.list_leads(company_id)

    report_text = (
        f"Income: ₱{summary.get('income', 0):,.2f} | "
        f"Expenses: ₱{summary.get('expenses', 0):,.2f} | "
        f"Customers: {customers} | Leads: {len(leads)}"
    )
    eco_repo.complete_automation_job(job["id"], company_id, report_text)
    eco_repo.create_notification(
        company_id, "Automatic report ready", report_text, "medium", "automation"
    )
    eco_repo.log_ecosystem_action(company_id, "automation.reporting", user_id)
    eco_repo.save_knowledge(company_id, "automation", "daily_report", report_text)
    return {**job, "status": "completed", "result": report_text}


def task_delegation(company_id: int, user_id: int | None = None) -> dict:
    """Delegate open tasks to the best-fit agent domains."""
    job = eco_repo.create_automation_job(company_id, "delegation", "Task Delegation", {})
    leads = crm_repo.list_leads(company_id)
    open_leads = [l for l in leads if l.get("status") in ("new", "contacted")]
    summary = accounting_repo.get_summary(company_id)
    profit = summary.get("income", 0) - summary.get("expenses", 0)

    assignments = []
    if open_leads:
        assignments.append({
            "task": f"Follow up {len(open_leads)} leads",
            "assigned_to": "sales_agent",
            "priority": "high",
        })
    if profit < 0:
        assignments.append({
            "task": "Cost audit and expense reduction",
            "assigned_to": "accounting_agent",
            "priority": "critical",
        })
    assignments.append({
        "task": "Weekly customer satisfaction check",
        "assigned_to": "support_agent",
        "priority": "medium",
    })

    result = f"Delegated {len(assignments)} tasks: " + "; ".join(
        f"{a['task']} → {a['assigned_to']}" for a in assignments
    )
    eco_repo.complete_automation_job(job["id"], company_id, result)
    for a in assignments:
        eco_repo.create_notification(
            company_id,
            f"Task delegated to {a['assigned_to']}",
            a["task"],
            a["priority"] if a["priority"] != "critical" else "high",
            "automation",
        )
    eco_repo.log_ecosystem_action(company_id, "automation.delegation", user_id)
    return {**job, "status": "completed", "assignments": assignments, "result": result}


def optimize_workflows(company_id: int, user_id: int | None = None) -> dict:
    job = eco_repo.create_automation_job(company_id, "workflow", "Workflow Optimization", {})
    optimizations = [
        "Batch similar admin tasks into two daily windows",
        "Route FAQ-style questions to Support Agent first",
        "Auto-create invoices when orders are confirmed",
        "Trigger restock alerts when stock < 5",
    ]
    result = " | ".join(optimizations)
    eco_repo.complete_automation_job(job["id"], company_id, result)
    eco_repo.create_notification(
        company_id, "Workflow optimizations available", result[:200], "low", "automation"
    )
    eco_repo.log_ecosystem_action(company_id, "automation.workflow", user_id)
    return {**job, "status": "completed", "optimizations": optimizations, "result": result}


def smart_notifications(company_id: int) -> list[dict]:
    """Generate smart alerts based on live business signals."""
    summary = accounting_repo.get_summary(company_id)
    leads = crm_repo.list_leads(company_id)
    income = summary.get("income", 0)
    expenses = summary.get("expenses", 0)
    created = []

    if expenses > income and income > 0:
        created.append(eco_repo.create_notification(
            company_id, "Cash flow warning",
            "Expenses exceed income this period.", "high", "intelligence"
        ))
    open_leads = [l for l in leads if l.get("status") == "new"]
    if len(open_leads) >= 5:
        created.append(eco_repo.create_notification(
            company_id, "Lead backlog",
            f"{len(open_leads)} new leads need contact.", "medium", "automation"
        ))
    if not created:
        created.append(eco_repo.create_notification(
            company_id, "Ecosystem healthy",
            "No critical alerts. Continue monitoring.", "low", "system"
        ))
    return created


def run_automation_suite(company_id: int, user_id: int | None = None) -> dict:
    eco_repo.log_ecosystem_action(company_id, "automation.suite", user_id)
    return {
        "reporting": automatic_reporting(company_id, user_id),
        "delegation": task_delegation(company_id, user_id),
        "workflows": optimize_workflows(company_id, user_id),
        "notifications": smart_notifications(company_id),
    }

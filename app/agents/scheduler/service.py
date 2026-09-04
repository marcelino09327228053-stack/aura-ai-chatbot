"""Scheduler — daily/weekly reports and reminders."""

from datetime import datetime, timezone

from app.agents import repository as agent_repo
from app.modules.reports import service as reports_service


def run_daily_report(company_id: int) -> dict:
    report = reports_service.daily_summary(company_id)
    agent_repo.create_reminder(
        company_id,
        title="Daily Business Report",
        message=f"Income: {report['accounting']['income']}, Expenses: {report['accounting']['expenses']}",
        remind_at=datetime.now(timezone.utc).isoformat(),
    )
    return report


def run_weekly_report(company_id: int) -> dict:
    report = reports_service.monthly_summary(company_id)
    agent_repo.create_reminder(
        company_id,
        title="Weekly Business Summary",
        message=f"Profit: {report['accounting']['profit']}, Customers: {report['customers']}",
        remind_at=datetime.now(timezone.utc).isoformat(),
    )
    return report


def process_due_reminders(company_id: int) -> list[dict]:
    reminders = agent_repo.list_reminders(company_id)
    due = [r for r in reminders if r["status"] == "pending"]
    return due


def setup_default_schedules(company_id: int) -> None:
    existing = agent_repo.list_scheduler_tasks(company_id)
    if existing:
        return
    agent_repo.create_scheduler_task(company_id, "daily_report", "0 8 * * *")
    agent_repo.create_scheduler_task(company_id, "weekly_report", "0 8 * * 1")

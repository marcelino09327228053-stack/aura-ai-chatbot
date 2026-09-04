"""Automation system — daily tasks, weekly reports, notifications."""

from app.agents.scheduler import service as agent_scheduler
from app.os import repository as os_repo
from app.os.workflows import engine as workflow_engine

DEFAULT_TASKS = {
    "daily_report": "0 8 * * *",
    "weekly_report": "0 8 * * 1",
    "daily_accounting": "0 9 * * *",
    "inventory_check": "0 10 * * *",
}


def setup_defaults(company_id: int) -> list[dict]:
    tasks = []
    for key, schedule in DEFAULT_TASKS.items():
        tasks.append(os_repo.ensure_automation_task(company_id, key, schedule))
    return tasks


def run_task(company_id: int, task_key: str) -> dict:
    os_repo.touch_automation_task(company_id, task_key)

    if task_key == "daily_report":
        result = agent_scheduler.run_daily_report(company_id)
        os_repo.add_notification(company_id, "Daily Report", "Daily business report generated.")
        return {"task": task_key, "result": result}

    if task_key == "weekly_report":
        result = agent_scheduler.run_weekly_report(company_id)
        os_repo.add_notification(company_id, "Weekly Report", "Weekly business summary generated.")
        return {"task": task_key, "result": result}

    if task_key == "daily_accounting":
        wf = workflow_engine.start_workflow(company_id, "daily_accounting")
        workflow_engine.run_all_steps(company_id, wf["id"])
        return {"task": task_key, "workflow_id": wf["id"]}

    if task_key == "inventory_check":
        wf = workflow_engine.start_workflow(company_id, "inventory_restocking")
        workflow_engine.run_all_steps(company_id, wf["id"])
        return {"task": task_key, "workflow_id": wf["id"]}

    return {"task": task_key, "status": "unknown"}


def list_tasks(company_id: int) -> list[dict]:
    setup_defaults(company_id)
    return os_repo.list_automation_tasks(company_id)

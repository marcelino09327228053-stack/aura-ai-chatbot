"""Workflow engine — predefined business flows."""

from app.os import repository as os_repo
from app.os.communication import bus as comm_bus

WORKFLOW_DEFINITIONS = {
    "customer_order": {
        "name": "Customer Order Flow",
        "steps": [
            {"agent": "sales", "action": "capture_lead"},
            {"agent": "inventory", "action": "check_stock"},
            {"agent": "accounting", "action": "create_invoice"},
            {"agent": "support", "action": "confirm_order"},
        ],
    },
    "employee_onboarding": {
        "name": "Employee Onboarding",
        "steps": [
            {"agent": "hr", "action": "create_employee_record"},
            {"agent": "hr", "action": "assign_policies"},
            {"agent": "accounting", "action": "setup_payroll"},
            {"agent": "support", "action": "welcome_message"},
        ],
    },
    "daily_accounting": {
        "name": "Daily Accounting",
        "steps": [
            {"agent": "accounting", "action": "collect_transactions"},
            {"agent": "accounting", "action": "generate_summary"},
            {"agent": "hr", "action": "sync_attendance"},
        ],
    },
    "inventory_restocking": {
        "name": "Inventory Restocking",
        "steps": [
            {"agent": "inventory", "action": "check_low_stock"},
            {"agent": "marketing", "action": "pause_promotions"},
            {"agent": "accounting", "action": "approve_purchase"},
            {"agent": "inventory", "action": "update_stock"},
        ],
    },
}


def list_workflow_templates() -> list[dict]:
    return [
        {"key": key, "name": defn["name"], "steps": len(defn["steps"])}
        for key, defn in WORKFLOW_DEFINITIONS.items()
    ]


def start_workflow(company_id: int, workflow_key: str, payload: dict | None = None) -> dict:
    if workflow_key not in WORKFLOW_DEFINITIONS:
        raise ValueError(f"Unknown workflow: {workflow_key}")
    defn = WORKFLOW_DEFINITIONS[workflow_key]
    wf = os_repo.create_workflow(company_id, workflow_key, defn["name"], payload)
    return advance_workflow(company_id, wf["id"])


def advance_workflow(company_id: int, workflow_id: int) -> dict:
    wf = os_repo.get_workflow(company_id, workflow_id)
    if not wf or wf["status"] != "running":
        return wf

    defn = WORKFLOW_DEFINITIONS.get(wf["workflow_key"])
    if not defn:
        os_repo.update_workflow(company_id, workflow_id, status="failed")
        return os_repo.get_workflow(company_id, workflow_id)

    steps = defn["steps"]
    step_idx = wf["current_step"]

    if step_idx >= len(steps):
        os_repo.update_workflow(company_id, workflow_id, status="completed")
        os_repo.add_notification(company_id, f"Workflow complete: {defn['name']}", "All steps finished.")
        return os_repo.get_workflow(company_id, workflow_id)

    step = steps[step_idx]
    agent = step["agent"]
    action = step["action"]

    if agent == "inventory":
        agent = "marketing"

    job = os_repo.create_job(company_id, f"workflow:{action}", assigned_agent=agent, payload={"step": step})
    os_repo.update_job_status(company_id, job["id"], "completed", result=f"Step {step_idx + 1}: {action}")

    if step_idx > 0:
        prev_agent = steps[step_idx - 1]["agent"]
        if prev_agent == "inventory":
            prev_agent = "marketing"
        try:
            comm_bus.send_message(company_id, prev_agent, agent, f"Workflow step: {action}")
        except ValueError:
            pass

    os_repo.update_workflow(
        company_id, workflow_id,
        current_step=step_idx + 1,
        payload={**wf["payload"], f"step_{step_idx}": action},
    )

    if step_idx + 1 >= len(steps):
        os_repo.update_workflow(company_id, workflow_id, status="completed")
        os_repo.add_notification(company_id, f"Workflow complete: {defn['name']}", "All steps finished.")

    return os_repo.get_workflow(company_id, workflow_id)


def run_all_steps(company_id: int, workflow_id: int) -> dict:
    wf = os_repo.get_workflow(company_id, workflow_id)
    if not wf:
        raise ValueError("Workflow not found.")
    defn = WORKFLOW_DEFINITIONS.get(wf["workflow_key"], {})
    for _ in range(len(defn.get("steps", [])) + 1):
        wf = advance_workflow(company_id, workflow_id)
        if wf["status"] in ("completed", "failed"):
            break
    return wf

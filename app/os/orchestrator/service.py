"""AI Orchestrator — route tasks, assign agents, track status."""

from app.agents import repository as agent_repo
from app.os import repository as os_repo

TASK_ROUTES = {
    "support": ("support", ["help", "question", "issue", "problem", "refund", "complaint"]),
    "sales": ("sales", ["buy", "price", "order", "quote", "product", "purchase"]),
    "hr": ("hr", ["employee", "leave", "payroll", "attendance", "policy", "hire"]),
    "accounting": ("accounting", ["invoice", "expense", "profit", "revenue", "budget", "tax"]),
    "marketing": ("marketing", ["campaign", "post", "promotion", "social", "brand", "ad"]),
}


def detect_agent(text: str) -> str:
    text_lower = text.lower()
    best_agent = "support"
    best_score = 0
    for agent_type, (_, keywords) in TASK_ROUTES.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > best_score:
            best_score = score
            best_agent = agent_type
    return best_agent


def create_and_assign_job(company_id: int, task_type: str, text: str, payload: dict | None = None) -> dict:
    agent_type = detect_agent(text) if task_type == "auto" else task_type
    job = os_repo.create_job(company_id, task_type, assigned_agent=agent_type, payload=payload or {"text": text})
    os_repo.update_job_status(company_id, job["id"], "assigned", assigned_agent=agent_type)
    return os_repo.get_job(company_id, job["id"])


def list_agent_status(company_id: int) -> list[dict]:
    agents = agent_repo.list_agents(company_id)
    pending = os_repo.list_jobs(company_id, status="pending")
    assigned = os_repo.list_jobs(company_id, status="assigned")
    running = os_repo.list_jobs(company_id, status="running")
    for agent in agents:
        agent["pending_jobs"] = sum(1 for j in pending if j.get("assigned_agent") == agent["type"])
        agent["active_jobs"] = sum(
            1 for j in assigned + running if j.get("assigned_agent") == agent["type"]
        )
    return agents


def complete_job(company_id: int, job_id: int, result: str, success: bool = True) -> dict | None:
    status = "completed" if success else "failed"
    return os_repo.update_job_status(company_id, job_id, status, result=result)

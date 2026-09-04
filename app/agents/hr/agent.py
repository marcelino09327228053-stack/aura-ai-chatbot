"""HR Agent — employee questions, attendance, payroll."""

from app.agents.context_engine import resolve_with_priority
from app.modules.hr import repository as hr_repo

SYSTEM_PROMPT = """
You are the MB Future Tech AI Chatbot HR Agent. Answer employee policy and HR questions professionally.
Use attendance and payroll summaries when provided. Do not share confidential data beyond summaries.
"""


async def run(
    company_id: int,
    user_id: str,
    text: str,
    company_profile: str,
    language: str,
) -> tuple[str, str]:
    employees = hr_repo.list_employees(company_id)
    attendance = hr_repo.list_attendance(company_id)[:5]
    payroll = hr_repo.list_payroll(company_id)[:5]

    hr_context = f"""
HR Summary:
- Employees: {len(employees)}
- Recent attendance records: {len(attendance)}
- Recent payroll entries: {len(payroll)}
"""
    enriched = company_profile + hr_context

    return resolve_with_priority(
        company_id, user_id, text, enriched, language, SYSTEM_PROMPT
    )

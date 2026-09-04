"""Accounting Agent — income, expenses, profit."""

from app.agents.context_engine import resolve_with_priority
from app.modules.accounting import repository as accounting_repo

SYSTEM_PROMPT = """
You are the MB Future Tech AI Chatbot Accounting Agent. Provide clear financial summaries and expense analysis.
Use the provided figures; do not invent numbers.
"""


async def run(
    company_id: int,
    user_id: str,
    text: str,
    company_profile: str,
    language: str,
) -> tuple[str, str]:
    summary = accounting_repo.get_summary(company_id)
    daily = accounting_repo.get_daily_report(company_id)
    finance_ctx = f"""
Financial Summary:
- Total income: {summary['income']}
- Total expenses: {summary['expenses']}
- Profit: {summary['profit']}
Today's income: {daily['income']}, expenses: {daily['expenses']}, profit: {daily['profit']}
"""
    enriched = company_profile + finance_ctx
    return resolve_with_priority(
        company_id, user_id, text, enriched, language, SYSTEM_PROMPT
    )

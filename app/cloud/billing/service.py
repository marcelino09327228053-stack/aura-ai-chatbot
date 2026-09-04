"""Billing business logic."""

from app.cloud.billing import repository as billing_repo
from app.cloud.billing.plans import get_amount, list_plans
from app.database import subscription_repository
from app.infrastructure.audit import service as audit_service


def subscribe(company_id: int, plan: str, cycle: str, user_id: int) -> dict:
    if cycle not in ("monthly", "annual", "trial"):
        raise ValueError("Invalid billing cycle.")
    if cycle == "trial":
        trial = billing_repo.start_trial(company_id)
        subscription_repository.update_subscription_plan(company_id, "pro")
        audit_service.record(f"billing.trial:{plan}", company_id, user_id)
        return {"trial": trial, "plan": "pro", "cycle": "trial"}

    amount = get_amount(plan, cycle)
    record = billing_repo.create_billing_record(company_id, plan, cycle, status="active")
    payment = billing_repo.record_payment(company_id, record["id"], amount)
    subscription_repository.update_subscription_plan(company_id, plan)
    audit_service.record(f"billing.subscribe:{plan}:{cycle}", company_id, user_id)
    return {"billing": record, "payment": payment}


def get_billing_summary(company_id: int) -> dict:
    sub = subscription_repository.get_subscription_by_company(company_id)
    return {
        "subscription": sub,
        "plans": list_plans(),
        "billing_history": billing_repo.list_billing(company_id),
        "payment_history": billing_repo.list_payment_history(company_id),
        "trial": billing_repo.get_trial(company_id),
    }

"""Accounting API routes."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.deps import require_auth
from app.modules.accounting import repository as repo

router = APIRouter(prefix="/accounting", tags=["accounting"])


class TransactionCreate(BaseModel):
    type: str
    amount: float
    description: str = ""


@router.get("/transactions")
def get_transactions(type: str | None = None, ctx=Depends(require_auth)):
    return repo.list_transactions(ctx.company_id, type)


@router.post("/transactions", status_code=201)
def post_transaction(body: TransactionCreate, ctx=Depends(require_auth)):
    return repo.create_transaction(ctx.company_id, body.type, body.amount, body.description)


@router.get("/summary")
def get_summary(ctx=Depends(require_auth)):
    return repo.get_summary(ctx.company_id)


@router.get("/daily")
def get_daily(ctx=Depends(require_auth)):
    return repo.get_daily_report(ctx.company_id)

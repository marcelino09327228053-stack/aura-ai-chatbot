"""CRM API routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.deps import require_auth
from app.modules.crm import repository as repo

router = APIRouter(prefix="/crm", tags=["crm"])


class CustomerCreate(BaseModel):
    name: str
    phone: str = ""
    email: str = ""


class LeadCreate(BaseModel):
    name: str
    status: str = "new"
    source: str = ""
    customer_id: int | None = None


class NoteCreate(BaseModel):
    body: str
    customer_id: int | None = None
    lead_id: int | None = None


class ContactHistoryCreate(BaseModel):
    customer_id: int
    channel: str = "other"
    summary: str


@router.get("/customers")
def get_customers(ctx=Depends(require_auth)):
    return repo.list_customers(ctx.company_id)


@router.post("/customers", status_code=201)
def post_customer(body: CustomerCreate, ctx=Depends(require_auth)):
    return repo.create_customer(ctx.company_id, body.name, body.phone, body.email)


@router.put("/customers/{customer_id}")
def put_customer(customer_id: int, body: CustomerCreate, ctx=Depends(require_auth)):
    row = repo.update_customer(ctx.company_id, customer_id, name=body.name, phone=body.phone, email=body.email)
    if not row:
        raise HTTPException(status_code=404, detail="Customer not found.")
    return row


@router.delete("/customers/{customer_id}")
def delete_customer(customer_id: int, ctx=Depends(require_auth)):
    if not repo.delete_customer(ctx.company_id, customer_id):
        raise HTTPException(status_code=404, detail="Customer not found.")
    return {"ok": True}


@router.get("/leads")
def get_leads(ctx=Depends(require_auth)):
    return repo.list_leads(ctx.company_id)


@router.post("/leads", status_code=201)
def post_lead(body: LeadCreate, ctx=Depends(require_auth)):
    return repo.create_lead(ctx.company_id, body.name, body.status, body.source, body.customer_id)


@router.get("/notes")
def get_notes(customer_id: int | None = None, ctx=Depends(require_auth)):
    return repo.list_notes(ctx.company_id, customer_id)


@router.post("/notes", status_code=201)
def post_note(body: NoteCreate, ctx=Depends(require_auth)):
    return repo.create_note(ctx.company_id, body.body, body.customer_id, body.lead_id)


@router.get("/contact-history")
def get_contact_history(customer_id: int | None = None, ctx=Depends(require_auth)):
    return repo.list_contact_history(ctx.company_id, customer_id)


@router.post("/contact-history", status_code=201)
def post_contact_history(body: ContactHistoryCreate, ctx=Depends(require_auth)):
    return repo.add_contact_history(ctx.company_id, body.customer_id, body.channel, body.summary)

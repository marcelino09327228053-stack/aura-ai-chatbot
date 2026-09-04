"""HR API routes."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.deps import require_auth
from app.modules.hr import repository as repo

router = APIRouter(prefix="/hr", tags=["hr"])


class EmployeeCreate(BaseModel):
    name: str
    role: str = "staff"
    salary: float = 0


class AttendanceCreate(BaseModel):
    employee_id: int
    work_date: str
    status: str = "present"


class PayrollCreate(BaseModel):
    employee_id: int
    period: str
    amount: float
    status: str = "pending"


@router.get("/employees")
def get_employees(ctx=Depends(require_auth)):
    return repo.list_employees(ctx.company_id)


@router.post("/employees", status_code=201)
def post_employee(body: EmployeeCreate, ctx=Depends(require_auth)):
    return repo.create_employee(ctx.company_id, body.name, body.role, body.salary)


@router.get("/attendance")
def get_attendance(employee_id: int | None = None, ctx=Depends(require_auth)):
    return repo.list_attendance(ctx.company_id, employee_id)


@router.post("/attendance", status_code=201)
def post_attendance(body: AttendanceCreate, ctx=Depends(require_auth)):
    return repo.record_attendance(ctx.company_id, body.employee_id, body.work_date, body.status)


@router.get("/payroll")
def get_payroll(ctx=Depends(require_auth)):
    return repo.list_payroll(ctx.company_id)


@router.post("/payroll", status_code=201)
def post_payroll(body: PayrollCreate, ctx=Depends(require_auth)):
    return repo.create_payroll(ctx.company_id, body.employee_id, body.period, body.amount, body.status)

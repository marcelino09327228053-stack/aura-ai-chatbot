"""Reports API routes."""

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.core.deps import require_auth
from app.modules.reports import service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/daily")
def daily_report(ctx=Depends(require_auth)):
    return service.daily_summary(ctx.company_id)


@router.get("/monthly")
def monthly_report(ctx=Depends(require_auth)):
    return service.monthly_summary(ctx.company_id)


@router.get("/export/excel")
def export_excel(ctx=Depends(require_auth)):
    content = service.export_excel_csv(ctx.company_id)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=aura-report.csv"},
    )


@router.get("/export/pdf")
def export_pdf(ctx=Depends(require_auth)):
    content = service.export_pdf_bytes(ctx.company_id)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=aura-report.pdf"},
    )

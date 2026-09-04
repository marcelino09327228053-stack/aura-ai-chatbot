"""Aura Global Intelligence API routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.deps import require_auth
from . import repository as global_repo
from .currencies import service as currency_service
from .insights import document_intelligence as doc_intel
from .insights import service as insights_service
from .localization import engine as loc_engine
from .regulations import service as reg_service
from .translation import engine as trans_engine

router = APIRouter(prefix="/global", tags=["global"])


# ── Request models ────────────────────────────────────────────────────────────

class LanguageSettingsRequest(BaseModel):
    primary_language: str = "en"
    supported_languages: list[str] = ["en"]
    timezone: str = "UTC"
    date_format: str = "YYYY-MM-DD"
    currency_code: str = "PHP"


class TranslateRequest(BaseModel):
    text: str
    target_lang: str
    source_lang: str = "en"


class TranslateBatchRequest(BaseModel):
    texts: list[str]
    target_lang: str
    source_lang: str = "en"


class CurrencyConvertRequest(BaseModel):
    amount: float
    from_currency: str
    to_currency: str


class InvoiceRequest(BaseModel):
    items: list[dict]
    currency: str = "PHP"
    tax_rate: float = 0.0


class AnalyzeDocumentRequest(BaseModel):
    document_type: str
    document_name: str = ""
    content: str


class AssistantRequest(BaseModel):
    assistant_type: str
    question: str


class ComplianceRequest(BaseModel):
    country_code: str
    has_employees: bool = False
    processes_personal_data: bool = True
    annual_revenue: float = 0.0


# ── Language & Translation ────────────────────────────────────────────────────

@router.get("/languages")
def list_languages():
    """List all supported languages with metadata."""
    return trans_engine.list_supported_languages()


@router.get("/settings")
def get_settings(ctx=Depends(require_auth)):
    return global_repo.get_language_settings(ctx.company_id)


@router.put("/settings")
def update_settings(body: LanguageSettingsRequest, ctx=Depends(require_auth)):
    global_repo.log_global_action(ctx.company_id, "settings.update")
    return global_repo.save_language_settings(ctx.company_id, body.model_dump())


@router.post("/translate")
def translate(body: TranslateRequest, ctx=Depends(require_auth)):
    if body.target_lang not in trans_engine.SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language: {body.target_lang}. Supported: {list(trans_engine.SUPPORTED_LANGUAGES)}",
        )
    translated = trans_engine.translate_text(
        body.text, body.target_lang, body.source_lang, ctx.company_id
    )
    result = global_repo.save_translation(
        ctx.company_id, body.text, body.source_lang, body.target_lang, translated
    )
    return result


@router.post("/translate/batch")
def translate_batch(body: TranslateBatchRequest, ctx=Depends(require_auth)):
    if body.target_lang not in trans_engine.SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {body.target_lang}")
    return trans_engine.translate_batch(
        body.texts, body.target_lang, body.source_lang, ctx.company_id
    )


@router.post("/detect-language")
def detect_language(body: TranslateRequest):
    return {"detected_language": trans_engine.detect_language(body.text)}


@router.get("/translations")
def list_translations(ctx=Depends(require_auth)):
    return global_repo.list_translations(ctx.company_id)


# ── Localization ──────────────────────────────────────────────────────────────

@router.get("/timezones")
def list_timezones():
    return loc_engine.list_timezones()


@router.get("/timezones/{tz_name:path}")
def get_timezone_time(tz_name: str):
    try:
        return loc_engine.get_current_time_in_zone(tz_name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/currencies")
def list_currencies():
    return loc_engine.list_currencies()


@router.post("/currencies/convert")
def convert_currency(body: CurrencyConvertRequest, ctx=Depends(require_auth)):
    try:
        result = currency_service.convert(body.amount, body.from_currency, body.to_currency)
        global_repo.log_global_action(
            ctx.company_id, "currency.convert",
            f"{body.amount} {body.from_currency} → {body.to_currency}",
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/currencies/multi-price")
def multi_currency_price(body: CurrencyConvertRequest, ctx=Depends(require_auth)):
    return currency_service.multi_currency_price(body.amount, body.from_currency)


@router.post("/currencies/invoice")
def build_invoice(body: InvoiceRequest, ctx=Depends(require_auth)):
    return currency_service.invoice_summary(body.items, body.currency, body.tax_rate)


@router.get("/formats/{country_code}")
def regional_formats(country_code: str):
    return loc_engine.get_regional_format(country_code)


@router.get("/tax/{country_code}")
def tax_settings(country_code: str):
    return loc_engine.get_tax_settings(country_code)


# ── Regulations ───────────────────────────────────────────────────────────────

@router.get("/regulations")
def get_regulations(country_code: str | None = None, regulation_type: str | None = None):
    return global_repo.get_regulations(country_code, regulation_type)


@router.get("/regulations/compliance/{country_code}")
def get_compliance(country_code: str, ctx=Depends(require_auth)):
    return reg_service.get_compliance_checklist(country_code)


@router.post("/regulations/risk-assessment")
def risk_assessment(body: ComplianceRequest, ctx=Depends(require_auth)):
    return reg_service.get_risk_assessment(
        body.country_code,
        {
            "has_employees": body.has_employees,
            "processes_personal_data": body.processes_personal_data,
            "annual_revenue": body.annual_revenue,
        },
    )


# ── Document Intelligence ─────────────────────────────────────────────────────

@router.post("/analyze")
def analyze_document(body: AnalyzeDocumentRequest, ctx=Depends(require_auth)):
    """
    Analyze a document (contract, invoice, or report).

    POST body:
      { document_type: "contract"|"invoice"|"report", document_name: "...", content: "full text" }
    """
    if not body.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    try:
        return doc_intel.analyze_document(
            ctx.company_id, body.document_type, body.content, body.document_name
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/documents")
def list_documents(document_type: str | None = None, ctx=Depends(require_auth)):
    return global_repo.list_document_analyses(ctx.company_id, document_type)


# ── Global Insights ───────────────────────────────────────────────────────────

@router.get("/insights")
def get_insights(region: str | None = None, ctx=Depends(require_auth)):
    """Return industry trends + competitor analysis + market opportunities."""
    global_repo.log_global_action(ctx.company_id, "insights.view")
    return {
        "industry_trends": insights_service.get_industry_trends(region),
        "competitor_analysis": insights_service.generate_competitor_analysis(ctx.company_id),
        "market_opportunities": insights_service.identify_market_opportunities(ctx.company_id),
        "growth_recommendations": insights_service.get_growth_recommendations(ctx.company_id),
    }


@router.get("/insights/trends")
def industry_trends(region: str | None = None, limit: int = 5):
    return insights_service.get_industry_trends(region, limit)


@router.get("/insights/competitor-analysis")
def competitor_analysis(ctx=Depends(require_auth)):
    return insights_service.generate_competitor_analysis(ctx.company_id)


@router.get("/insights/opportunities")
def market_opportunities(ctx=Depends(require_auth)):
    return insights_service.identify_market_opportunities(ctx.company_id)


@router.get("/insights/growth")
def growth_recommendations(ctx=Depends(require_auth)):
    return insights_service.get_growth_recommendations(ctx.company_id)


# ── AI Assistants ─────────────────────────────────────────────────────────────

@router.post("/assistant")
def ask_assistant(body: AssistantRequest, ctx=Depends(require_auth)):
    """
    Ask one of the four AI assistants.

    assistant_type: legal | financial | operations | strategy
    """
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    try:
        return insights_service.ask_assistant(body.assistant_type, body.question, ctx.company_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ── Global reports ────────────────────────────────────────────────────────────

@router.get("/reports")
def global_reports(ctx=Depends(require_auth)):
    """Full global intelligence report for the dashboard."""
    global_repo.log_global_action(ctx.company_id, "reports.view")
    settings = global_repo.get_language_settings(ctx.company_id)
    country = settings.get("currency_code", "PHP")[:2]  # PH from PHP, US from USD, etc.

    return {
        "language_settings": settings,
        "supported_languages": trans_engine.list_supported_languages(),
        "recent_translations": global_repo.list_translations(ctx.company_id, 5),
        "industry_trends": insights_service.get_industry_trends(limit=4),
        "competitor_analysis": insights_service.generate_competitor_analysis(ctx.company_id),
        "market_opportunities": insights_service.identify_market_opportunities(ctx.company_id),
        "growth_recommendations": insights_service.get_growth_recommendations(ctx.company_id),
        "recent_documents": global_repo.list_document_analyses(ctx.company_id, limit=5),
        "currencies": loc_engine.list_currencies(),
    }

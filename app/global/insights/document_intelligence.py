"""
Document Intelligence — analyze contracts, invoices, and reports.

Extracts key data fields, flags risks, and generates plain-language summaries.
Works with raw text input; no OCR dependency required.
"""

from __future__ import annotations
import hashlib
import re

from .. import repository as global_repo


# ── Extractors ────────────────────────────────────────────────────────────────

def _extract_amounts(text: str) -> list[float]:
    """Find all currency-like numbers in text."""
    patterns = [
        r"₱\s*([\d,]+(?:\.\d{1,2})?)",
        r"\$\s*([\d,]+(?:\.\d{1,2})?)",
        r"(?:PHP|USD|EUR|JPY|CNY|KRW)\s*([\d,]+(?:\.\d{1,2})?)",
        r"(?:amount|total|price|cost|fee|payment)[:\s]+(?:₱|\$)?([\d,]+(?:\.\d{1,2})?)",
    ]
    amounts = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            try:
                amounts.append(float(match.group(1).replace(",", "")))
            except ValueError:
                pass
    return sorted(set(amounts), reverse=True)


def _extract_dates(text: str) -> list[str]:
    """Find date-like strings."""
    patterns = [
        r"\b\d{4}[-/]\d{2}[-/]\d{2}\b",
        r"\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b",
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
        r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\b",
    ]
    dates = []
    for pattern in patterns:
        dates.extend(re.findall(pattern, text, re.IGNORECASE))
    return list(dict.fromkeys(dates))[:10]


def _extract_parties(text: str) -> list[str]:
    """Heuristic party/entity extraction."""
    patterns = [
        r"(?:between|party|parties|client|vendor|supplier|contractor|employer|employee)[:\s]+([A-Z][A-Za-z\s&.,]+?)(?=\n|and|,)",
        r"(?:signed by|executed by|represented by)[:\s]+([A-Z][A-Za-z\s]+?)(?=\n|,)",
    ]
    parties = []
    for pattern in patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            name = m.group(1).strip()
            if 3 < len(name) < 60:
                parties.append(name)
    return list(dict.fromkeys(parties))[:5]


# ── Risk flag detectors ───────────────────────────────────────────────────────

CONTRACT_RISK_KEYWORDS = {
    "high": [
        "unlimited liability", "indemnify", "waive all claims", "perpetual license",
        "irrevocable", "non-compete", "liquidated damages", "automatic renewal",
        "exclusive rights", "all intellectual property",
    ],
    "medium": [
        "jurisdiction", "arbitration", "penalty", "termination without cause",
        "force majeure", "confidentiality", "non-disclosure", "governing law",
        "assignment", "sublicense",
    ],
    "low": [
        "notice period", "amendment", "severability", "entire agreement",
    ],
}

INVOICE_RISK_KEYWORDS = {
    "high": ["overdue", "final notice", "legal action", "collection", "past due"],
    "medium": ["late fee", "interest", "penalty", "disputed", "partial payment"],
    "low": ["reminder", "balance due", "outstanding"],
}


def _detect_risk_flags(text: str, doc_type: str) -> list[dict]:
    risk_map = CONTRACT_RISK_KEYWORDS if doc_type == "contract" else INVOICE_RISK_KEYWORDS
    flags = []
    text_lower = text.lower()
    for level, keywords in risk_map.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                flags.append({"level": level, "keyword": kw, "message": f'Contains "{kw}" — review carefully'})
    return sorted(flags, key=lambda f: ["high", "medium", "low"].index(f["level"]))


# ── Analysers by document type ────────────────────────────────────────────────

def analyze_contract(company_id: int, text: str, document_name: str = "contract") -> dict:
    amounts = _extract_amounts(text)
    dates = _extract_dates(text)
    parties = _extract_parties(text)
    risk_flags = _detect_risk_flags(text, "contract")

    # AI summary
    summary = _ai_summary(company_id, text, "legal contract")

    extracted = {
        "parties": parties,
        "key_amounts": amounts[:5],
        "key_dates": dates[:5],
        "clause_count": text.count("\n") // 3,
        "word_count": len(text.split()),
    }

    content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
    return global_repo.save_document_analysis(
        company_id, "contract", document_name,
        extracted, summary, risk_flags, content_hash,
    )


def analyze_invoice(company_id: int, text: str, document_name: str = "invoice") -> dict:
    amounts = _extract_amounts(text)
    dates = _extract_dates(text)
    risk_flags = _detect_risk_flags(text, "invoice")

    # Try to pull invoice number
    inv_match = re.search(r"(?:invoice|inv|bill)\s*[#no.:]+\s*([A-Z0-9-]+)", text, re.IGNORECASE)
    invoice_number = inv_match.group(1) if inv_match else "—"

    summary = _ai_summary(company_id, text, "business invoice")

    extracted = {
        "invoice_number": invoice_number,
        "amounts_found": amounts[:5],
        "total_amount": amounts[0] if amounts else 0,
        "dates": dates[:3],
        "word_count": len(text.split()),
    }

    content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
    return global_repo.save_document_analysis(
        company_id, "invoice", document_name,
        extracted, summary, risk_flags, content_hash,
    )


def analyze_report(company_id: int, text: str, document_name: str = "report") -> dict:
    amounts = _extract_amounts(text)
    dates = _extract_dates(text)

    # Extract section headers
    headers = re.findall(r"^#+\s+(.+)$|^([A-Z][A-Z\s]{4,}):?\s*$", text, re.MULTILINE)
    sections = [h[0] or h[1] for h in headers if any(h)][:8]

    summary = _ai_summary(company_id, text, "business report")

    extracted = {
        "sections": sections,
        "key_figures": amounts[:8],
        "date_references": dates[:5],
        "word_count": len(text.split()),
        "page_estimate": max(1, len(text.split()) // 250),
    }

    content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
    return global_repo.save_document_analysis(
        company_id, "report", document_name,
        extracted, summary, [], content_hash,
    )


def analyze_document(company_id: int, document_type: str, text: str, document_name: str = "") -> dict:
    """Dispatch to the appropriate analyser."""
    global_repo.log_global_action(company_id, f"document.analyze.{document_type}", document_name[:80])
    name = document_name or document_type

    if document_type == "contract":
        return analyze_contract(company_id, text, name)
    elif document_type == "invoice":
        return analyze_invoice(company_id, text, name)
    elif document_type == "report":
        return analyze_report(company_id, text, name)
    else:
        raise ValueError(f"Unknown document type: {document_type}. Choose: contract, invoice, report")


# ── AI summary helper ─────────────────────────────────────────────────────────

def _ai_summary(company_id: int, text: str, doc_label: str) -> str:
    """Generate a 3-sentence plain-language summary using AI."""
    snippet = text[:3000]
    try:
        from app.services.ai_gateway import generate_sync
        prompt = (
            f"Summarise this {doc_label} in 3 clear, plain-language sentences. "
            f"Focus on: parties involved, key amounts or obligations, and any notable risks.\n\n"
            f"Document:\n{snippet}"
        )
        return generate_sync(prompt, company_id)["reply"]
    except Exception:
        return (
            f"This {doc_label} contains {len(text.split())} words. "
            "AI summary unavailable — check Gemini API key in settings."
        )

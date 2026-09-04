"""
Compliance engine — tax report generation, regulatory checks, document validation.
"""

from __future__ import annotations
import re

from app.enterprise import repository as ent_repo
from app.modules.accounting import repository as accounting_repo
from app.modules.hr import repository as hr_repo


# ── Tax report ────────────────────────────────────────────────────────────────

def generate_tax_report(company_id: int, country_code: str = "PH", period: str = "monthly") -> dict:
    summary = accounting_repo.get_summary(company_id)
    txns = accounting_repo.list_transactions(company_id)

    income = summary.get("income", 0)
    expenses = summary.get("expenses", 0)
    profit = income - expenses

    # Philippine tax defaults
    rates = {
        "PH": {"vat_rate": 0.12, "corporate_tax": 0.25, "label": "Philippine BIR"},
        "US": {"vat_rate": 0.0,  "corporate_tax": 0.21, "label": "US IRS"},
        "EU": {"vat_rate": 0.20, "corporate_tax": 0.19, "label": "EU Tax Authority"},
        "JP": {"vat_rate": 0.10, "corporate_tax": 0.232,"label": "Japan NTA"},
        "CN": {"vat_rate": 0.13, "corporate_tax": 0.25, "label": "China STA"},
        "KR": {"vat_rate": 0.10, "corporate_tax": 0.22, "label": "Korea NTS"},
        "ES": {"vat_rate": 0.21, "corporate_tax": 0.25, "label": "Spain Agencia Tributaria"},
    }
    r = rates.get(country_code.upper(), rates["PH"])

    vat_payable = round(income * r["vat_rate"], 2)
    taxable_profit = max(profit, 0)
    corporate_tax = round(taxable_profit * r["corporate_tax"], 2)
    total_tax = vat_payable + corporate_tax

    result = {
        "country": country_code.upper(),
        "authority": r["label"],
        "period": period,
        "income": income,
        "expenses": expenses,
        "profit": profit,
        "taxable_profit": taxable_profit,
        "vat_rate": f"{r['vat_rate']*100:.0f}%",
        "vat_payable": vat_payable,
        "corporate_tax_rate": f"{r['corporate_tax']*100:.1f}%",
        "corporate_tax_payable": corporate_tax,
        "total_tax_obligation": total_tax,
        "net_after_tax": round(profit - corporate_tax, 2),
        "disclaimer": "This is an estimate only. Consult a licensed accountant for official filings.",
    }

    ent_repo.save_compliance_check(
        company_id, f"tax_report_{country_code}",
        result, passed=True,
        notes=f"Tax obligation: ₱{total_tax:,.2f}"
    )
    ent_repo.log_enterprise_action(company_id, "compliance.tax_report", details=country_code)
    return result


# ── Regulatory checks ─────────────────────────────────────────────────────────

REGULATORY_RULES = {
    "financial_records": {
        "name": "Financial Records Maintained",
        "description": "Business maintains income and expense records",
        "check_fn": lambda d: d.get("has_transactions", False),
        "fix": "Start recording transactions in the Accounting module",
    },
    "employee_records": {
        "name": "Employee Records",
        "description": "Employee information is documented",
        "check_fn": lambda d: d.get("employee_count", 0) > 0,
        "fix": "Add employees in the HR module",
    },
    "data_privacy_policy": {
        "name": "Data Privacy Policy Exists",
        "description": "Company has a documented data privacy policy",
        "check_fn": lambda d: d.get("has_privacy_policy", False),
        "fix": "Create a data privacy policy in the Governance module",
    },
    "expense_approval_policy": {
        "name": "Expense Approval Policy",
        "description": "Company has documented expense approval rules",
        "check_fn": lambda d: d.get("has_expense_policy", False),
        "fix": "Create an expense approval policy in the Governance module",
    },
    "positive_cash_flow": {
        "name": "Positive Cash Flow",
        "description": "Income exceeds expenses",
        "check_fn": lambda d: d.get("profit", -1) >= 0,
        "fix": "Review and reduce expenses or increase revenue",
    },
}


def run_regulatory_checks(company_id: int) -> dict:
    summary = accounting_repo.get_summary(company_id)
    employees = hr_repo.list_employees(company_id)
    txns = accounting_repo.list_transactions(company_id)
    policies = ent_repo.list_policies(company_id)

    privacy_pol = any("privacy" in p.get("category", "") or "privacy" in p.get("title", "").lower() for p in policies)
    expense_pol = any("expense" in p.get("title", "").lower() for p in policies)

    data = {
        "has_transactions": len(txns) > 0,
        "employee_count": len(employees),
        "has_privacy_policy": privacy_pol,
        "has_expense_policy": expense_pol,
        "profit": summary.get("income", 0) - summary.get("expenses", 0),
    }

    results = []
    passed = 0
    for key, rule in REGULATORY_RULES.items():
        ok = rule["check_fn"](data)
        if ok:
            passed += 1
        results.append({
            "rule": key,
            "name": rule["name"],
            "description": rule["description"],
            "passed": ok,
            "fix": rule["fix"] if not ok else None,
        })

    overall = passed == len(REGULATORY_RULES)
    ent_repo.save_compliance_check(
        company_id, "regulatory_checks",
        {"passed_count": passed, "total": len(REGULATORY_RULES)},
        passed=overall,
        notes=f"{passed}/{len(REGULATORY_RULES)} checks passed",
    )

    return {
        "passed": passed,
        "total": len(REGULATORY_RULES),
        "compliance_rate": round(passed / len(REGULATORY_RULES) * 100, 1),
        "overall_compliant": overall,
        "checks": results,
    }


# ── Document validation ───────────────────────────────────────────────────────

DOCUMENT_REQUIREMENTS = {
    "invoice": [
        {"field": "Invoice number", "pattern": r"(?:invoice|inv|bill)\s*[#no.]+\s*[A-Z0-9-]+"},
        {"field": "Date", "pattern": r"\b\d{4}[-/]\d{2}[-/]\d{2}\b|\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b"},
        {"field": "Amount/Total", "pattern": r"(?:total|amount|due)[:\s]+(?:₱|\$|PHP)?\s*[\d,]+"},
        {"field": "Vendor/Supplier name", "pattern": r"(?:from|vendor|supplier|issued by)[:\s]+[A-Za-z]+"},
    ],
    "contract": [
        {"field": "Party names", "pattern": r"(?:between|party|parties)[:\s]+[A-Z][A-Za-z]+"},
        {"field": "Date or effective date", "pattern": r"\b\d{4}[-/]\d{2}[-/]\d{2}\b"},
        {"field": "Signatures or execution clause", "pattern": r"(?:signed|executed|agreed|witness)"},
        {"field": "Terms or obligations", "pattern": r"(?:shall|must|agree|obligation|term)"},
    ],
    "payslip": [
        {"field": "Employee name", "pattern": r"(?:employee|name)[:\s]+[A-Za-z]+"},
        {"field": "Pay period", "pattern": r"(?:period|from|pay date)[:\s]+\d"},
        {"field": "Net pay", "pattern": r"(?:net pay|net salary|take home)[:\s]+(?:₱|\$)?[\d,]+"},
        {"field": "Deductions", "pattern": r"(?:sss|philhealth|pagibig|tax|deduction)"},
    ],
}


def validate_document(company_id: int, document_type: str, content: str) -> dict:
    requirements = DOCUMENT_REQUIREMENTS.get(document_type.lower(), [])
    if not requirements:
        raise ValueError(f"Unknown document type '{document_type}'. Choose: {list(DOCUMENT_REQUIREMENTS)}")

    checks = []
    passed = 0
    for req in requirements:
        found = bool(re.search(req["pattern"], content, re.IGNORECASE))
        if found:
            passed += 1
        checks.append({"field": req["field"], "found": found})

    score = round(passed / len(requirements) * 100, 1)
    valid = passed == len(requirements)

    missing = [c["field"] for c in checks if not c["found"]]

    ent_repo.log_enterprise_action(
        company_id, "compliance.doc_validate",
        details=f"{document_type}: {passed}/{len(requirements)} fields found"
    )

    return {
        "document_type": document_type,
        "valid": valid,
        "completeness_score": score,
        "fields_found": passed,
        "fields_required": len(requirements),
        "field_checks": checks,
        "missing_fields": missing,
        "recommendation": (
            "Document appears complete and valid." if valid
            else f"Document is missing: {', '.join(missing)}. Add these before submission."
        ),
    }

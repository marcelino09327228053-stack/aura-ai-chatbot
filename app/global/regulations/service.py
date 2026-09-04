"""
Regulations service — country-specific compliance rules and alerts.
"""

from .. import repository as global_repo
from ..localization.engine import TAX_SETTINGS


COMPLIANCE_CHECKLIST: dict[str, list[dict]] = {
    "PH": [
        {"item": "BIR Registration", "required": True, "description": "All businesses must register with BIR"},
        {"item": "VAT Registration", "required": True, "description": "Required if annual gross sales exceed ₱3M"},
        {"item": "SSS Registration", "required": True, "description": "Mandatory for all employers"},
        {"item": "PhilHealth Registration", "required": True, "description": "Mandatory health insurance"},
        {"item": "Pag-IBIG Registration", "required": True, "description": "Mandatory housing fund"},
        {"item": "DTI/SEC Registration", "required": True, "description": "Business name or corporation registration"},
        {"item": "13th Month Pay", "required": True, "description": "Due by December 24 each year"},
        {"item": "Data Privacy Act Compliance", "required": True, "description": "NPC registration if processing sensitive data"},
    ],
    "US": [
        {"item": "EIN Registration", "required": True, "description": "Employer Identification Number from IRS"},
        {"item": "State Business License", "required": True, "description": "Varies by state and business type"},
        {"item": "Sales Tax Permits", "required": True, "description": "Required in states with nexus"},
        {"item": "Federal Tax Filing", "required": True, "description": "Annual corporate return (Form 1120)"},
        {"item": "CCPA Compliance", "required": False, "description": "Required if serving California residents"},
    ],
    "EU": [
        {"item": "GDPR Compliance", "required": True, "description": "Data protection compliance mandatory"},
        {"item": "VAT Registration", "required": True, "description": "Required for B2C sales in EU"},
        {"item": "EU Business Registration", "required": True, "description": "Register in country of establishment"},
    ],
    "JP": [
        {"item": "Company Registration", "required": True, "description": "Register at Legal Affairs Bureau"},
        {"item": "Tax Office Registration", "required": True, "description": "Notify National Tax Agency"},
        {"item": "Social Insurance", "required": True, "description": "Health insurance and pension"},
        {"item": "Consumption Tax Filing", "required": True, "description": "Annual filing; quarterly if large"},
    ],
    "CN": [
        {"item": "Business License", "required": True, "description": "Issued by SAMR"},
        {"item": "Tax Registration", "required": True, "description": "Register with local tax authority"},
        {"item": "VAT Invoice System", "required": True, "description": "Use official VAT invoice system (Fapiao)"},
        {"item": "PIPL Compliance", "required": True, "description": "Personal Information Protection Law"},
    ],
    "KR": [
        {"item": "Business Registration", "required": True, "description": "Register with local tax office"},
        {"item": "VAT Filing", "required": True, "description": "Biannual VAT returns"},
        {"item": "National Pension", "required": True, "description": "Mandatory for all employees"},
        {"item": "PIPA Compliance", "required": True, "description": "Personal Information Protection Act"},
    ],
    "ES": [
        {"item": "Tax ID (NIF/CIF)", "required": True, "description": "Required for all businesses"},
        {"item": "IAE Registration", "required": True, "description": "Economic Activities Tax"},
        {"item": "IVA (VAT) Filing", "required": True, "description": "Quarterly VAT returns"},
        {"item": "Social Security", "required": True, "description": "Employer/employee contributions"},
        {"item": "LOPD/GDPR Compliance", "required": True, "description": "Data protection compliance"},
    ],
}


def get_compliance_checklist(country_code: str) -> dict:
    code = country_code.upper()
    checklist = COMPLIANCE_CHECKLIST.get(code, [])
    regulations = global_repo.get_regulations(country_code=code)
    tax = TAX_SETTINGS.get(code, {})
    return {
        "country": code,
        "compliance_items": checklist,
        "required_count": sum(1 for i in checklist if i["required"]),
        "regulations": regulations,
        "tax_overview": tax,
    }


def get_risk_assessment(country_code: str, company_profile: dict) -> dict:
    code = country_code.upper()
    checklist = COMPLIANCE_CHECKLIST.get(code, [])
    missing = []
    # Heuristic: check if company has enough data to indicate compliance
    has_employees = company_profile.get("has_employees", False)
    processes_data = company_profile.get("processes_personal_data", True)
    annual_revenue = company_profile.get("annual_revenue", 0)

    for item in checklist:
        if not item["required"]:
            continue
        name = item["item"]
        if "SSS" in name or "PhilHealth" in name or "Pag-IBIG" in name or "Social" in name or "Pension" in name:
            if not has_employees:
                continue
        if "Privacy" in name or "GDPR" in name or "PIPL" in name or "PIPA" in name or "LOPD" in name:
            if not processes_data:
                continue
        if "VAT" in name and code == "PH" and annual_revenue < 3_000_000:
            continue
        missing.append(name)

    risk_level = "high" if len(missing) > 4 else "medium" if len(missing) > 1 else "low"
    return {
        "country": code,
        "risk_level": risk_level,
        "potentially_missing_compliance": missing,
        "recommendation": (
            "Consult a local accountant or legal advisor to ensure full compliance."
            if risk_level != "low"
            else "Basic compliance appears covered. Periodic review recommended."
        ),
    }

"""
Risk management engine — financial, operational, security, and compliance risks.

Risk score = likelihood × impact (both 1–3), giving scores 1–9.
  1–2: Low    3–4: Medium    6–9: High
"""

from __future__ import annotations

from app.corporation import repository as corp_repo
from app.modules.accounting import repository as accounting_repo
from app.modules.crm import repository as crm_repo
from app.modules.hr import repository as hr_repo
from app.modules.inventory import repository as inventory_repo


RISK_SCORE_LABELS = {1: "low", 2: "low", 3: "medium", 4: "medium", 6: "high", 9: "critical"}


def _score_label(score: int) -> str:
    return RISK_SCORE_LABELS.get(score, "high" if score >= 6 else "medium")


# ── Financial risks ───────────────────────────────────────────────────────────

def assess_financial_risks(company_id: int) -> list[dict]:
    summary = accounting_repo.get_summary(company_id)
    income = summary.get("income", 0)
    expenses = summary.get("expenses", 0)
    profit = income - expenses

    risks_data = []

    if profit < 0:
        risks_data.append({
            "risk_type": "financial", "title": "Operating Loss",
            "description": f"Business is running at a loss of ₱{abs(profit):,.2f}.",
            "likelihood": "high", "impact": "high",
            "mitigation": "Immediate cost audit; identify and cut non-essential expenses within 30 days.",
        })

    if income > 0 and expenses / income > 0.85:
        risks_data.append({
            "risk_type": "financial", "title": "Dangerously High Expense Ratio",
            "description": f"Expenses are {expenses/income*100:.0f}% of income — leaves minimal buffer.",
            "likelihood": "high", "impact": "medium",
            "mitigation": "Renegotiate top 3 expense items; target ratio below 70%.",
        })

    if income < 50_000:
        risks_data.append({
            "risk_type": "financial", "title": "Low Revenue Base",
            "description": "Monthly revenue is under ₱50,000 — vulnerable to any demand drop.",
            "likelihood": "medium", "impact": "high",
            "mitigation": "Diversify revenue streams; add at least one recurring income source.",
        })

    risks_data.append({
        "risk_type": "financial", "title": "Single-Customer Concentration",
        "description": "If top customers represent >50% of revenue, losing one is critical.",
        "likelihood": "medium", "impact": "high",
        "mitigation": "Limit any single customer to <30% of revenue; actively diversify.",
    })

    saved = [corp_repo.save_risk(company_id, r) for r in risks_data]
    corp_repo.log_corp_action(company_id, "risk.financial_assessment")
    return saved


# ── Operational risks ─────────────────────────────────────────────────────────

def assess_operational_risks(company_id: int) -> list[dict]:
    employees = hr_repo.list_employees(company_id)
    products = inventory_repo.list_products(company_id)

    risks_data = []

    out_of_stock = [p for p in products if p.get("stock", 0) == 0]
    if out_of_stock:
        risks_data.append({
            "risk_type": "operational", "title": "Stockout Risk",
            "description": f"{len(out_of_stock)} products are out of stock, causing potential lost sales.",
            "likelihood": "high", "impact": "medium",
            "mitigation": "Implement automatic reorder points; place emergency orders immediately.",
        })

    if len(employees) == 1:
        risks_data.append({
            "risk_type": "operational", "title": "Single Point of Failure — Team",
            "description": "Single-employee businesses stop operating if that person is unavailable.",
            "likelihood": "medium", "impact": "high",
            "mitigation": "Document key processes; cross-train or hire a second person for critical tasks.",
        })

    risks_data.append({
        "risk_type": "operational", "title": "Process Documentation Gap",
        "description": "Undocumented processes create inconsistency and knowledge silos.",
        "likelihood": "medium", "impact": "medium",
        "mitigation": "Document top 5 business processes as SOPs; review quarterly.",
    })

    risks_data.append({
        "risk_type": "operational", "title": "Supplier Dependency",
        "description": "Reliance on a single supplier creates supply chain vulnerability.",
        "likelihood": "medium", "impact": "high",
        "mitigation": "Identify and qualify at least one backup supplier per critical product.",
    })

    saved = [corp_repo.save_risk(company_id, r) for r in risks_data]
    corp_repo.log_corp_action(company_id, "risk.operational_assessment")
    return saved


# ── Security risks ────────────────────────────────────────────────────────────

def assess_security_risks(company_id: int) -> list[dict]:
    risks_data = [
        {
            "risk_type": "security", "title": "Data Breach / Unauthorised Access",
            "description": "Customer and financial data exposed due to weak access controls or passwords.",
            "likelihood": "medium", "impact": "high",
            "mitigation": "Enforce strong passwords, 2FA, and role-based access. Audit user accounts quarterly.",
        },
        {
            "risk_type": "security", "title": "Phishing and Social Engineering",
            "description": "Employees tricked into revealing credentials or approving fraudulent transactions.",
            "likelihood": "high", "impact": "high",
            "mitigation": "Security awareness training; implement email filtering and verify all payment requests.",
        },
        {
            "risk_type": "security", "title": "No Data Backup / Disaster Recovery",
            "description": "System failure or ransomware could cause total data loss without backups.",
            "likelihood": "medium", "impact": "high",
            "mitigation": "Implement automated daily backups; test restore procedure monthly.",
        },
        {
            "risk_type": "security", "title": "Third-Party Vendor Risk",
            "description": "SaaS tools and vendors may have their own security vulnerabilities.",
            "likelihood": "low", "impact": "medium",
            "mitigation": "Review vendor security practices; only share data with vendors on need-to-know basis.",
        },
    ]
    saved = [corp_repo.save_risk(company_id, r) for r in risks_data]
    corp_repo.log_corp_action(company_id, "risk.security_assessment")
    return saved


# ── Compliance risks ──────────────────────────────────────────────────────────

def assess_compliance_risks(company_id: int) -> list[dict]:
    risks_data = [
        {
            "risk_type": "compliance", "title": "Tax Non-Compliance",
            "description": "Late or incorrect tax filings result in penalties and interest charges.",
            "likelihood": "medium", "impact": "high",
            "mitigation": "Use accounting software; engage a licensed accountant for filings.",
        },
        {
            "risk_type": "compliance", "title": "Data Privacy Act Violation",
            "description": "Improper handling of personal data may result in NPC complaints and fines.",
            "likelihood": "low", "impact": "high",
            "mitigation": "Implement privacy policy, data consent forms, and data minimisation practices.",
        },
        {
            "risk_type": "compliance", "title": "Labour Law Non-Compliance",
            "description": "Failure to pay mandatory benefits (SSS, PhilHealth, Pag-IBIG, 13th month) exposes to DOLE penalties.",
            "likelihood": "medium", "impact": "medium",
            "mitigation": "Automate payroll with mandatory deductions; maintain employee records.",
        },
        {
            "risk_type": "compliance", "title": "Business Permit Non-Renewal",
            "description": "Operating without a valid business permit may result in closure orders.",
            "likelihood": "low", "impact": "high",
            "mitigation": "Set annual renewal reminders; designate a person responsible for permit compliance.",
        },
    ]
    saved = [corp_repo.save_risk(company_id, r) for r in risks_data]
    corp_repo.log_corp_action(company_id, "risk.compliance_assessment")
    return saved


# ── Combined risk dashboard ───────────────────────────────────────────────────

def run_full_risk_assessment(company_id: int) -> dict:
    corp_repo.log_corp_action(company_id, "risk.full_assessment")
    financial = assess_financial_risks(company_id)
    operational = assess_operational_risks(company_id)
    security = assess_security_risks(company_id)
    compliance = assess_compliance_risks(company_id)

    all_risks = financial + operational + security + compliance
    critical = [r for r in all_risks if r.get("risk_score", 0) >= 6]
    high = [r for r in all_risks if r.get("risk_score", 0) in (3, 4)]
    low = [r for r in all_risks if r.get("risk_score", 0) <= 2]

    overall_level = "critical" if critical else "high" if high else "medium" if high else "low"

    return {
        "overall_risk_level": overall_level,
        "total_risks": len(all_risks),
        "critical_count": len(critical),
        "high_count": len(high),
        "low_count": len(low),
        "by_type": {
            "financial": financial,
            "operational": operational,
            "security": security,
            "compliance": compliance,
        },
        "top_risks": sorted(all_risks, key=lambda r: r.get("risk_score", 0), reverse=True)[:5],
    }


def get_risk_register(company_id: int) -> list[dict]:
    return corp_repo.list_risks(company_id)

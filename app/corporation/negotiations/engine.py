"""
Negotiation engine — supplier, customer, and contract negotiation support.

Generates structured negotiation strategies, BATNA analysis,
and recommended contract terms using live business data.
"""

from __future__ import annotations

from app.corporation import repository as corp_repo
from app.modules.accounting import repository as accounting_repo
from app.modules.crm import repository as crm_repo
from app.modules.inventory import repository as inventory_repo


# ── Supplier negotiation ──────────────────────────────────────────────────────

def negotiate_supplier(company_id: int, supplier_name: str, product: str,
                       current_price: float, desired_discount_pct: float = 10.0) -> dict:
    summary = accounting_repo.get_summary(company_id)
    income = summary.get("income", 0)
    expenses = summary.get("expenses", 0)

    # Our leverage points
    leverage = []
    if income > 100_000:
        leverage.append(f"Significant monthly revenue (₱{income:,.0f}) demonstrates reliable payment capacity")
    if expenses > 0:
        leverage.append("Consistent procurement history")
    leverage.append("Potential for long-term contract (12+ months)")
    leverage.append("Possibility of volume increase with business growth")

    target_price = round(current_price * (1 - desired_discount_pct / 100), 2)
    walkaway_price = round(current_price * 0.95, 2)  # Max 5% above target before walking away
    opening_offer = round(current_price * (1 - (desired_discount_pct + 5) / 100), 2)

    proposed_terms = {
        "current_price": current_price,
        "opening_offer": opening_offer,
        "target_price": target_price,
        "walkaway_price": walkaway_price,
        "payment_terms": "Net 30",
        "contract_length": "12 months",
        "volume_commitment": "Minimum order guaranteed monthly",
    }

    strategy = {
        "approach": "collaborative",
        "opening_position": f"Request {desired_discount_pct + 5:.0f}% discount citing volume and long-term commitment",
        "concession_plan": f"Concede to {desired_discount_pct:.0f}% if supplier offers Net 30 payment terms",
        "batna": "Source alternative supplier or negotiate with 2 suppliers simultaneously",
        "walk_away_condition": f"If final price exceeds ₱{walkaway_price:,.2f}",
    }

    result = corp_repo.save_negotiation(company_id, {
        "negotiation_type": "supplier",
        "counterparty": supplier_name,
        "subject": product,
        "our_position": {"target_price": target_price, "leverage": leverage},
        "their_position": {"current_price": current_price},
        "proposed_terms": proposed_terms,
    })

    corp_repo.log_corp_action(company_id, "negotiation.supplier", "coo", f"{supplier_name}: {product}")
    return {**result, "strategy": strategy, "leverage_points": leverage, "proposed_terms": proposed_terms}


# ── Customer proposal ─────────────────────────────────────────────────────────

def generate_customer_proposal(company_id: int, customer_name: str,
                                deal_value: float, proposal_type: str = "standard") -> dict:
    products = inventory_repo.list_products(company_id)
    customers = crm_repo.count_customers(company_id)

    # Discount logic based on deal size
    discount = 0.0
    if deal_value > 100_000:
        discount = 10.0
    elif deal_value > 50_000:
        discount = 5.0
    elif deal_value > 20_000:
        discount = 3.0

    discounted_value = round(deal_value * (1 - discount / 100), 2)

    inclusions = ["Dedicated account manager", "Priority support", "30-day satisfaction guarantee"]
    if deal_value > 50_000:
        inclusions.append("Quarterly business review")
    if deal_value > 100_000:
        inclusions.append("Custom onboarding and training")

    terms = {
        "deal_value": deal_value,
        "discount_pct": discount,
        "final_value": discounted_value,
        "payment_terms": "50% upfront, 50% on delivery" if deal_value > 50_000 else "Full payment on delivery",
        "delivery_timeline": "14 business days",
        "warranty": "90 days",
        "inclusions": inclusions,
    }

    proposal_text = (
        f"Proposal for {customer_name}\n"
        f"Deal Value: ₱{deal_value:,.2f}"
        + (f" (with {discount:.0f}% loyalty discount: ₱{discounted_value:,.2f})" if discount > 0 else "")
        + f"\nPayment Terms: {terms['payment_terms']}"
        + f"\nDelivery: {terms['delivery_timeline']}"
        + f"\nIncludes: {', '.join(inclusions)}"
    )

    corp_repo.save_negotiation(company_id, {
        "negotiation_type": "customer",
        "counterparty": customer_name,
        "subject": f"{proposal_type} proposal — ₱{deal_value:,.0f}",
        "our_position": terms,
        "proposed_terms": terms,
    })

    corp_repo.log_corp_action(company_id, "negotiation.customer_proposal", "cmo", customer_name)
    return {"customer": customer_name, "proposal": proposal_text, "terms": terms}


# ── Contract recommendations ──────────────────────────────────────────────────

CONTRACT_TEMPLATES = {
    "freelancer": {
        "title": "Freelance / Independent Contractor Agreement",
        "key_clauses": [
            "Scope of work and deliverables",
            "Payment terms and schedule",
            "Intellectual property ownership (work-for-hire)",
            "Confidentiality / NDA clause",
            "Termination with 14-day notice",
            "Independent contractor status (no employment relationship)",
        ],
        "red_flags": ["Unlimited revision requests", "Payment contingent on business success", "Non-compete exceeding 1 year"],
        "recommended_duration": "Project-based or max 12 months",
    },
    "supplier": {
        "title": "Supplier / Vendor Agreement",
        "key_clauses": [
            "Product specifications and quality standards",
            "Pricing and payment terms (Net 30)",
            "Delivery schedule and penalties for delay",
            "Warranty and defect liability",
            "Force majeure clause",
            "Termination for cause / convenience",
            "Governing law and dispute resolution",
        ],
        "red_flags": ["Exclusivity requirements", "No price-lock guarantee", "Automatic price escalation clauses"],
        "recommended_duration": "12 months with renewal option",
    },
    "employment": {
        "title": "Employment Contract",
        "key_clauses": [
            "Job title, duties, and reporting line",
            "Salary, benefits, and 13th month pay (PH)",
            "Working hours and remote work policy",
            "Probationary period (6 months PH standard)",
            "Confidentiality and non-disclosure",
            "Termination and separation pay",
            "Data privacy obligations",
        ],
        "red_flags": ["Waiver of mandatory benefits", "Non-compete beyond 6 months", "No overtime pay provisions"],
        "recommended_duration": "Indefinite (regular employment after probation)",
    },
    "saas": {
        "title": "SaaS / Software Subscription Agreement",
        "key_clauses": [
            "License scope and permitted users",
            "Service Level Agreement (uptime guarantee)",
            "Data ownership and portability",
            "Privacy and data security obligations",
            "Auto-renewal and cancellation terms",
            "Limitation of liability",
            "Price escalation cap",
        ],
        "red_flags": ["No data export option", "Unlimited liability clause", "No SLA commitments"],
        "recommended_duration": "Annual with monthly exit option",
    },
}


def recommend_contract(company_id: int, contract_type: str) -> dict:
    template = CONTRACT_TEMPLATES.get(contract_type.lower())
    if not template:
        raise ValueError(f"Unknown contract type: {contract_type}. Choose: {list(CONTRACT_TEMPLATES)}")

    corp_repo.log_corp_action(company_id, "negotiation.contract_rec", "cto", contract_type)
    return {
        "contract_type": contract_type,
        **template,
        "disclaimer": "This is a general guide only. Have a licensed attorney review before signing.",
    }

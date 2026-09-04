"""
Global business insights — industry trends, competitor analysis, market opportunities,
and growth recommendations.

Also hosts the four AI assistants:
  - Legal assistant
  - Financial assistant
  - Operations assistant
  - Strategy assistant
"""

from __future__ import annotations

from .. import repository as global_repo
from app.modules.accounting import repository as accounting_repo
from app.modules.crm import repository as crm_repo
from app.modules.inventory import repository as inventory_repo


# ── Industry trend database ───────────────────────────────────────────────────

INDUSTRY_TRENDS: list[dict] = [
    {
        "trend": "AI-Powered Customer Service",
        "impact": "high",
        "region": "global",
        "description": "Businesses using AI chatbots report 30% reduction in support costs and 25% faster resolution times.",
        "action": "Deploy or upgrade AI support agents with custom FAQ training.",
    },
    {
        "trend": "E-commerce Growth in Southeast Asia",
        "impact": "high",
        "region": "SEA",
        "description": "SEA e-commerce market expected to reach $330B by 2025, driven by mobile-first consumers.",
        "action": "Add online ordering channels and mobile-optimised checkout.",
    },
    {
        "trend": "Subscription Business Models",
        "impact": "medium",
        "region": "global",
        "description": "SaaS and subscription models show 5–8× higher customer lifetime value vs one-time sales.",
        "action": "Introduce monthly or annual subscription tiers for your products.",
    },
    {
        "trend": "Data Privacy Regulations Tightening",
        "impact": "medium",
        "region": "global",
        "description": "GDPR, CCPA, and similar laws are spreading globally. Non-compliance fines are increasing.",
        "action": "Audit data collection practices and implement consent management.",
    },
    {
        "trend": "Green Business Practices",
        "impact": "medium",
        "region": "global",
        "description": "73% of consumers prefer eco-conscious brands. ESG reporting becoming mandatory in more markets.",
        "action": "Document and publish sustainability initiatives.",
    },
    {
        "trend": "Digital Payment Adoption",
        "impact": "high",
        "region": "global",
        "description": "Cash transactions declining globally. QR codes, e-wallets, and BNPL growing rapidly.",
        "action": "Integrate GCash, PayMaya, or international payment gateways.",
    },
    {
        "trend": "Remote Work & Distributed Teams",
        "impact": "medium",
        "region": "global",
        "description": "Companies with remote-friendly policies attract 2× more qualified candidates.",
        "action": "Invest in collaboration tools and async work processes.",
    },
    {
        "trend": "Hyper-Personalisation",
        "impact": "high",
        "region": "global",
        "description": "Personalised marketing generates 6× higher transaction rates than generic campaigns.",
        "action": "Use CRM data to segment customers and personalise communications.",
    },
]


def get_industry_trends(region: str | None = None, limit: int = 5) -> list[dict]:
    if region:
        filtered = [t for t in INDUSTRY_TRENDS if t["region"] in (region, "global")]
    else:
        filtered = INDUSTRY_TRENDS
    return filtered[:limit]


# ── Competitor analysis ───────────────────────────────────────────────────────

def generate_competitor_analysis(company_id: int) -> dict:
    products = inventory_repo.list_products(company_id)
    customers = crm_repo.count_customers(company_id)
    summary = accounting_repo.get_summary(company_id)
    income = summary.get("income", 0)

    strengths = []
    weaknesses = []
    opportunities = []

    if products:
        strengths.append(f"Active product catalogue with {len(products)} SKUs")
    else:
        weaknesses.append("No products in inventory — hard to compete without catalogue")

    if customers > 20:
        strengths.append(f"Established customer base ({customers} customers)")
    elif customers > 5:
        opportunities.append("Growing customer base — focus on retention now")
    else:
        weaknesses.append("Very small customer base — acquisition must be priority")

    if income > 100_000:
        strengths.append(f"Strong revenue base (₱{income:,.0f})")
    elif income > 10_000:
        opportunities.append("Revenue is growing — ready for marketing investment")
    else:
        weaknesses.append("Low revenue — focus on high-margin products first")

    opportunities.append("Explore partnerships with complementary businesses")
    opportunities.append("Leverage AI tools for competitive differentiation")

    global_repo.save_insight(company_id, "competitor_analysis", "SWOT Analysis", str({
        "strengths": strengths, "weaknesses": weaknesses, "opportunities": opportunities
    }))

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "opportunities": opportunities,
        "threats": [
            "Larger competitors with more marketing budget",
            "Rapidly changing customer expectations",
            "Regulatory complexity in target markets",
        ],
    }


# ── Market opportunities ──────────────────────────────────────────────────────

def identify_market_opportunities(company_id: int) -> list[dict]:
    leads = crm_repo.list_leads(company_id)
    products = inventory_repo.list_products(company_id)
    opportunities = []

    open_leads = [l for l in leads if l.get("status") in ("new", "contacted")]
    if open_leads:
        opportunities.append({
            "type": "sales",
            "title": "Convert Open Leads",
            "description": f"{len(open_leads)} leads waiting for follow-up.",
            "priority": "high",
            "estimated_value": len(open_leads) * 8000,
        })

    if products:
        avg_price = sum(p.get("price", 0) for p in products) / len(products)
        if avg_price < 500:
            opportunities.append({
                "type": "pricing",
                "title": "Premium Product Line Opportunity",
                "description": "Average product price is low. Introducing premium SKUs can improve margins.",
                "priority": "medium",
                "estimated_value": 0,
            })

    opportunities.append({
        "type": "market_expansion",
        "title": "Online Sales Channel",
        "description": "Southeast Asian e-commerce is growing 20% YoY. Adding an online store can triple reach.",
        "priority": "high",
        "estimated_value": 50000,
    })

    opportunities.append({
        "type": "partnership",
        "title": "B2B Partnership Programme",
        "description": "Partner with complementary businesses for cross-referral and bundled offerings.",
        "priority": "medium",
        "estimated_value": 30000,
    })

    for opp in opportunities:
        global_repo.save_insight(
            company_id, "market_opportunity",
            opp["title"], opp["description"],
        )

    return opportunities


# ── Growth recommendations ────────────────────────────────────────────────────

def get_growth_recommendations(company_id: int) -> list[dict]:
    summary = accounting_repo.get_summary(company_id)
    customers = crm_repo.count_customers(company_id)
    income = summary.get("income", 0)
    expenses = summary.get("expenses", 0)

    recs = []

    if income > 0 and (expenses / max(income, 1)) > 0.7:
        recs.append({
            "category": "financial",
            "title": "Reduce Operating Expenses",
            "description": "Your expense ratio is above 70%. Review subscriptions, overhead, and supplier contracts.",
            "impact": "high",
        })

    if customers < 50:
        recs.append({
            "category": "growth",
            "title": "Invest in Customer Acquisition",
            "description": "At under 50 customers, growth is the top priority. Allocate 15–20% of revenue to marketing.",
            "impact": "high",
        })
    else:
        recs.append({
            "category": "growth",
            "title": "Optimise Customer Retention",
            "description": "With an established base, keeping customers costs 5× less than acquiring new ones.",
            "impact": "medium",
        })

    recs.append({
        "category": "technology",
        "title": "Automate Repetitive Tasks",
        "description": "Use workflow automation for order processing, follow-ups, and reporting to free up team time.",
        "impact": "medium",
    })

    recs.append({
        "category": "global",
        "title": "Enter a New Geographic Market",
        "description": "Consider expanding to one neighbouring country with low regulatory barriers.",
        "impact": "high",
    })

    return recs


# ── AI Assistants ─────────────────────────────────────────────────────────────

ASSISTANT_SYSTEM_PROMPTS = {
    "legal": (
        "You are a legal assistant for a small-to-medium business. "
        "Provide practical, plain-language guidance on contracts, regulations, compliance, "
        "and legal risks. Always recommend consulting a licensed attorney for binding advice."
    ),
    "financial": (
        "You are a financial assistant for a small-to-medium business. "
        "Provide clear advice on cash flow, budgeting, investment, taxes, and financial planning. "
        "Always recommend consulting a licensed accountant for official filings."
    ),
    "operations": (
        "You are an operations assistant for a small-to-medium business. "
        "Help optimise workflows, supply chains, team management, inventory, and daily processes. "
        "Focus on practical, actionable improvements."
    ),
    "strategy": (
        "You are a business strategy assistant. "
        "Help with market analysis, competitive positioning, growth planning, pricing strategy, "
        "and long-term business development. Be concise and data-driven."
    ),
}


def ask_assistant(assistant_type: str, question: str, company_id: int) -> dict:
    system_prompt = ASSISTANT_SYSTEM_PROMPTS.get(assistant_type)
    if not system_prompt:
        raise ValueError(f"Unknown assistant type: {assistant_type}. Choose: {list(ASSISTANT_SYSTEM_PROMPTS)}")

    global_repo.log_global_action(company_id, f"assistant.{assistant_type}", question[:100])

    try:
        from app.services.ai_service import generate_reply
        full_prompt = f"{system_prompt}\n\nUser question: {question}"
        answer = generate_reply(full_prompt)
    except Exception as exc:
        answer = (
            f"[{assistant_type.title()} Assistant] I'm here to help with your {assistant_type} questions. "
            f"However, AI service is currently unavailable ({exc}). "
            f"Please check your AI configuration in Settings."
        )

    return {
        "assistant": assistant_type,
        "question": question,
        "answer": answer,
        "disclaimer": ASSISTANT_SYSTEM_PROMPTS[assistant_type].split("Always")[-1].strip()
        if "Always" in ASSISTANT_SYSTEM_PROMPTS[assistant_type] else "",
    }

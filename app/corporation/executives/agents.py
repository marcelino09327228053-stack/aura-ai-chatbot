"""
Executive AI Agents — CEO, CFO, COO, CTO, CMO.

Each agent has a defined role, domain expertise, decision scope,
and a system prompt for AI-powered analysis. Agents pull real
business data and produce structured decisions + recommendations.
"""

from __future__ import annotations

from app.corporation import repository as corp_repo
from app.modules.accounting import repository as accounting_repo
from app.modules.crm import repository as crm_repo
from app.modules.hr import repository as hr_repo
from app.modules.inventory import repository as inventory_repo


# ── Agent registry ────────────────────────────────────────────────────────────

EXECUTIVE_AGENTS = {
    "ceo": {
        "title": "Chief Executive Officer",
        "emoji": "👔",
        "domain": "Overall business strategy, growth, and company direction",
        "decision_types": ["strategic", "expansion", "partnership", "crisis"],
        "system_prompt": (
            "You are the CEO AI agent for a growing SMB. You analyse the full business picture — "
            "revenue, growth, team, and market position — then provide clear, decisive strategic guidance. "
            "Be direct, data-driven, and focus on sustainable growth."
        ),
    },
    "cfo": {
        "title": "Chief Financial Officer",
        "emoji": "💰",
        "domain": "Financial health, budgeting, capital allocation, tax, and risk",
        "decision_types": ["investment", "budget", "cost_reduction", "financial_risk"],
        "system_prompt": (
            "You are the CFO AI agent. You analyse financial statements, cash flow, and expense patterns "
            "to protect and grow company capital. Provide conservative, numbers-first recommendations. "
            "Always flag financial risks and suggest specific mitigation steps."
        ),
    },
    "coo": {
        "title": "Chief Operating Officer",
        "emoji": "⚙️",
        "domain": "Operations, processes, supply chain, team efficiency, and delivery",
        "decision_types": ["operational", "process", "supply_chain", "hiring"],
        "system_prompt": (
            "You are the COO AI agent. You focus on operational efficiency, process improvement, "
            "team structure, and delivery excellence. Identify bottlenecks and recommend practical "
            "operational changes that improve throughput and reduce waste."
        ),
    },
    "cto": {
        "title": "Chief Technology Officer",
        "emoji": "💻",
        "domain": "Technology, systems, security, data, and digital transformation",
        "decision_types": ["technology", "security", "digital", "infrastructure"],
        "system_prompt": (
            "You are the CTO AI agent. You evaluate the company's technology stack, data security, "
            "automation opportunities, and digital maturity. Recommend technology investments that "
            "deliver measurable business value. Prioritise security and scalability."
        ),
    },
    "cmo": {
        "title": "Chief Marketing Officer",
        "emoji": "📣",
        "domain": "Marketing, brand, customer acquisition, retention, and revenue growth",
        "decision_types": ["marketing", "brand", "customer", "campaign"],
        "system_prompt": (
            "You are the CMO AI agent. You analyse customer data, market trends, and competitor "
            "positioning to drive revenue through targeted marketing strategies. Focus on measurable "
            "ROI, customer lifetime value, and cost-effective acquisition channels."
        ),
    },
}


# ── Data context builder ──────────────────────────────────────────────────────

def _build_business_context(company_id: int) -> str:
    summary = accounting_repo.get_summary(company_id)
    customers = crm_repo.count_customers(company_id)
    leads = crm_repo.list_leads(company_id)
    employees = hr_repo.list_employees(company_id)
    products = inventory_repo.list_products(company_id)

    income = summary.get("income", 0)
    expenses = summary.get("expenses", 0)
    profit = income - expenses
    conversion = (
        len([l for l in leads if l.get("status") == "converted"]) / max(len(leads), 1) * 100
    )

    return (
        f"BUSINESS SNAPSHOT:\n"
        f"- Monthly Income: ₱{income:,.2f}\n"
        f"- Monthly Expenses: ₱{expenses:,.2f}\n"
        f"- Net Profit: ₱{profit:,.2f}\n"
        f"- Total Customers: {customers}\n"
        f"- Open Leads: {len([l for l in leads if l.get('status') in ('new','contacted')])}\n"
        f"- Lead Conversion Rate: {conversion:.1f}%\n"
        f"- Employees: {len(employees)}\n"
        f"- Products in Inventory: {len(products)}\n"
        f"- Out-of-Stock Items: {len([p for p in products if p.get('stock',0)==0])}\n"
    )


# ── Agent runner ──────────────────────────────────────────────────────────────

def run_agent(company_id: int, agent_role: str, question: str | None = None) -> dict:
    """
    Run an executive agent:
    1. Build business context from live data
    2. Generate AI analysis + recommendation
    3. Save decision to DB
    4. Return structured result
    """
    agent = EXECUTIVE_AGENTS.get(agent_role)
    if not agent:
        raise ValueError(f"Unknown agent role: {agent_role}. Choose: {list(EXECUTIVE_AGENTS)}")

    context = _build_business_context(company_id)
    user_q = question or f"As {agent['title']}, analyse the current business state and provide your top 3 recommendations."

    full_prompt = (
        f"{agent['system_prompt']}\n\n"
        f"{context}\n\n"
        f"Question/Task: {user_q}\n\n"
        f"Provide a structured response with:\n"
        f"1. ANALYSIS (2-3 sentences)\n"
        f"2. KEY FINDINGS (3 bullet points)\n"
        f"3. RECOMMENDATIONS (3 actionable steps)\n"
        f"4. CONFIDENCE LEVEL (high/medium/low) and why"
    )

    try:
        from app.services.ai_service import generate_reply
        ai_response = generate_reply(full_prompt)
        confidence = 0.82
    except Exception as exc:
        ai_response = (
            f"[{agent['title']} Agent] AI service unavailable ({exc}).\n\n"
            f"Based on available data:\n{context}\n\n"
            f"Standard recommendations for your business stage:\n"
            f"1. Focus on profitability before expansion\n"
            f"2. Document key processes for scalability\n"
            f"3. Invest in customer retention programmes"
        )
        confidence = 0.55

    decision = corp_repo.save_decision(
        company_id=company_id,
        agent_role=agent_role,
        decision_type=agent["decision_types"][0],
        title=user_q[:120],
        analysis=ai_response,
        recommendation=ai_response,
        confidence=confidence,
    )
    corp_repo.log_corp_action(company_id, f"agent.{agent_role}.run", agent_role, user_q[:80])

    return {
        **decision,
        "agent": {
            "role": agent_role,
            "title": agent["title"],
            "emoji": agent["emoji"],
            "domain": agent["domain"],
        },
        "context_snapshot": context,
    }


def run_all_agents(company_id: int) -> dict:
    """Run a quick briefing from all five executive agents."""
    corp_repo.log_corp_action(company_id, "agents.run_all", details="C-suite briefing")
    results = {}
    for role in EXECUTIVE_AGENTS:
        try:
            results[role] = run_agent(company_id, role)
        except Exception as exc:
            results[role] = {"error": str(exc), "agent_role": role}
    return results

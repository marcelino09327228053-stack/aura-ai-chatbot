"""Expansion tools — branches, companies, markets, global deployment."""

from __future__ import annotations

from app.universe import repository as uni_repo

MARKET_REGIONS = [
    {"code": "PH", "name": "Philippines", "timezone": "Asia/Manila"},
    {"code": "US", "name": "United States", "timezone": "America/New_York"},
    {"code": "JP", "name": "Japan", "timezone": "Asia/Tokyo"},
    {"code": "SG", "name": "Singapore", "timezone": "Asia/Singapore"},
    {"code": "EU", "name": "European Union", "timezone": "Europe/Berlin"},
    {"code": "AU", "name": "Australia", "timezone": "Australia/Sydney"},
]

DEPLOYMENT_PROFILES = {
    "development": {"replicas": 1, "region": "local", "ssl": False},
    "staging": {"replicas": 2, "region": "regional", "ssl": True},
    "production": {"replicas": 3, "region": "global", "ssl": True, "cdn": True},
}


def plan_new_branch(company_id: int, name: str, region: str, config: dict | None = None) -> dict:
    expansion = uni_repo.save_expansion(company_id, "branch", name, region, {
        **(config or {}),
        "type": "branch",
        "estimated_setup_days": 14,
    })
    uni_repo.log_universe_action(company_id, "expansion.branch", details=name)
    return expansion


def plan_new_company(company_id: int, name: str, region: str, config: dict | None = None) -> dict:
    expansion = uni_repo.save_expansion(company_id, "company", name, region, {
        **(config or {}),
        "type": "subsidiary",
        "requires_approval": True,
    })
    uni_repo.create_approval(company_id, {
        "approval_type": "expansion",
        "title": f"New company: {name}",
        "details": f"Subsidiary expansion in {region}",
    })
    uni_repo.log_universe_action(company_id, "expansion.company", details=name)
    return expansion


def plan_new_market(company_id: int, market_code: str, config: dict | None = None) -> dict:
    market = next((m for m in MARKET_REGIONS if m["code"] == market_code), None)
    name = market["name"] if market else market_code
    expansion = uni_repo.save_expansion(company_id, "market", name, market_code, {
        **(config or {}),
        "market_code": market_code,
        "timezone": market.get("timezone") if market else "UTC",
        "readiness_score": 0.6 + (hash(market_code + str(company_id)) % 35) / 100,
    })
    uni_repo.log_universe_action(company_id, "expansion.market", details=market_code)
    return expansion


def plan_global_deployment(company_id: int, profile: str = "production", regions: list[str] | None = None) -> dict:
    deploy_config = DEPLOYMENT_PROFILES.get(profile, DEPLOYMENT_PROFILES["production"])
    target_regions = regions or [m["code"] for m in MARKET_REGIONS[:3]]
    expansion = uni_repo.save_expansion(company_id, "deployment", f"Global {profile.title()}", "global", {
        "profile": profile,
        "regions": target_regions,
        **deploy_config,
    })
    uni_repo.log_universe_action(company_id, "expansion.deployment", details=profile)
    return expansion


def run_expansion(company_id: int, expansion_type: str, params: dict) -> dict:
    """Dispatcher for POST /universe/expand."""
    if expansion_type == "branch":
        result = plan_new_branch(company_id, params.get("name", "New Branch"), params.get("region", "PH"), params)
    elif expansion_type == "company":
        result = plan_new_company(company_id, params.get("name", "New Company"), params.get("region", "PH"), params)
    elif expansion_type == "market":
        result = plan_new_market(company_id, params.get("market_code", "PH"), params)
    elif expansion_type == "deployment":
        result = plan_global_deployment(
            company_id,
            params.get("profile", "production"),
            params.get("regions"),
        )
    else:
        return {"error": f"Unknown expansion type: {expansion_type}"}

    return {"expansion": result, "type": expansion_type, "status": "planned"}


def expansion_overview(company_id: int) -> dict:
    all_expansions = uni_repo.list_expansions(company_id)
    return {
        "branches": uni_repo.list_expansions(company_id, "branch"),
        "companies": uni_repo.list_expansions(company_id, "company"),
        "markets": uni_repo.list_expansions(company_id, "market"),
        "deployments": uni_repo.list_expansions(company_id, "deployment"),
        "available_markets": MARKET_REGIONS,
        "deployment_profiles": DEPLOYMENT_PROFILES,
        "total": len(all_expansions),
    }

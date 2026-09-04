"""Network governance — permissions and tenant policies."""

from app.network import repository as net_repo

NETWORK_MODES = {
    "private": {
        "description": "No data leaves this company. Full tenant isolation.",
        "sync_enabled": False,
        "federation_enabled": False,
        "shared_ai": False,
    },
    "shared": {
        "description": "Participate in network sync with encrypted payloads.",
        "sync_enabled": True,
        "federation_enabled": True,
        "shared_ai": False,
    },
    "enterprise": {
        "description": "Full federation, shared AI resources, and marketplace.",
        "sync_enabled": True,
        "federation_enabled": True,
        "shared_ai": True,
    },
}


def get_mode_config(network_mode: str) -> dict:
    return NETWORK_MODES.get(network_mode, NETWORK_MODES["private"])


def enforce_tenant_isolation(company_id: int, target_company_id: int) -> bool:
    """Companies can only access their own data unless enterprise shared resources."""
    if company_id == target_company_id:
        return True
    governance = net_repo.get_governance(company_id)
    return governance["network_mode"] == "enterprise"


def set_policies(company_id: int, network_mode: str, policies: dict | None = None) -> dict:
    if network_mode not in NETWORK_MODES:
        raise ValueError(f"Invalid mode: {network_mode}")
    return net_repo.set_governance(company_id, network_mode, policies)


def get_policies(company_id: int) -> dict:
    governance = net_repo.get_governance(company_id)
    mode_config = get_mode_config(governance["network_mode"])
    return {**governance, "mode_config": mode_config}

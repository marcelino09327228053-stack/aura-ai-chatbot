"""Network marketplace — shared extensions across the federation."""

from app.cloud.marketplace import service as cloud_marketplace
from app.network import repository as net_repo


def list_network_extensions() -> list[dict]:
    shared = net_repo.list_shared_resources("plugin")
    catalog = cloud_marketplace.list_extensions()
    catalog_keys = {e["plugin_key"] for e in catalog}
    for resource in shared:
        key = resource["resource_key"]
        if key not in catalog_keys:
            catalog.append({
                "plugin_key": key,
                "name": f"Shared: {key}",
                "version": "network",
                "source": "federation",
                "owner_company_id": resource["owner_company_id"],
            })
    return catalog


def publish_extension(company_id: int, plugin_key: str) -> dict:
    governance = net_repo.get_governance(company_id)
    if governance["network_mode"] not in ("shared", "enterprise"):
        raise ValueError("Publishing requires shared or enterprise network mode.")
    return net_repo.share_resource("plugin", plugin_key, company_id)

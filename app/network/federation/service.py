"""Network federation — multi-instance connectivity."""

from app.network import repository as net_repo

NETWORK_MODES = ("private", "shared", "enterprise")


def join(company_id: int, network_mode: str = "shared", remote_node_id: str | None = None) -> dict:
    if network_mode not in NETWORK_MODES:
        raise ValueError(f"Invalid network mode: {network_mode}")
    membership = net_repo.join_network(company_id, network_mode)
    if remote_node_id:
        net_repo.register_remote_node(remote_node_id, f"Remote {remote_node_id[:8]}")
    return membership


def leave(company_id: int) -> dict:
    net_repo.leave_network(company_id)
    return {"company_id": company_id, "status": "left"}


def status(company_id: int) -> dict:
    local_node = net_repo.ensure_local_node()
    membership = net_repo.get_membership(company_id)
    governance = net_repo.get_governance(company_id)
    return {
        "local_node": local_node,
        "membership": membership,
        "governance": governance,
        "network_members": len(net_repo.list_members()),
        "connected_nodes": len(net_repo.list_nodes()),
        "shared_resources": len(net_repo.list_shared_resources()),
    }

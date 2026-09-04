"""Network clusters — group companies and nodes."""

from app.network import repository as net_repo


def get_cluster_info() -> dict:
    nodes = net_repo.list_nodes()
    members = net_repo.list_members()
    return {
        "node_count": len(nodes),
        "member_count": len(members),
        "nodes": nodes,
        "members": members,
    }


def assign_company_to_cluster(company_id: int, node_id: str | None = None) -> dict:
    node_id = node_id or net_repo.get_local_node_id()
    net_repo.ensure_local_node()
    membership = net_repo.get_membership(company_id)
    if membership:
        return membership
    return net_repo.join_network(company_id, "shared", node_id)

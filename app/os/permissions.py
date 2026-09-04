"""OS-level permissions."""

ROLES = ("owner", "admin", "employee", "guest")

PERMISSIONS = {
    "owner": {
        "os.manage", "os.view", "os.run_workflows", "os.manage_automation",
        "os.view_memory", "os.manage_agents",
    },
    "admin": {
        "os.manage", "os.view", "os.run_workflows", "os.manage_automation",
        "os.view_memory", "os.manage_agents",
    },
    "employee": {
        "os.view", "os.run_workflows", "os.view_memory",
    },
    "guest": {
        "os.view",
    },
}


def has_permission(role: str, permission: str) -> bool:
    return permission in PERMISSIONS.get(role, set())


def resolve_role(user_id: int | None, owner_id: int | None, team_role: str | None) -> str:
    if user_id is None:
        return "guest"
    if owner_id and user_id == owner_id:
        return "owner"
    if team_role in ("owner", "admin", "member"):
        if team_role == "member":
            return "employee"
        return team_role
    return "employee"

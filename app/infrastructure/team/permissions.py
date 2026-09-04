"""Team roles and permissions."""

ROLES = ("owner", "admin", "member", "viewer")

ROLE_PERMISSIONS = {
    "owner": {
        "manage_team", "manage_billing", "manage_settings",
        "view_reports", "edit_data", "delete_data", "run_agents", "manage_plugins",
    },
    "admin": {
        "manage_team", "manage_billing", "manage_settings", "view_reports",
        "edit_data", "delete_data", "run_agents", "manage_plugins",
    },
    "member": {
        "view_reports", "edit_data", "run_agents",
    },
    "viewer": {
        "view_reports",
    },
}

# Cloud portal permissions (mapped to team roles)
CLOUD_PERMISSIONS = {
    "manage_billing": {"owner", "admin"},
    "manage_settings": {"owner", "admin"},
}



def has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())

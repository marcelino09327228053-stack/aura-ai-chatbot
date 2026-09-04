"""Team collaboration service."""

from app.infrastructure.team import permissions, repository as team_repo


def ensure_owner_member(company_id: int, owner_id: int) -> None:
    existing = team_repo.get_member(company_id, owner_id)
    if not existing:
        team_repo.add_member(company_id, owner_id, "owner")


def invite_member(company_id: int, user_id: int, role: str = "member") -> dict:
    if role not in permissions.ROLES:
        raise ValueError(f"Invalid role: {role}")
    if role == "owner":
        raise ValueError("Cannot assign owner role via invite.")
    return team_repo.add_member(company_id, user_id, role)


def check_permission(company_id: int, user_id: int, owner_id: int | None, permission: str) -> bool:
    role = team_repo.get_user_role(company_id, user_id, owner_id)
    return permissions.has_permission(role, permission)

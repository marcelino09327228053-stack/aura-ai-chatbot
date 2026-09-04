"""
FastAPI dependencies for authentication and company context.
"""

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import LEGACY_COMPANY_ID
from app.core.security import decode_access_token
from app.database import company_repository, user_repository

bearer_scheme = HTTPBearer(auto_error=False)


class AuthContext:
    def __init__(self, user_id: int | None, company_id: int, authenticated: bool):
        self.user_id = user_id
        self.company_id = company_id
        self.authenticated = authenticated


def get_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_company_id: int | None = Header(default=None, alias="X-Company-Id"),
) -> AuthContext:
    """
    Resolve the active company from JWT (and optional header override after validation).
    Unauthenticated requests fall back to the legacy company for backward compatibility.
    """
    if credentials is None:
        return AuthContext(user_id=None, company_id=LEGACY_COMPANY_ID, authenticated=False)

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    user_id = int(payload["sub"])
    company_id = int(payload.get("company_id", LEGACY_COMPANY_ID))

    if x_company_id is not None and x_company_id != company_id:
        if not company_repository.user_owns_company(user_id, x_company_id):
            raise HTTPException(status_code=403, detail="Access denied for this company.")
        company_id = x_company_id

    return AuthContext(user_id=user_id, company_id=company_id, authenticated=True)


def require_auth(ctx: AuthContext = Depends(get_auth_context)) -> AuthContext:
    if not ctx.authenticated:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return ctx


def get_current_user(ctx: AuthContext = Depends(require_auth)) -> dict:
    user = user_repository.get_user_by_id(ctx.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found.")
    return user

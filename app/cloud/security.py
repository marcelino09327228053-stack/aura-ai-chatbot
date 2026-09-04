"""Aura Cloud security — encryption and permission helpers."""

import base64
import hashlib
import os

from cryptography.fernet import Fernet
from fastapi import HTTPException

from app.infrastructure.team import service as team_service
from app.database import company_repository


def _fernet() -> Fernet:
    key = os.getenv("CLOUD_ENCRYPTION_KEY", "")
    if not key:
        derived = hashlib.sha256(
            os.getenv("SECRET_KEY", "aura-dev").encode()
        ).digest()
        key = base64.urlsafe_b64encode(derived)
    return Fernet(key)


def encrypt_value(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_value(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()


def require_cloud_permission(
    company_id: int,
    user_id: int,
    permission: str,
) -> None:
    company = company_repository.get_company(company_id)
    owner_id = company["owner_id"] if company else None
    if not team_service.check_permission(company_id, user_id, owner_id, permission):
        raise HTTPException(status_code=403, detail=f"Permission denied: {permission}")

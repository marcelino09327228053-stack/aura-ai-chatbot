"""Authentication business logic."""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from fastapi import HTTPException

from app.core.config import RESET_TOKEN_EXPIRE_HOURS, SECRET_KEY, get_aura_env
from app.core.security import (
    create_access_token,
    generate_reset_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.database import (
    company_repository,
    login_code_repository,
    reset_token_repository,
    subscription_repository,
    user_repository,
)
from app.services import email_service
from app.services.subscription_service import check_can_create_company


def _login_code_hash(email: str, code: str) -> str:
    value = f"{email.lower().strip()}:{code}:{SECRET_KEY}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def request_login_code(email: str) -> dict:
    normalized_email = email.lower().strip()
    code = f"{secrets.randbelow(1_000_000):06d}"
    delivered = email_service.send_login_code(normalized_email, code)
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    login_code_repository.create_code(
        normalized_email,
        _login_code_hash(normalized_email, code),
        expires_at,
    )

    result = {
        "message": "Confirmation code sent. Check your email.",
        "expires_in_seconds": 600,
        "delivery": "email" if delivered else "development",
    }
    if not delivered and get_aura_env() != "production":
        result["development_code"] = code
        result["message"] = "Development mode: use the confirmation code shown below."
    return result


def verify_confirmation_code(email: str, code: str) -> None:
    normalized_email = email.lower().strip()
    submitted_code = code.strip()
    if len(submitted_code) != 6 or not submitted_code.isdigit():
        raise HTTPException(status_code=400, detail="Enter a valid 6-digit code.")
    record = login_code_repository.get_latest_code(normalized_email)
    if record is None or record["used_at"] is not None:
        raise HTTPException(status_code=400, detail="Invalid or expired confirmation code.")
    if record["attempts"] >= 5:
        raise HTTPException(status_code=429, detail="Too many attempts. Request a new code.")
    expires_at = datetime.fromisoformat(record["expires_at"])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        login_code_repository.consume_code(record["id"])
        raise HTTPException(status_code=400, detail="Invalid or expired confirmation code.")
    expected = _login_code_hash(normalized_email, submitted_code)
    if not hmac.compare_digest(expected, record["code_hash"]):
        login_code_repository.record_failed_attempt(record["id"])
        raise HTTPException(status_code=400, detail="Invalid or expired confirmation code.")
    login_code_repository.consume_code(record["id"])


def verify_login_code(email: str, code: str, company_name: str | None = None,
                      referral_token: str | None = None) -> dict:
    normalized_email = email.lower().strip()
    submitted_code = code.strip()
    if len(submitted_code) != 6 or not submitted_code.isdigit():
        raise HTTPException(status_code=400, detail="Enter a valid 6-digit code.")

    record = login_code_repository.get_latest_code(normalized_email)
    if record is None or record["used_at"] is not None:
        raise HTTPException(status_code=400, detail="Invalid or expired confirmation code.")
    if record["attempts"] >= 5:
        raise HTTPException(status_code=429, detail="Too many attempts. Request a new code.")

    expires_at = datetime.fromisoformat(record["expires_at"])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        login_code_repository.consume_code(record["id"])
        raise HTTPException(status_code=400, detail="Invalid or expired confirmation code.")

    expected = _login_code_hash(normalized_email, submitted_code)
    if not hmac.compare_digest(expected, record["code_hash"]):
        login_code_repository.record_failed_attempt(record["id"])
        raise HTTPException(status_code=400, detail="Invalid or expired confirmation code.")

    login_code_repository.consume_code(record["id"])
    user = user_repository.get_user_by_email(normalized_email)
    new_user = user is None
    if user is None:
        user = user_repository.create_user(
            normalized_email,
            hash_password(secrets.token_urlsafe(32)),
        )

    companies = company_repository.list_companies_by_owner(user["id"])
    if not companies:
        company = company_repository.create_company(
            user["id"],
            (company_name or "My Company").strip() or "My Company",
        )
        subscription_repository.create_subscription(company["id"], "free")
        from app.infrastructure.team import service as team_service
        team_service.ensure_owner_member(company["id"], user["id"])
        _attribute_new_company(company["id"], user["id"], referral_token)
        companies = [company]

    company = companies[0]
    token = create_access_token(user["id"], company["id"])
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "created_at": user["created_at"],
        },
        "company": company,
        "companies": companies,
        "subscription": subscription_repository.get_subscription_by_company(company["id"]),
        "new_user": new_user,
    }


def login_with_verified_identity(
    provider: str,
    subject: str,
    email: str,
    full_name: str = "",
    profile_image: str = "",
    referral_token: str | None = None,
) -> dict:
    """Sign in with a verified external identity and link matching emails safely."""
    from app.database import oauth_identity_repository

    normalized_email = email.lower().strip()
    identity = oauth_identity_repository.get_identity(provider, subject)
    user = user_repository.get_user_by_id(identity["user_id"]) if identity else None
    new_user = False
    if user is None:
        user = user_repository.get_user_by_email(normalized_email)
        if user is None:
            new_user = True
            user = user_repository.create_user(
                normalized_email,
                hash_password(secrets.token_urlsafe(32)),
            )
        oauth_identity_repository.save_identity(
            user["id"], provider, subject, normalized_email
        )

    if full_name and not user.get("full_name"):
        user = user_repository.update_profile(user["id"], full_name) or user
    if profile_image and not user.get("profile_image"):
        user = user_repository.update_profile_image(user["id"], profile_image) or user

    companies = company_repository.list_companies_by_owner(user["id"])
    if not companies:
        company = company_repository.create_company(user["id"], "My Company")
        subscription_repository.create_subscription(company["id"], "free")
        from app.infrastructure.team import service as team_service
        team_service.ensure_owner_member(company["id"], user["id"])
        _attribute_new_company(company["id"], user["id"], referral_token)
        companies = [company]

    company = companies[0]
    token = create_access_token(user["id"], company["id"])
    return {
        "token": token,
        "user": user,
        "company": company,
        "companies": companies,
        "subscription": subscription_repository.get_subscription_by_company(company["id"]),
        "new_user": new_user,
        "provider": provider,
    }


def register_user(email: str, password: str, company_name: str,
                  referral_token: str | None = None) -> dict:
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    if user_repository.get_user_by_email(email):
        raise HTTPException(status_code=409, detail="Email already registered.")

    user = user_repository.create_user(email, hash_password(password))
    company = company_repository.create_company(user["id"], company_name)
    subscription_repository.create_subscription(company["id"], "free")
    from app.infrastructure.team import service as team_service
    team_service.ensure_owner_member(company["id"], user["id"])
    _attribute_new_company(company["id"], user["id"], referral_token)
    from app.infrastructure.audit import service as audit_service
    audit_service.record("user.register", company["id"], user["id"])
    token = create_access_token(user["id"], company["id"])

    return {
        "token": token,
        "user": user,
        "company": company,
        "subscription": subscription_repository.get_subscription_by_company(company["id"]),
    }


def _attribute_new_company(company_id: int, user_id: int, token: str | None) -> None:
    if not token: return
    from app.referrals.service import agent_id_from_token
    from app.referrals.repository import create_attribution
    agent_id = agent_id_from_token(token)
    if agent_id:
        _, created = create_attribution(company_id, user_id, agent_id)
        if created:
            from app.infrastructure.audit import service as audit_service
            audit_service.record("referral.attributed", company_id, user_id)


def login_user(email: str, password: str) -> dict:
    user = user_repository.get_user_by_email(email)
    if user is None or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    companies = company_repository.list_companies_by_owner(user["id"])
    if not companies:
        company = company_repository.create_company(user["id"], "My Company")
        subscription_repository.create_subscription(company["id"], "free")
        companies = [company]

    company = companies[0]
    token = create_access_token(user["id"], company["id"])

    from app.infrastructure.audit import service as audit_service
    from app.infrastructure.redis.session_cache import save_session
    audit_service.record("user.login", company["id"], user["id"])
    save_session(token[:32], {"user_id": user["id"], "company_id": company["id"]})

    return {
        "token": token,
        "user": {"id": user["id"], "email": user["email"], "created_at": user["created_at"]},
        "company": company,
        "companies": companies,
        "subscription": subscription_repository.get_subscription_by_company(company["id"]),
    }


def select_company(user_id: int, company_id: int) -> dict:
    if not company_repository.user_owns_company(user_id, company_id):
        raise HTTPException(status_code=403, detail="Access denied for this company.")

    company = company_repository.get_company(company_id)
    token = create_access_token(user_id, company_id)

    return {
        "token": token,
        "company": company,
        "subscription": subscription_repository.get_subscription_by_company(company_id),
    }


def create_company_for_user(user_id: int, company_name: str) -> dict:
    check_can_create_company(user_id)
    company = company_repository.create_company(user_id, company_name)
    subscription_repository.create_subscription(company["id"], "free")
    from app.infrastructure.team import service as team_service
    team_service.ensure_owner_member(company["id"], user_id)
    return {
        "company": company,
        "subscription": subscription_repository.get_subscription_by_company(company["id"]),
    }


def request_password_reset(email: str) -> dict:
    user = user_repository.get_user_by_email(email)
    if user is None:
        return {"message": "If that email exists, a reset link has been sent."}

    token = generate_reset_token()
    reset_token_repository.create_reset_token(
        user["id"],
        hash_token(token),
        RESET_TOKEN_EXPIRE_HOURS,
    )

    return {
        "message": "If that email exists, a reset link has been sent.",
        "reset_token": token,
    }


def reset_password(token: str, new_password: str) -> dict:
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    user_id = reset_token_repository.consume_reset_token(hash_token(token))
    if user_id is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    user_repository.update_password(user_id, hash_password(new_password))
    return {"message": "Password updated successfully."}

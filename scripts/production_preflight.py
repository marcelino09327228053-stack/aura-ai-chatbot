"""Fail-safe production configuration check without printing secret values."""
import argparse
import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=".env")
    args = parser.parse_args()
    env_path = (ROOT / args.env_file).resolve()
    if not env_path.is_file():
        print(f"FAIL: environment file not found: {env_path.name}")
        return 1
    load_dotenv(env_path, override=True)
    os.environ["AURA_ENV"] = "production"

    from app.core.config import validate_production_config

    errors = []
    try:
        validate_production_config()
    except RuntimeError as exc:
        errors.append(str(exc))

    required = (
        "PUBLIC_DOMAIN", "POSTGRES_PASSWORD", "REDIS_PASSWORD", "OWNER_EMAIL",
        "OWNER_PASSWORD_HASH", "OWNER_CONSOLE_SECRET", "OWNER_TOTP_SECRET",
    )
    for name in required:
        value = os.getenv(name, "").strip()
        if not value or "replace-with" in value or "example.com" in value or "generate-with" in value:
            errors.append(f"{name} is missing or still a placeholder")
    if os.getenv("OWNER_MFA_REQUIRED", "true").lower() not in {"1", "true", "yes"}:
        errors.append("OWNER_MFA_REQUIRED must be true")
    domain = os.getenv("PUBLIC_DOMAIN", "").lower()
    hosts = {item.strip().lower() for item in os.getenv("ALLOWED_HOSTS", "").split(",")}
    if domain and domain not in hosts:
        errors.append("PUBLIC_DOMAIN must be present in ALLOWED_HOSTS")
    try:
        if unquote(urlsplit(os.getenv("DATABASE_URL", "")).password or "") != os.getenv("POSTGRES_PASSWORD", ""):
            errors.append("DATABASE_URL password does not match POSTGRES_PASSWORD")
        if unquote(urlsplit(os.getenv("REDIS_URL", "")).password or "") != os.getenv("REDIS_PASSWORD", ""):
            errors.append("REDIS_URL password does not match REDIS_PASSWORD")
    except ValueError:
        errors.append("DATABASE_URL or REDIS_URL is invalid")

    if errors:
        print("PRODUCTION PREFLIGHT FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PRODUCTION PREFLIGHT PASSED")
    print("Secrets were validated but not displayed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

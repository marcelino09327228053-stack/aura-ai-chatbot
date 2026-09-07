"""
Application configuration from environment variables.
"""

import os
import json

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "aura-dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))
RESET_TOKEN_EXPIRE_HOURS = int(os.getenv("RESET_TOKEN_EXPIRE_HOURS", "1"))

# Legacy company used when no JWT is provided (backward compatibility).
LEGACY_COMPANY_ID = int(os.getenv("LEGACY_COMPANY_ID", "1"))

PLAN_LIMITS = {
    "free": {"max_companies": 1, "max_messages_per_day": 100},
    "test": {"max_companies": 5, "max_messages_per_day": 5000},
    "pro": {"max_companies": 5, "max_messages_per_day": 5000},
    "enterprise": {"max_companies": None, "max_messages_per_day": None},
}


def _json_env(name: str, default: dict) -> dict:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return default
    return value if isinstance(value, dict) else default


# These are operational defaults, not final commercial prices. Override the entire
# catalog with AI_PLAN_CONFIG_JSON in each deployment.
AI_PLAN_CONFIG = _json_env(
    "AI_PLAN_CONFIG_JSON",
    {
        "free": {
            "price_minor": 0,
            "monthly_ai_allowance_minor": 0,
            "currency": "PHP",
            "max_companies": 1,
        },
        "test": {
            "price_minor": 150_000,
            "monthly_ai_allowance_minor": 50_000,
            "currency": "PHP",
            "max_companies": 5,
        },
    },
)

AI_GATEWAY_PROVIDER_ORDER = tuple(
    item.strip().lower()
    for item in os.getenv("AI_GATEWAY_PROVIDER_ORDER", "gemini,openai,claude,groq").split(",")
    if item.strip()
)
AI_GATEWAY_MAX_RETRIES = max(0, int(os.getenv("AI_GATEWAY_MAX_RETRIES", "1")))
AI_GATEWAY_GLOBAL_CONCURRENCY = max(1, int(os.getenv("AI_GATEWAY_GLOBAL_CONCURRENCY", "20")))
AI_GATEWAY_CUSTOMER_CONCURRENCY = max(1, int(os.getenv("AI_GATEWAY_CUSTOMER_CONCURRENCY", "2")))
AI_GATEWAY_QUEUE_LIMIT = max(1, int(os.getenv("AI_GATEWAY_QUEUE_LIMIT", "200")))
AI_GATEWAY_CUSTOMER_QUEUE_LIMIT = max(1, int(os.getenv("AI_GATEWAY_CUSTOMER_QUEUE_LIMIT", "10")))
AI_GATEWAY_QUEUE_TIMEOUT_SECONDS = max(0.1, float(os.getenv("AI_GATEWAY_QUEUE_TIMEOUT_SECONDS", "30")))
AI_GATEWAY_RETRY_BASE_SECONDS = max(0.0, float(os.getenv("AI_GATEWAY_RETRY_BASE_SECONDS", "0.5")))
AI_GATEWAY_RETRY_MAX_SECONDS = max(AI_GATEWAY_RETRY_BASE_SECONDS, float(os.getenv("AI_GATEWAY_RETRY_MAX_SECONDS", "15")))
AI_GATEWAY_RETRY_JITTER_SECONDS = max(0.0, float(os.getenv("AI_GATEWAY_RETRY_JITTER_SECONDS", "0.25")))
AI_GATEWAY_PROVIDER_COOLDOWN_SECONDS = max(0.1, float(os.getenv("AI_GATEWAY_PROVIDER_COOLDOWN_SECONDS", "30")))
AI_GATEWAY_DISTRIBUTED_LEASE_SECONDS = max(5, int(os.getenv("AI_GATEWAY_DISTRIBUTED_LEASE_SECONDS", "120")))
AI_GATEWAY_QUEUE_POLL_SECONDS = max(0.01, float(os.getenv("AI_GATEWAY_QUEUE_POLL_SECONDS", "0.05")))
AI_MODEL_COSTS_USD = _json_env("AI_MODEL_COSTS_USD_JSON", {})
AI_GATEWAY_USD_TO_ALLOWANCE_RATE = float(
    os.getenv("AI_GATEWAY_USD_TO_ALLOWANCE_RATE", "58.0")
)
MOCK_PAYMENTS_ENABLED = os.getenv("MOCK_PAYMENTS_ENABLED", "true").lower() in (
    "1", "true", "yes"
)
PAYMENT_WEBHOOK_MAX_AGE_SECONDS = max(60, int(os.getenv("PAYMENT_WEBHOOK_MAX_AGE_SECONDS", "600")))

MODULE_NAMES = ("crm", "inventory", "accounting", "hr", "reports", "analytics")

AGENT_TYPES = ("support", "sales", "hr", "accounting", "marketing")


def is_module_enabled(name: str) -> bool:
    """Business modules are enabled by default; set MODULE_<NAME>_ENABLED=false to disable."""
    key = f"MODULE_{name.upper()}_ENABLED"
    return os.getenv(key, "true").lower() in ("1", "true", "yes")


def agents_enabled() -> bool:
    """Agent platform is off by default for backward-compatible /chat."""
    return os.getenv("AGENTS_ENABLED", "false").lower() in ("1", "true", "yes")


def is_agent_type_enabled(agent_type: str) -> bool:
    """Per-agent flags default to enabled when the platform is on."""
    try:
        from app.owner.repository import agent_enabled
        configured = agent_enabled(agent_type)
        if configured is not None:
            return configured
    except Exception:
        pass
    key = f"AGENT_{agent_type.upper()}_ENABLED"
    return os.getenv(key, "true").lower() in ("1", "true", "yes")


def plugins_enabled() -> bool:
    """Plugin platform is off by default."""
    return os.getenv("PLUGINS_ENABLED", "false").lower() in ("1", "true", "yes")


def get_aura_env() -> str:
    return os.getenv("AURA_ENV", "development").lower()


def validate_production_config() -> None:
    """Fail closed when required production security settings are unsafe."""
    if get_aura_env() != "production":
        return
    errors = []
    secret = os.getenv("SECRET_KEY", "")
    if len(secret) < 32 or "change" in secret.lower() or "dev-secret" in secret.lower():
        errors.append("SECRET_KEY must be a strong random value of at least 32 characters")
    for name in ("PAYMENT_WEBHOOK_SECRET", "AI_METRICS_BEARER_TOKEN"):
        value = os.getenv(name, "")
        if len(value) < 32 or "replace" in value.lower():
            errors.append(f"{name} must be a strong random value of at least 32 characters")
    if len(os.getenv("CLOUD_ENCRYPTION_KEY", "")) < 40:
        errors.append("CLOUD_ENCRYPTION_KEY must be a dedicated Fernet key")
    if os.getenv("DB_BACKEND", "").lower() != "postgres" or not os.getenv("DATABASE_URL", ""):
        errors.append("production requires DB_BACKEND=postgres and DATABASE_URL")
    if os.getenv("REDIS_ENABLED", "").lower() not in ("1", "true", "yes") or not os.getenv("REDIS_URL", ""):
        errors.append("production requires REDIS_ENABLED=true and REDIS_URL")
    if not os.getenv("ALLOWED_HOSTS", "").strip():
        errors.append("ALLOWED_HOSTS must contain the production hostname")
    origins = get_cors_origins()
    if not origins or any(not origin.startswith("https://") for origin in origins):
        errors.append("CORS_ALLOWED_ORIGINS must contain only explicit HTTPS origins")
    if errors:
        raise RuntimeError("Unsafe production configuration: " + "; ".join(errors))


PROVIDER_SECURITY_CONFIG = {
    "gemini": {"key_env": "GEMINI_API_KEY"},
    "openai": {"key_env": "OPENAI_API_KEY"},
    "claude": {"key_env": "ANTHROPIC_API_KEY"},
    "groq": {"key_env": "GROQ_API_KEY"},
    "deepseek": {"key_env": "DEEPSEEK_API_KEY"},
    "grok": {"key_env": "XAI_API_KEY"},
}


def get_cors_origins() -> list[str]:
    configured = [
        item.strip()
        for item in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
        if item.strip()
    ]
    if configured:
        return configured
    if get_aura_env() == "production":
        return []
    return [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:8081",
        "http://localhost:8081",
    ]

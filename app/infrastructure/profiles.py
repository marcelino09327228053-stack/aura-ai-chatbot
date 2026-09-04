"""Deployment environment profiles."""

import os

PROFILES = {
    "development": {
        "debug": True,
        "db_backend": "sqlite",
        "redis_enabled": False,
        "cors_origins": ["*"],
        "log_level": "DEBUG",
    },
    "staging": {
        "debug": False,
        "db_backend": "postgres",
        "redis_enabled": True,
        "cors_origins": ["*"],
        "log_level": "INFO",
    },
    "production": {
        "debug": False,
        "db_backend": "postgres",
        "redis_enabled": True,
        "cors_origins": [],
        "log_level": "WARNING",
    },
}


def get_profile() -> dict:
    env = os.getenv("AURA_ENV", "development").lower()
    return PROFILES.get(env, PROFILES["development"])


def get_env_name() -> str:
    return os.getenv("AURA_ENV", "development").lower()

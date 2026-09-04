"""PostgreSQL configuration helpers."""

import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://aura:aura@database:5432/aura",
)

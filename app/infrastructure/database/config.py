"""Database backend selection and SQL dialect helpers."""

import os
import re

DB_BACKEND = os.getenv("DB_BACKEND", "sqlite").lower()
DATABASE_URL = os.getenv("DATABASE_URL", "")
SQLITE_PATH = os.getenv("SQLITE_PATH", "aura.db")


def is_postgres() -> bool:
    return DB_BACKEND == "postgres" and bool(DATABASE_URL)


def adapt_sql(sql: str) -> str:
    if not is_postgres():
        return sql
    out = sql
    out = re.sub(
        r"INTEGER PRIMARY KEY AUTOINCREMENT",
        "SERIAL PRIMARY KEY",
        out,
        flags=re.IGNORECASE,
    )
    out = out.replace("datetime('now')", "CURRENT_TIMESTAMP")
    out = out.replace("?", "%s")
    return out


def placeholder() -> str:
    return "%s" if is_postgres() else "?"

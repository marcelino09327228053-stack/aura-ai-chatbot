"""Database backend selection and SQL dialect helpers."""

import os
import re

DB_BACKEND = os.getenv("DB_BACKEND", "sqlite").lower()
DATABASE_URL = os.getenv("DATABASE_URL", "")
SQLITE_PATH = os.getenv("SQLITE_PATH", "aura.db")


def is_postgres() -> bool:
    return DB_BACKEND == "postgres" and bool(DATABASE_URL)


def _replace_qmark_placeholders(sql: str) -> str:
    """Replace SQLite ? bind markers outside quoted SQL literals.

    A plain ``str.replace`` also changes question marks inside string
    literals (for example a default welcome message), causing psycopg2 to
    interpret the resulting ``%s`` as a bind placeholder and fail when no
    parameters were supplied.
    """
    result = []
    i = 0
    quote = None
    while i < len(sql):
        ch = sql[i]
        if quote:
            result.append(ch)
            if ch == quote:
                # SQL escapes a quote inside a string by doubling it.
                if i + 1 < len(sql) and sql[i + 1] == quote:
                    result.append(sql[i + 1])
                    i += 1
                else:
                    quote = None
        else:
            if ch in ("'", '"'):
                quote = ch
                result.append(ch)
            elif ch == "?":
                result.append("%s")
            else:
                result.append(ch)
        i += 1
    return "".join(result)


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
    out = _replace_qmark_placeholders(out)
    return out


def placeholder() -> str:
    return "%s" if is_postgres() else "?"

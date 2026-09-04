"""SQLite database backend (development default)."""

import sqlite3

from app.infrastructure.database.compat import CompatConnection
from app.infrastructure.database.config import SQLITE_PATH

_conn = None


def get_connection() -> CompatConnection:
    global _conn
    if _conn is None:
        raw = sqlite3.connect(SQLITE_PATH, check_same_thread=False)
        raw.row_factory = sqlite3.Row
        _conn = CompatConnection(raw)
    return _conn


def column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def table_exists(cursor, table: str) -> bool:
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return cursor.fetchone() is not None

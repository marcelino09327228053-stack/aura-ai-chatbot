"""PostgreSQL database backend (production)."""

from app.infrastructure.database.compat import CompatConnection
from app.infrastructure.database.config import DATABASE_URL

_conn = None


def get_connection() -> CompatConnection:
    global _conn
    if _conn is None:
        import psycopg2
        raw = psycopg2.connect(DATABASE_URL)
        _conn = CompatConnection(raw)
    return _conn


def column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_name = ? AND column_name = ?
        """,
        (table, column),
    )
    return cursor.fetchone() is not None


def table_exists(cursor, table: str) -> bool:
    cursor.execute(
        """
        SELECT 1 FROM information_schema.tables
        WHERE table_name = ?
        """,
        (table,),
    )
    return cursor.fetchone() is not None

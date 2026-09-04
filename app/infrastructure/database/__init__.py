"""Database backend factory."""

from app.infrastructure.database.config import is_postgres


def get_connection():
    if is_postgres():
        from app.infrastructure.database import postgres_backend
        return postgres_backend.get_connection()
    from app.infrastructure.database import sqlite_backend
    return sqlite_backend.get_connection()


def column_exists(cursor, table: str, column: str) -> bool:
    if is_postgres():
        from app.infrastructure.database import postgres_backend
        return postgres_backend.column_exists(cursor, table, column)
    from app.infrastructure.database import sqlite_backend
    return sqlite_backend.column_exists(cursor, table, column)


def table_exists(cursor, table: str) -> bool:
    if is_postgres():
        from app.infrastructure.database import postgres_backend
        return postgres_backend.table_exists(cursor, table)
    from app.infrastructure.database import sqlite_backend
    return sqlite_backend.table_exists(cursor, table)

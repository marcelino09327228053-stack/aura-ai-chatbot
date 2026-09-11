"""Compatible database cursor/connection wrappers for SQLite and PostgreSQL."""

from app.infrastructure.database.config import adapt_sql, is_postgres


class CompatRow(dict):
    """Dict-like row compatible with sqlite3.Row access."""

    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


class CompatCursor:
    def __init__(self, cursor):
        self._cursor = cursor
        self.lastrowid = None

    def execute(self, sql: str, params=()):
        adapted = adapt_sql(sql)
        self._cursor.execute(adapted, params)
        if is_postgres():
            if adapted.strip().upper().startswith("INSERT") and "RETURNING" not in adapted.upper():
                try:
                    self._cursor.execute("SELECT LASTVAL()")
                    row = self._cursor.fetchone()
                    if row:
                        self.lastrowid = next(iter(row.values())) if hasattr(row, "values") else row[0]
                except Exception:
                    self.lastrowid = None
        else:
            self.lastrowid = self._cursor.lastrowid
        return self

    def executemany(self, sql: str, params_seq):
        return self._cursor.executemany(adapt_sql(sql), params_seq)

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        if hasattr(row, "keys"):
            return CompatRow({k: row[k] for k in row.keys()})
        if isinstance(row, (list, tuple)):
            cols = [d[0] for d in self._cursor.description] if self._cursor.description else []
            return CompatRow(dict(zip(cols, row)))
        return CompatRow(dict(row))

    def fetchall(self):
        rows = self._cursor.fetchall()
        result = []
        for row in rows:
            if hasattr(row, "keys"):
                result.append(CompatRow({k: row[k] for k in row.keys()}))
            elif isinstance(row, (list, tuple)):
                cols = [d[0] for d in self._cursor.description] if self._cursor.description else []
                result.append(CompatRow(dict(zip(cols, row))))
            else:
                result.append(CompatRow(dict(row)))
        return result


class CompatConnection:
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        raw = self._conn.cursor()
        if is_postgres():
            from psycopg2.extras import RealDictCursor
            raw = self._conn.cursor(cursor_factory=RealDictCursor)
        return CompatCursor(raw)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        if hasattr(self._conn, "rollback"):
            self._conn.rollback()

    def close(self):
        self._conn.close()

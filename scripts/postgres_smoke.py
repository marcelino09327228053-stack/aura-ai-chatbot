"""Initialize the complete schema against a dedicated PostgreSQL test database."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database.connection import get_connection, init_db


def main() -> None:
    init_db()
    cursor = get_connection().cursor()
    cursor.execute("SELECT 1")
    if cursor.fetchone()[0] != 1:
        raise RuntimeError("PostgreSQL smoke query failed")
    for table in ("users", "companies", "subscriptions", "ai_gateway_requests", "referral_agents"):
        cursor.execute("SELECT 1 FROM information_schema.tables WHERE table_name = ?", (table,))
        if cursor.fetchone() is None:
            raise RuntimeError(f"Missing table: {table}")
    print("PostgreSQL schema smoke test passed.")


if __name__ == "__main__":
    main()

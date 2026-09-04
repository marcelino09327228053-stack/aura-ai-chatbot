"""Cloud marketplace — extensions, ratings, reviews, updates."""

from app.infrastructure.database import get_connection
from app.plugins.marketplace import catalog


def list_extensions() -> list[dict]:
    items = catalog.list_catalog()
    for item in items:
        item["avg_rating"] = get_average_rating(item["plugin_key"])
        item["review_count"] = count_reviews(item["plugin_key"])
        item["latest_version"] = get_latest_version(item["plugin_key"])
    return items


def add_review(
    company_id: int,
    user_id: int,
    extension_key: str,
    rating: int,
    review_text: str,
) -> dict:
    rating = max(1, min(5, rating))
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO marketplace_reviews (company_id, extension_key, user_id, rating, review_text)
        VALUES (?, ?, ?, ?, ?)
        """,
        (company_id, extension_key, user_id, rating, review_text[:1000]),
    )
    conn.commit()
    cursor.execute("SELECT * FROM marketplace_reviews WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_reviews(extension_key: str, limit: int = 20) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT * FROM marketplace_reviews
        WHERE extension_key = ? ORDER BY created_at DESC LIMIT ?
        """,
        (extension_key, limit),
    )
    return [dict(r) for r in cursor.fetchall()]


def get_average_rating(extension_key: str) -> float:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT AVG(rating) FROM marketplace_reviews WHERE extension_key = ?",
        (extension_key,),
    )
    val = cursor.fetchone()[0]
    return round(float(val), 1) if val else 0.0


def count_reviews(extension_key: str) -> int:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM marketplace_reviews WHERE extension_key = ?",
        (extension_key,),
    )
    return cursor.fetchone()[0]


def register_update(extension_key: str, version: str, changelog: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO marketplace_updates (extension_key, version, changelog)
        VALUES (?, ?, ?)
        """,
        (extension_key, version, changelog),
    )
    conn.commit()
    cursor.execute("SELECT * FROM marketplace_updates WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_updates(extension_key: str) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT * FROM marketplace_updates
        WHERE extension_key = ? ORDER BY created_at DESC
        """,
        (extension_key,),
    )
    return [dict(r) for r in cursor.fetchall()]


def get_latest_version(extension_key: str) -> str | None:
    updates = list_updates(extension_key)
    return updates[0]["version"] if updates else None

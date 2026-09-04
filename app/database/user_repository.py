"""User data access."""

import sqlite3

from app.database.connection import get_connection


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "email": row["email"],
        "full_name": row["full_name"],
        "profile_image": row["profile_image"],
        "created_at": row["created_at"],
    }


def create_user(email: str, password_hash: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (email, password_hash) VALUES (?, ?)",
        (email.lower().strip(), password_hash),
    )
    conn.commit()
    return get_user_by_id(cursor.lastrowid)


def get_user_by_id(user_id: int) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT id, email, full_name, profile_image, created_at FROM users WHERE id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    return _row_to_dict(row) if row else None


def get_user_by_email(email: str) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT id, email, full_name, profile_image, password_hash, created_at FROM users WHERE email = ?",
        (email.lower().strip(),),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "email": row["email"],
        "full_name": row["full_name"],
        "profile_image": row["profile_image"],
        "password_hash": row["password_hash"],
        "created_at": row["created_at"],
    }


def count_users() -> int:
    cursor = get_connection().cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    return cursor.fetchone()[0]


def update_password(user_id: int, password_hash: str) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (password_hash, user_id),
    )
    conn.commit()


def update_profile(user_id: int, full_name: str) -> dict | None:
    conn = get_connection()
    conn.cursor().execute(
        "UPDATE users SET full_name = ? WHERE id = ?",
        (full_name.strip(), user_id),
    )
    conn.commit()
    return get_user_by_id(user_id)


def update_email(user_id: int, email: str) -> dict | None:
    conn = get_connection()
    conn.cursor().execute(
        "UPDATE users SET email = ? WHERE id = ?",
        (email.lower().strip(), user_id),
    )
    conn.commit()
    return get_user_by_id(user_id)


def update_profile_image(user_id: int, image_path: str) -> dict | None:
    conn = get_connection()
    conn.cursor().execute(
        "UPDATE users SET profile_image = ? WHERE id = ?",
        (image_path, user_id),
    )
    conn.commit()
    return get_user_by_id(user_id)

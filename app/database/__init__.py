"""Database layer: SQLite connection and repositories."""

from app.database.connection import get_connection, init_db
from app.database.faq_repository import (
    bulk_create_faqs,
    create_faq,
    delete_faq,
    find_faq_answer,
    get_faq,
    list_faqs,
    update_faq,
)

__all__ = [
    "get_connection",
    "init_db",
    "find_faq_answer",
    "list_faqs",
    "get_faq",
    "create_faq",
    "update_faq",
    "delete_faq",
    "bulk_create_faqs",
]

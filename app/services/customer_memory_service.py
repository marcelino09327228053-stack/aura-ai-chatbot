"""Lightweight explicit customer preferences and compact conversation memory."""

from __future__ import annotations

import re

from app.database import memory_repository


PREFERENCE_TYPES = ("preferred_title", "preferred_name", "preferred_language")
LANGUAGE_LABELS = {
    "english": "English",
    "tagalog": "Filipino",
    "filipino": "Filipino",
    "bisaya": "Cebuano/Bisaya",
    "cebuano": "Cebuano/Bisaya",
}


def _clean_contact_key(value: str) -> str:
    return str(value or "default").strip()[:180] or "default"


def get_preferences(company_id: int, contact_key: str) -> dict[str, str]:
    key = _clean_contact_key(contact_key)
    result: dict[str, str] = {}
    for memory_type in PREFERENCE_TYPES:
        item = memory_repository.get_memory(company_id, key, memory_type)
        if item and item.get("content"):
            result[memory_type] = str(item["content"]).strip()
    return result


def update_explicit_preferences(company_id: int, contact_key: str, message: str) -> dict[str, str]:
    """Store only preferences explicitly stated or corrected by the customer."""
    key = _clean_contact_key(contact_key)
    text = " ".join(str(message or "").strip().split())[:1000]
    lowered = text.casefold()

    if re.search(r"(?:kalimutan|forget|huwag.*(?:tawag|gamit)).*(?:sir|ma'am|mam|title)", lowered):
        memory_repository.delete_memory(company_id, key, "preferred_title")
    else:
        title_match = re.search(
            r"\b(?:(sir|mr\.?|mister|ma'am|mam|madam|miss|mrs\.?)\s+(?:ako|po ako)|"
            r"(?:tawagin mo (?:na lang )?akong|call me)\s+(sir|mr\.?|mister|ma'am|mam|madam|miss|mrs\.?))\b",
            text,
            flags=re.IGNORECASE,
        )
        if title_match:
            raw_title = next(group for group in title_match.groups() if group)
            normalized = raw_title.casefold().rstrip(".")
            title = {
                "mr": "Sir", "mister": "Sir", "sir": "Sir",
                "ma'am": "Ma'am", "mam": "Ma'am", "madam": "Ma'am",
                "miss": "Miss", "mrs": "Mrs.",
            }[normalized]
            memory_repository.upsert_memory(company_id, key, "preferred_title", title)

    if re.search(r"(?:kalimutan|forget|huwag.*gamit).*(?:pangalan|name)", lowered):
        memory_repository.delete_memory(company_id, key, "preferred_name")
    else:
        name_match = re.search(
            r"\b(?:ang pangalan ko (?:ay|is)|my name is|call me|tawagin mo (?:na lang )?akong)\s+"
            r"([A-Za-zÀ-ÖØ-öø-ÿ' -]{2,50}?)(?=[.!?](?:\s|$)|$)",
            text,
            flags=re.IGNORECASE,
        )
        if name_match:
            name = " ".join(name_match.group(1).split()).strip()
            if name.casefold() not in {"sir", "mr", "mister", "ma'am", "mam", "madam", "miss", "mrs"}:
                memory_repository.upsert_memory(company_id, key, "preferred_name", name.title())

    if re.search(r"(?:kalimutan|forget|automatic).*(?:language|wika)", lowered):
        memory_repository.delete_memory(company_id, key, "preferred_language")
    else:
        language_match = re.search(
            r"\b(english|tagalog|filipino|bisaya|cebuano)\b(?:\s+(?:na lang|tayo|please))?",
            lowered,
        )
        explicit_language_request = bool(
            language_match
            and re.search(r"(?:mag-|speak|use|gamit|tayo|na lang|reply|sumagot)", lowered)
        )
        if explicit_language_request:
            memory_repository.upsert_memory(
                company_id,
                key,
                "preferred_language",
                LANGUAGE_LABELS[language_match.group(1)],
            )
    return get_preferences(company_id, key)


def get_conversation_summary(company_id: int, contact_key: str) -> str:
    item = memory_repository.get_memory(
        company_id, _clean_contact_key(contact_key), "conversation_summary"
    )
    return str(item.get("content", "")).strip()[:2500] if item else ""


def save_conversation_summary(company_id: int, contact_key: str, summary: str) -> None:
    clean = " ".join(str(summary or "").split())[:2500]
    if clean:
        memory_repository.upsert_memory(
            company_id, _clean_contact_key(contact_key), "conversation_summary", clean
        )


def build_customer_memory_context(preferences: dict[str, str]) -> str:
    lines = []
    if preferences.get("preferred_name"):
        lines.append(f"Preferred customer name: {preferences['preferred_name']}")
    if preferences.get("preferred_title"):
        lines.append(f"Preferred customer title: {preferences['preferred_title']}")
    if preferences.get("preferred_language"):
        lines.append(f"Preferred response language: {preferences['preferred_language']}")
    if not lines:
        return "No explicitly saved customer preferences."
    return "\n".join(lines) + (
        "\nHonor these explicit preferences naturally. Do not repeatedly mention that they "
        "were saved, and never infer additional personal attributes."
    )

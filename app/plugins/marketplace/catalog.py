"""Marketplace catalog of installable plugins."""

from pathlib import Path
import json

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"

_BUILTIN_KEYS = ("email_sender", "sms_sender", "pdf_generator", "inventory_sync")


def _load_manifest(plugin_key: str) -> dict:
    path = EXAMPLES_DIR / plugin_key / "plugin.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def list_catalog() -> list[dict]:
    catalog = []
    for key in _BUILTIN_KEYS:
        try:
            manifest = _load_manifest(key)
            catalog.append({
                "plugin_key": key,
                "name": manifest["name"],
                "version": manifest["version"],
                "author": manifest["author"],
                "description": manifest["description"],
                "permissions": manifest.get("permissions", []),
            })
        except (FileNotFoundError, json.JSONDecodeError):
            continue
    return catalog


def get_catalog_entry(plugin_key: str) -> dict | None:
    if plugin_key not in _BUILTIN_KEYS:
        return None
    try:
        manifest = _load_manifest(plugin_key)
        return {"plugin_key": plugin_key, "manifest": manifest}
    except (FileNotFoundError, json.JSONDecodeError):
        return None

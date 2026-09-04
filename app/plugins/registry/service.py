"""Plugin registry service — register, enable, disable, remove."""

from app.plugins.marketplace import catalog
from app.plugins.registry import repository as plugin_repo
from app.plugins.runtime.loader import load_plugin_class
from app.plugins.runtime.validator import validate_manifest
from app.plugins.sdk.manifest import ALL_PERMISSIONS


def register_plugin(company_id: int, manifest: dict, plugin_key: str | None = None) -> dict:
    validate_manifest(manifest)
    key = plugin_key or manifest["name"].lower().replace(" ", "_")
    existing = plugin_repo.get_plugin_by_key(company_id, key)
    if existing:
        raise ValueError(f"Plugin '{key}' is already installed.")

    for perm in manifest.get("permissions", []):
        if perm not in ALL_PERMISSIONS:
            raise ValueError(f"Unknown permission: {perm}")

    load_plugin_class(key)

    return plugin_repo.create_plugin(
        company_id=company_id,
        plugin_key=key,
        name=manifest["name"],
        version=manifest["version"],
        description=manifest.get("description", ""),
        manifest=manifest,
        enabled=False,
    )


def install_from_marketplace(company_id: int, plugin_key: str) -> dict:
    entry = catalog.get_catalog_entry(plugin_key)
    if not entry:
        raise ValueError(f"Plugin '{plugin_key}' not found in marketplace.")
    return register_plugin(company_id, entry["manifest"], plugin_key=plugin_key)


def enable_plugin(company_id: int, plugin_id: int) -> dict | None:
    plugin = plugin_repo.get_plugin(company_id, plugin_id)
    if not plugin:
        return None
    load_plugin_class(plugin["plugin_key"])
    row = plugin_repo.set_plugin_enabled(company_id, plugin_id, True)
    if row:
        plugin_repo.add_log(company_id, plugin_id, "Plugin enabled", "info")
    return row


def disable_plugin(company_id: int, plugin_id: int) -> dict | None:
    row = plugin_repo.set_plugin_enabled(company_id, plugin_id, False)
    if row:
        plugin_repo.add_log(company_id, plugin_id, "Plugin disabled", "info")
    return row


def remove_plugin(company_id: int, plugin_id: int) -> bool:
    plugin = plugin_repo.get_plugin(company_id, plugin_id)
    if not plugin:
        return False
    plugin_repo.add_log(company_id, plugin_id, "Plugin removed", "info")
    return plugin_repo.delete_plugin(company_id, plugin_id)


def update_settings(company_id: int, plugin_id: int, settings: dict) -> dict | None:
    return plugin_repo.update_plugin_settings(company_id, plugin_id, settings)


def get_dashboard(company_id: int) -> dict:
    installed = plugin_repo.list_plugins(company_id)
    return {
        "installed": installed,
        "marketplace": catalog.list_catalog(),
        "logs": plugin_repo.list_logs(company_id, limit=20),
        "api_keys": plugin_repo.list_api_keys(company_id),
        "available_permissions": ALL_PERMISSIONS,
    }

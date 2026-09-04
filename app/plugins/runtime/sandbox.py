"""Sandboxed plugin execution."""

import traceback

from app.plugins.registry import repository as plugin_repo
from app.plugins.runtime.loader import load_plugin_class
from app.plugins.sdk.context import PluginContext


def run_in_sandbox(
    company_id: int,
    plugin: dict,
    settings: dict | None = None,
    **kwargs,
) -> dict:
    """
    Execute a plugin inside a restricted context.
    Plugins only access data through PluginContext permission checks.
    """
    plugin_id = plugin["id"]
    permissions = plugin["manifest"].get("permissions", [])
    context = PluginContext(company_id, permissions, plugin_id)

    try:
        plugin_cls = load_plugin_class(plugin["plugin_key"])
        instance = plugin_cls()
        merged_settings = {**plugin.get("settings", {}), **(settings or {})}
        result = instance.execute(context, settings=merged_settings, **kwargs)
        plugin_repo.add_log(company_id, plugin_id, "Execution succeeded", "info")
        return {"ok": True, "result": result}
    except PermissionError as exc:
        plugin_repo.add_log(company_id, plugin_id, f"Permission denied: {exc}", "error")
        return {"ok": False, "error": str(exc), "code": "permission_denied"}
    except Exception as exc:
        tb = traceback.format_exc()
        plugin_repo.add_log(company_id, plugin_id, f"Error: {exc}", "error")
        return {"ok": False, "error": str(exc), "code": "execution_error", "trace": tb}

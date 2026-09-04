"""Plugin runtime executor with validation and error handling."""

from app.plugins.registry import repository as plugin_repo
from app.plugins.runtime.sandbox import run_in_sandbox
from app.plugins.runtime.validator import validate_manifest


def execute_plugin(
    company_id: int,
    plugin_id: int,
    settings: dict | None = None,
    **kwargs,
) -> dict:
    plugin = plugin_repo.get_plugin(company_id, plugin_id)
    if not plugin:
        return {"ok": False, "error": "Plugin not found.", "code": "not_found"}

    if not plugin["enabled"]:
        return {"ok": False, "error": "Plugin is disabled.", "code": "disabled"}

    validate_manifest(plugin["manifest"])
    return run_in_sandbox(company_id, plugin, settings=settings, **kwargs)

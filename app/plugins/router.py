"""Plugin platform public API and developer dashboard routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.config import plugins_enabled
from app.core.deps import require_auth
from app.plugins.marketplace import catalog
from app.plugins.registry import repository as plugin_repo
from app.plugins.registry import service as plugin_service
from app.plugins.runtime.executor import execute_plugin
from app.plugins.security import create_company_api_key, require_plugin_api_key

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


class InstallRequest(BaseModel):
    plugin_key: str


class PluginToggle(BaseModel):
    enabled: bool


class PluginSettingsUpdate(BaseModel):
    settings: dict


class ApiKeyCreate(BaseModel):
    name: str


class ExecuteRequest(BaseModel):
    settings: dict | None = None
    params: dict | None = None


def _ensure_plugins_enabled() -> None:
    if not plugins_enabled():
        raise HTTPException(
            status_code=403,
            detail="Plugin platform is disabled. Set PLUGINS_ENABLED=true.",
        )


@router.get("")
def list_plugins(ctx=Depends(require_auth)):
    _ensure_plugins_enabled()
    installed = plugin_repo.list_plugins(ctx.company_id)
    marketplace = catalog.list_catalog()
    return {"installed": installed, "marketplace": marketplace}


@router.post("/install", status_code=201)
def install_plugin(body: InstallRequest, ctx=Depends(require_auth)):
    _ensure_plugins_enabled()
    try:
        return plugin_service.install_from_marketplace(ctx.company_id, body.plugin_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{plugin_id}")
def uninstall_plugin(plugin_id: int, ctx=Depends(require_auth)):
    _ensure_plugins_enabled()
    if not plugin_service.remove_plugin(ctx.company_id, plugin_id):
        raise HTTPException(status_code=404, detail="Plugin not found.")
    return {"ok": True}


@router.put("/{plugin_id}/toggle")
def toggle_plugin(plugin_id: int, body: PluginToggle, ctx=Depends(require_auth)):
    _ensure_plugins_enabled()
    if body.enabled:
        row = plugin_service.enable_plugin(ctx.company_id, plugin_id)
    else:
        row = plugin_service.disable_plugin(ctx.company_id, plugin_id)
    if not row:
        raise HTTPException(status_code=404, detail="Plugin not found.")
    return row


@router.get("/dashboard")
def developer_dashboard(ctx=Depends(require_auth)):
    _ensure_plugins_enabled()
    return plugin_service.get_dashboard(ctx.company_id)


@router.get("/{plugin_id}/logs")
def plugin_logs(plugin_id: int, ctx=Depends(require_auth)):
    _ensure_plugins_enabled()
    plugin = plugin_repo.get_plugin(ctx.company_id, plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found.")
    return plugin_repo.list_logs(ctx.company_id, plugin_id=plugin_id)


@router.get("/{plugin_id}/settings")
def get_plugin_settings(plugin_id: int, ctx=Depends(require_auth)):
    _ensure_plugins_enabled()
    plugin = plugin_repo.get_plugin(ctx.company_id, plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found.")
    return {
        "plugin_id": plugin_id,
        "permissions": plugin["manifest"].get("permissions", []),
        "settings": plugin.get("settings", {}),
    }


@router.put("/{plugin_id}/settings")
def update_plugin_settings(plugin_id: int, body: PluginSettingsUpdate, ctx=Depends(require_auth)):
    _ensure_plugins_enabled()
    row = plugin_service.update_settings(ctx.company_id, plugin_id, body.settings)
    if not row:
        raise HTTPException(status_code=404, detail="Plugin not found.")
    return row


@router.post("/{plugin_id}/execute")
def run_plugin(plugin_id: int, body: ExecuteRequest, ctx=Depends(require_auth)):
    _ensure_plugins_enabled()
    return execute_plugin(
        ctx.company_id,
        plugin_id,
        settings=body.settings,
        **(body.params or {}),
    )


@router.post("/api-keys", status_code=201)
def create_api_key(body: ApiKeyCreate, ctx=Depends(require_auth)):
    _ensure_plugins_enabled()
    return create_company_api_key(ctx.company_id, body.name)


@router.get("/api-keys")
def list_api_keys(ctx=Depends(require_auth)):
    _ensure_plugins_enabled()
    return plugin_repo.list_api_keys(ctx.company_id)


@router.delete("/api-keys/{key_id}")
def revoke_api_key(key_id: int, ctx=Depends(require_auth)):
    _ensure_plugins_enabled()
    if not plugin_repo.revoke_api_key(ctx.company_id, key_id):
        raise HTTPException(status_code=404, detail="API key not found.")
    return {"ok": True}


@router.post("/external/execute/{plugin_id}")
def external_execute(
    plugin_id: int,
    body: ExecuteRequest,
    api_key=Depends(require_plugin_api_key),
):
    _ensure_plugins_enabled()
    if api_key["company_id"] is None:
        raise HTTPException(status_code=403, detail="Invalid API key.")
    return execute_plugin(
        api_key["company_id"],
        plugin_id,
        settings=body.settings,
        **(body.params or {}),
    )

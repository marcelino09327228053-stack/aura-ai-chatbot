"""Synchronization — settings, knowledge, and plugins."""

import json

from app.cloud.security import encrypt_value
from app.database import settings_repository
from app.network import repository as net_repo
from app.os import repository as os_repo
from app.plugins.registry import repository as plugin_repo


def sync_company_settings(company_id: int) -> dict:
    governance = net_repo.get_governance(company_id)
    if governance["network_mode"] == "private":
        return {"synced": False, "reason": "private mode"}

    settings = settings_repository.get_settings(company_id)
    payload = json.dumps(settings)
    encrypted = encrypt_value(payload)
    log = net_repo.log_sync(company_id, "settings", "outbound", "completed", encrypted)
    return {"synced": True, "sync_log": log, "fields": len(settings)}


def sync_knowledge(company_id: int) -> dict:
    governance = net_repo.get_governance(company_id)
    if governance["network_mode"] == "private":
        return {"synced": False, "reason": "private mode"}

    knowledge = os_repo.list_knowledge(company_id, limit=100)
    memories = os_repo.list_long_term_memory(company_id, limit=100)
    summary_count = len(knowledge) + len(memories)

    payload = json.dumps({"knowledge_count": len(knowledge), "memory_count": len(memories)})
    encrypted = encrypt_value(payload)
    log = net_repo.log_sync(company_id, "knowledge", "outbound", "completed", encrypted)

    if governance["network_mode"] == "enterprise":
        net_repo.share_resource("knowledge", f"company_{company_id}", company_id)

    return {"synced": True, "items": summary_count, "sync_log": log}


def sync_plugins(company_id: int) -> dict:
    governance = net_repo.get_governance(company_id)
    if governance["network_mode"] == "private":
        return {"synced": False, "reason": "private mode"}

    plugins = plugin_repo.list_plugins(company_id)
    payload = json.dumps([{"key": p["plugin_key"], "version": p["version"]} for p in plugins])
    encrypted = encrypt_value(payload)
    log = net_repo.log_sync(company_id, "plugins", "outbound", "completed", encrypted)

    for p in plugins:
        if governance["network_mode"] == "enterprise":
            net_repo.share_resource("plugin", p["plugin_key"], company_id)

    return {"synced": True, "plugins": len(plugins), "sync_log": log}


def sync_all(company_id: int) -> dict:
    return {
        "settings": sync_company_settings(company_id),
        "knowledge": sync_knowledge(company_id),
        "plugins": sync_plugins(company_id),
    }

"""Infrastructure manager — servers, databases, networks, monitoring, backups."""

from __future__ import annotations

from app.civilization import repository as civ_repo

DEFAULT_NODES = [
    ("server", "api-primary", {"cpu_pct": 32, "mem_pct": 48, "uptime_hrs": 720}),
    ("server", "api-worker", {"cpu_pct": 28, "mem_pct": 41, "uptime_hrs": 680}),
    ("database", "postgres-main", {"connections": 42, "disk_pct": 55, "replication": "ok"}),
    ("database", "redis-cache", {"hit_rate": 0.92, "memory_mb": 256}),
    ("network", "edge-gateway", {"latency_ms": 18, "throughput_mbps": 850}),
    ("network", "internal-mesh", {"latency_ms": 4, "packet_loss_pct": 0.01}),
    ("monitor", "metrics-collector", {"scrapes_per_min": 120, "alerts_open": 0}),
]


def bootstrap_infrastructure(company_id: int) -> list[dict]:
    existing = civ_repo.list_infra_nodes(company_id)
    if existing:
        return existing
    nodes = []
    for node_type, name, metrics in DEFAULT_NODES:
        status = "healthy"
        if metrics.get("cpu_pct", 0) > 80 or metrics.get("disk_pct", 0) > 85:
            status = "degraded"
        nodes.append(civ_repo.upsert_infra_node(
            company_id, node_type, name, status, metrics,
            config={"managed": True, "auto_scale": node_type == "server"},
        ))
    civ_repo.log_civ_action(company_id, "infra.bootstrap", details=f"{len(nodes)} nodes")
    return nodes


def refresh_monitoring(company_id: int) -> dict:
    nodes = bootstrap_infrastructure(company_id)
    healthy = [n for n in nodes if n.get("status") == "healthy"]
    degraded = [n for n in nodes if n.get("status") != "healthy"]
    by_type: dict[str, int] = {}
    for n in nodes:
        t = n.get("node_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    return {
        "nodes": nodes,
        "by_type": by_type,
        "healthy": len(healthy),
        "degraded": len(degraded),
        "health_score": round(len(healthy) / max(len(nodes), 1), 2),
    }


def run_backup(company_id: int, backup_type: str = "full") -> dict:
    size = 120 + (hash(str(company_id) + backup_type) % 80)
    backup = civ_repo.create_backup(
        company_id,
        backup_type,
        f"s3://aura-civ-backups/{company_id}/{backup_type}",
        float(size),
    )
    civ_repo.log_civ_action(company_id, "infra.backup", details=backup_type)
    return backup


def infrastructure_summary(company_id: int) -> dict:
    monitoring = refresh_monitoring(company_id)
    backups = civ_repo.list_backups(company_id)
    return {
        **monitoring,
        "backups": backups[:10],
        "backup_count": len(backups),
        "modules": {
            "servers": monitoring["by_type"].get("server", 0),
            "databases": monitoring["by_type"].get("database", 0),
            "networks": monitoring["by_type"].get("network", 0),
            "monitors": monitoring["by_type"].get("monitor", 0),
        },
    }

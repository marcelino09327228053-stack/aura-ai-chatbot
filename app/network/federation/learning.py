"""Federated learning — local training, global improvements without raw data sharing."""

import hashlib
import json

from app.network import repository as net_repo


def local_train(company_id: int, model_key: str, local_metrics: dict) -> dict:
    """Simulate local training; only gradient hash is shared, not raw data."""
    governance = net_repo.get_governance(company_id)
    if governance["network_mode"] == "private":
        return {"trained": False, "reason": "private mode — no federation"}

    gradient_payload = json.dumps({
        "company_id": company_id,
        "model_key": model_key,
        "metrics": local_metrics,
        "sample_count": local_metrics.get("samples", 0),
    })
    gradient_hash = hashlib.sha256(gradient_payload.encode()).hexdigest()
    score = local_metrics.get("accuracy", 0.0)

    update = net_repo.record_federated_update(model_key, gradient_hash, score)
    net_repo.log_sync(company_id, "federated_learning", "outbound", "completed", gradient_hash)
    return {
        "trained": True,
        "gradient_hash": gradient_hash,
        "update": update,
        "note": "Only gradient hash shared — private data stays local.",
    }


def aggregate_global_improvements(model_key: str | None = None) -> dict:
    updates = net_repo.list_federated_updates(model_key)
    if not updates:
        return {"model_key": model_key, "contributors": 0, "avg_score": 0.0}

    scores = [u["improvement_score"] for u in updates]
    return {
        "model_key": model_key or "all",
        "contributors": sum(u["contributor_count"] for u in updates),
        "update_count": len(updates),
        "avg_improvement_score": round(sum(scores) / len(scores), 3),
        "latest": updates[0] if updates else None,
    }

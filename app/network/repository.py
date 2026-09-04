"""Network data access."""

import hashlib
import json
import secrets
import uuid

from app.infrastructure.database import get_connection

LOCAL_NODE_ID = None


def get_local_node_id() -> str:
    global LOCAL_NODE_ID
    if LOCAL_NODE_ID is None:
        LOCAL_NODE_ID = str(uuid.uuid4())[:12]
    return LOCAL_NODE_ID


def ensure_local_node(name: str = "Aura Local") -> dict:
    node_id = get_local_node_id()
    cursor = get_connection().cursor()
    cursor.execute("SELECT * FROM network_nodes WHERE node_id = ?", (node_id,))
    row = cursor.fetchone()
    if row:
        return dict(row)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO network_nodes (node_id, name, instance_url, status)
        VALUES (?, ?, '', 'active')
        """,
        (node_id, name),
    )
    conn.commit()
    cursor.execute("SELECT * FROM network_nodes WHERE node_id = ?", (node_id,))
    return dict(cursor.fetchone())


def list_nodes() -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute("SELECT * FROM network_nodes ORDER BY created_at ASC")
    return [dict(r) for r in cursor.fetchall()]


def register_remote_node(node_id: str, name: str, instance_url: str = "") -> dict:
    cursor = get_connection().cursor()
    cursor.execute("SELECT * FROM network_nodes WHERE node_id = ?", (node_id,))
    row = cursor.fetchone()
    if row:
        return dict(row)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO network_nodes (node_id, name, instance_url, status)
        VALUES (?, ?, ?, 'active')
        """,
        (node_id, name, instance_url),
    )
    conn.commit()
    cursor.execute("SELECT * FROM network_nodes WHERE node_id = ?", (node_id,))
    return dict(cursor.fetchone())


def join_network(
    company_id: int,
    network_mode: str = "shared",
    node_id: str | None = None,
) -> dict:
    node_id = node_id or get_local_node_id()
    ensure_local_node()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM network_memberships WHERE company_id = ? AND left_at IS NULL",
        (company_id,),
    )
    existing = cursor.fetchone()
    if existing:
        return dict(existing)
    cursor.execute(
        """
        INSERT INTO network_memberships (company_id, node_id, network_mode)
        VALUES (?, ?, ?)
        """,
        (company_id, node_id, network_mode),
    )
    conn.commit()
    set_governance(company_id, network_mode)
    cursor.execute(
        "SELECT * FROM network_memberships WHERE company_id = ? AND left_at IS NULL",
        (company_id,),
    )
    return dict(cursor.fetchone())


def leave_network(company_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE network_memberships SET left_at = datetime('now')
        WHERE company_id = ? AND left_at IS NULL
        """,
        (company_id,),
    )
    conn.commit()
    set_governance(company_id, "private")
    return True


def get_membership(company_id: int) -> dict | None:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM network_memberships WHERE company_id = ? AND left_at IS NULL",
        (company_id,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def list_members() -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        "SELECT * FROM network_memberships WHERE left_at IS NULL ORDER BY joined_at ASC"
    )
    return [dict(r) for r in cursor.fetchall()]


def set_governance(company_id: int, network_mode: str, policies: dict | None = None) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO network_governance (company_id, network_mode, policies_json)
        VALUES (?, ?, ?)
        ON CONFLICT(company_id) DO UPDATE SET
            network_mode = excluded.network_mode,
            policies_json = excluded.policies_json,
            updated_at = datetime('now')
        """,
        (company_id, network_mode, json.dumps(policies or {})),
    )
    conn.commit()
    return get_governance(company_id)


def get_governance(company_id: int) -> dict:
    cursor = get_connection().cursor()
    cursor.execute("SELECT * FROM network_governance WHERE company_id = ?", (company_id,))
    row = cursor.fetchone()
    if not row:
        return {"company_id": company_id, "network_mode": "private", "policies": {}}
    data = dict(row)
    data["policies"] = json.loads(data.pop("policies_json", "{}") or "{}")
    return data


def log_sync(
    company_id: int,
    sync_type: str,
    direction: str,
    status: str,
    payload: str = "",
) -> dict:
    payload_hash = hashlib.sha256(payload.encode()).hexdigest()[:32]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO network_sync_log (company_id, sync_type, direction, status, payload_hash)
        VALUES (?, ?, ?, ?, ?)
        """,
        (company_id, sync_type, direction, status, payload_hash),
    )
    conn.commit()
    cursor.execute("SELECT * FROM network_sync_log WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_sync_log(company_id: int | None = None, limit: int = 50) -> list[dict]:
    cursor = get_connection().cursor()
    if company_id:
        cursor.execute(
            """
            SELECT * FROM network_sync_log WHERE company_id = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (company_id, limit),
        )
    else:
        cursor.execute(
            "SELECT * FROM network_sync_log ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
    return [dict(r) for r in cursor.fetchall()]


def record_federated_update(model_key: str, gradient_hash: str, score: float = 0.0) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM network_federated_updates WHERE model_key = ?",
        (model_key,),
    )
    count = cursor.fetchone()[0] + 1
    cursor.execute(
        """
        INSERT INTO network_federated_updates (model_key, gradient_hash, contributor_count, improvement_score)
        VALUES (?, ?, ?, ?)
        """,
        (model_key, gradient_hash, count, score),
    )
    conn.commit()
    cursor.execute("SELECT * FROM network_federated_updates WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_federated_updates(model_key: str | None = None, limit: int = 20) -> list[dict]:
    cursor = get_connection().cursor()
    if model_key:
        cursor.execute(
            """
            SELECT * FROM network_federated_updates WHERE model_key = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (model_key, limit),
        )
    else:
        cursor.execute(
            "SELECT * FROM network_federated_updates ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
    return [dict(r) for r in cursor.fetchall()]


def log_agent_run(
    company_id: int,
    agent_type: str,
    execution_mode: str,
    status: str,
    result_preview: str = "",
) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO network_agent_runs (company_id, agent_type, execution_mode, status, result_preview)
        VALUES (?, ?, ?, ?, ?)
        """,
        (company_id, agent_type, execution_mode, status, result_preview[:500]),
    )
    conn.commit()
    cursor.execute("SELECT * FROM network_agent_runs WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_agent_runs(company_id: int | None = None, limit: int = 50) -> list[dict]:
    cursor = get_connection().cursor()
    if company_id:
        cursor.execute(
            """
            SELECT * FROM network_agent_runs WHERE company_id = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (company_id, limit),
        )
    else:
        cursor.execute(
            "SELECT * FROM network_agent_runs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
    return [dict(r) for r in cursor.fetchall()]


def share_resource(resource_type: str, resource_key: str, owner_company_id: int) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO network_shared_resources (resource_type, resource_key, owner_company_id, shared)
        VALUES (?, ?, ?, 1)
        """,
        (resource_type, resource_key, owner_company_id),
    )
    conn.commit()
    cursor.execute("SELECT * FROM network_shared_resources WHERE id = ?", (cursor.lastrowid,))
    return dict(cursor.fetchone())


def list_shared_resources(resource_type: str | None = None) -> list[dict]:
    cursor = get_connection().cursor()
    if resource_type:
        cursor.execute(
            """
            SELECT * FROM network_shared_resources
            WHERE shared = 1 AND resource_type = ?
            ORDER BY created_at DESC
            """,
            (resource_type,),
        )
    else:
        cursor.execute(
            "SELECT * FROM network_shared_resources WHERE shared = 1 ORDER BY created_at DESC"
        )
    return [dict(r) for r in cursor.fetchall()]

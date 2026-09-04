"""Intelligence platform data access."""

import json

from app.cloud.security import encrypt_value
from app.infrastructure.database import get_connection


def save_prediction(
    company_id: int,
    prediction_type: str,
    value: float,
    confidence: float,
    period: str = "monthly",
) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO intelligence_predictions
            (company_id, prediction_type, value, confidence, period)
        VALUES (?, ?, ?, ?, ?)
        """,
        (company_id, prediction_type, value, confidence, period),
    )
    conn.commit()
    cursor.execute(
        "SELECT * FROM intelligence_predictions WHERE id = ?",
        (cursor.lastrowid,),
    )
    return dict(cursor.fetchone())


def list_predictions(
    company_id: int,
    prediction_type: str | None = None,
    limit: int = 20,
) -> list[dict]:
    cursor = get_connection().cursor()
    if prediction_type:
        cursor.execute(
            """
            SELECT * FROM intelligence_predictions
            WHERE company_id = ? AND prediction_type = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (company_id, prediction_type, limit),
        )
    else:
        cursor.execute(
            """
            SELECT * FROM intelligence_predictions
            WHERE company_id = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (company_id, limit),
        )
    return [dict(r) for r in cursor.fetchall()]


def save_recommendation(
    company_id: int,
    category: str,
    title: str,
    description: str,
    impact_score: float = 0.0,
) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO intelligence_recommendations
            (company_id, category, title, description, impact_score)
        VALUES (?, ?, ?, ?, ?)
        """,
        (company_id, category, title, description[:2000], impact_score),
    )
    conn.commit()
    cursor.execute(
        "SELECT * FROM intelligence_recommendations WHERE id = ?",
        (cursor.lastrowid,),
    )
    return dict(cursor.fetchone())


def list_recommendations(
    company_id: int,
    category: str | None = None,
    limit: int = 20,
) -> list[dict]:
    cursor = get_connection().cursor()
    if category:
        cursor.execute(
            """
            SELECT * FROM intelligence_recommendations
            WHERE company_id = ? AND category = ?
            ORDER BY impact_score DESC, created_at DESC LIMIT ?
            """,
            (company_id, category, limit),
        )
    else:
        cursor.execute(
            """
            SELECT * FROM intelligence_recommendations
            WHERE company_id = ?
            ORDER BY impact_score DESC, created_at DESC LIMIT ?
            """,
            (company_id, limit),
        )
    return [dict(r) for r in cursor.fetchall()]


def save_simulation(
    company_id: int,
    scenario_type: str,
    parameters: dict,
    result: dict,
) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    params_enc = encrypt_value(json.dumps(parameters))
    cursor.execute(
        """
        INSERT INTO intelligence_simulations
            (company_id, scenario_type, parameters, result)
        VALUES (?, ?, ?, ?)
        """,
        (company_id, scenario_type, params_enc, json.dumps(result)),
    )
    conn.commit()
    cursor.execute(
        "SELECT * FROM intelligence_simulations WHERE id = ?",
        (cursor.lastrowid,),
    )
    row = dict(cursor.fetchone())
    row["parameters"] = parameters
    row["result"] = result
    return row


def list_simulations(company_id: int, limit: int = 10) -> list[dict]:
    cursor = get_connection().cursor()
    cursor.execute(
        """
        SELECT * FROM intelligence_simulations
        WHERE company_id = ?
        ORDER BY created_at DESC LIMIT ?
        """,
        (company_id, limit),
    )
    rows = []
    for r in cursor.fetchall():
        data = dict(r)
        try:
            data["result"] = json.loads(data.get("result") or "{}")
        except Exception:
            data["result"] = {}
        data.pop("parameters", None)
        rows.append(data)
    return rows


def log_intelligence_action(company_id: int, action: str, details: str = "") -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO intelligence_audit (company_id, action, details)
        VALUES (?, ?, ?)
        """,
        (company_id, action, details[:500]),
    )
    conn.commit()

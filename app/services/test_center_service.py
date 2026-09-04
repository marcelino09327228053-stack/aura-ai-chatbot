"""Authenticated development/staging diagnostics for the web Test Center."""
import os
from pathlib import Path
import subprocess
import sys

from fastapi import HTTPException
from app.core.config import get_aura_env
from app.database.connection import get_connection
from app.infrastructure.redis.client import is_redis_available
from app.services import ai_service, subscription_service
from app.services.ai_observability import metrics_snapshot
from app.services.ai_provider_router import provider_health

ROOT = Path(__file__).resolve().parents[2]

def ensure_available():
    if get_aura_env() == "production":
        raise HTTPException(status_code=404, detail="Test Center is disabled in production.")

def diagnostics(company_id: int) -> dict:
    ensure_available()
    database_ok = True
    try: get_connection().cursor().execute("SELECT 1")
    except Exception: database_ok = False
    providers = [{"id": key, "configured": bool(os.getenv(value["key_env"], "").strip()),
                  "model": ai_service.get_server_model(key)} for key, value in ai_service.PROVIDERS.items()]
    return {"environment": get_aura_env(), "database": "ok" if database_ok else "error",
            "redis": is_redis_available(), "subscription": subscription_service.get_subscription_status(company_id),
            "providers": providers, "provider_health": provider_health.snapshot(), "metrics": metrics_snapshot()}

def _run(command: list[str], timeout: int) -> dict:
    try:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                timeout=timeout, encoding="utf-8", errors="replace")
        output = ((result.stdout or "") + (result.stderr or ""))[-20000:]
        return {"passed": result.returncode == 0, "exit_code": result.returncode, "output": output}
    except subprocess.TimeoutExpired:
        return {"passed": False, "exit_code": None, "output": "Test timed out."}

def run_automated_tests() -> dict:
    ensure_available()
    return _run([sys.executable, str(ROOT / "scripts" / "run_all_tests.py")], 180)

def run_live_provider_test(confirm_billable: bool) -> dict:
    ensure_available()
    if not confirm_billable:
        raise HTTPException(status_code=400, detail="Billable provider test confirmation is required.")
    return _run([sys.executable, str(ROOT / "scripts" / "check_ai_providers.py")], 180)

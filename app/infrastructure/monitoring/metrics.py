"""System monitoring — CPU, memory, API usage, error logs."""

import os
import time
from datetime import datetime, timezone
from pathlib import Path

from app.database import usage_repository
from app.infrastructure.database.config import DB_BACKEND, is_postgres

_error_buffer: list[dict] = []
_request_count = 0
_start_time = time.time()

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


def record_request() -> None:
    global _request_count
    _request_count += 1


def record_error(message: str, path: str = "", status_code: int = 500) -> None:
    entry = {
        "message": message[:500],
        "path": path,
        "status_code": status_code,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _error_buffer.append(entry)
    if len(_error_buffer) > 200:
        _error_buffer.pop(0)
    _write_error_log(entry)


def _write_error_log(entry: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / "errors.log"
    line = f"{entry['created_at']} [{entry['status_code']}] {entry['path']} {entry['message']}\n"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line)


def get_cpu_usage() -> float:
    try:
        import psutil
        return psutil.cpu_percent(interval=0.1)
    except Exception:
        return 0.0


def get_memory_usage() -> dict:
    try:
        import psutil
        mem = psutil.virtual_memory()
        return {
            "percent": mem.percent,
            "used_mb": round(mem.used / (1024 * 1024), 1),
            "total_mb": round(mem.total / (1024 * 1024), 1),
        }
    except Exception:
        return {"percent": 0.0, "used_mb": 0.0, "total_mb": 0.0}


def get_metrics(company_id: int | None = None) -> dict:
    uptime = round(time.time() - _start_time)
    api_usage = {
        "total_requests": _request_count,
        "messages_today": usage_repository.count_messages_today(company_id) if company_id else 0,
    }
    return {
        "uptime_seconds": uptime,
        "cpu_percent": get_cpu_usage(),
        "memory": get_memory_usage(),
        "api_usage": api_usage,
        "database_backend": "postgresql" if is_postgres() else "sqlite",
        "db_backend_env": DB_BACKEND,
        "error_count": len(_error_buffer),
        "recent_errors": list(reversed(_error_buffer[-20:])),
    }


def list_error_logs(limit: int = 50) -> list[dict]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / "errors.log"
    if not log_file.exists():
        return list(reversed(_error_buffer[-limit:]))
    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    return [{"line": line} for line in lines[-limit:]]

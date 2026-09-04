"""Database backup and restore."""

import shutil
from datetime import datetime, timezone
from pathlib import Path

from app.infrastructure.database.config import SQLITE_PATH, is_postgres

BACKUP_DIR = Path(__file__).resolve().parent / "storage"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def create_sqlite_backup(label: str = "manual") -> dict:
    src = Path(SQLITE_PATH)
    if not src.exists():
        return {"ok": False, "error": "SQLite database file not found."}
    dest = BACKUP_DIR / f"sqlite_{label}_{_timestamp()}.db"
    shutil.copy2(src, dest)
    return {"ok": True, "path": str(dest), "size_bytes": dest.stat().st_size}


def create_postgres_backup(label: str = "manual") -> dict:
    import os
    import subprocess

    url = os.getenv("DATABASE_URL", "")
    if not url:
        return {"ok": False, "error": "DATABASE_URL not set."}
    dest = BACKUP_DIR / f"postgres_{label}_{_timestamp()}.sql"
    try:
        subprocess.run(
            ["pg_dump", url, "-f", str(dest)],
            check=True,
            capture_output=True,
        )
        return {"ok": True, "path": str(dest), "size_bytes": dest.stat().st_size}
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        return {"ok": False, "error": str(exc)}


def run_backup(label: str = "manual") -> dict:
    if is_postgres():
        return create_postgres_backup(label)
    return create_sqlite_backup(label)


def run_daily_backup() -> dict:
    return run_backup("daily")


def run_weekly_backup() -> dict:
    return run_backup("weekly")


def list_backups() -> list[dict]:
    files = []
    for path in sorted(BACKUP_DIR.glob("*"), reverse=True):
        if path.is_file():
            files.append({
                "name": path.name,
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "created_at": datetime.fromtimestamp(
                    path.stat().st_mtime, tz=timezone.utc
                ).isoformat(),
            })
    return files


def restore_sqlite(backup_name: str) -> dict:
    src = BACKUP_DIR / backup_name
    if not src.exists() or not backup_name.endswith(".db"):
        return {"ok": False, "error": "Backup not found or invalid type."}
    dest = Path(SQLITE_PATH)
    shutil.copy2(src, dest)
    return {"ok": True, "restored_to": str(dest)}


def restore_backup(backup_name: str) -> dict:
    if backup_name.endswith(".db"):
        return restore_sqlite(backup_name)
    return {"ok": False, "error": "PostgreSQL restore: run psql -f <backup.sql> manually."}

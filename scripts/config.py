"""Shared config — load from environment / .env (never commit secrets)."""
from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


EBS_DB_DSN = os.environ.get("EBS_DB_DSN", "10.20.30.40:1521/PRODCDB")
APPS_USER = os.environ.get("APPS_USER", "APPS")
APPS_PWD = os.environ.get("APPS_PWD")  # set in .env locally
PROD_APPS_SSH = os.environ.get("PROD_APPS_SSH", "oracle@10.20.30.41")
EBS_APPS_ENV = os.environ.get(
    "EBS_APPS_ENV", "/u01/oracle/EBS/R12211/EBSapps.env"
)
WEBLOGIC_ADMIN_PASSWORD = os.environ.get("WEBLOGIC_ADMIN_PASSWORD", "")
ORACLE_CLIENT_LIB = os.environ.get(
    "ORACLE_CLIENT_LIB", r"C:\oracle\instantclient_21_3"
)
WFMLR_QUEUE_ID = os.environ.get("WFMLR_QUEUE_ID", "1140")
MONITOR_SINCE = os.environ.get("MONITOR_SINCE", "2026-08-25 16:21:00")
POISON_NOTIFICATION_ID = int(os.environ.get("POISON_NOTIFICATION_ID", "2103324"))

BACKUP_ROOT = Path(__file__).resolve().parents[1] / "backups"

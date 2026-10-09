#!/usr/bin/env python3
"""Restart WFMLRSVC Java container on Apps tier; verify PID changed."""
from __future__ import annotations

import subprocess
import time

from config import PROD_APPS_SSH, WFMLR_QUEUE_ID

PS = (
    "ps -eo pid,args | "
    f"awk '/[c]onc_queue_id={WFMLR_QUEUE_ID}/ && /GSMSvcComponentContainer/ "
    "{print $1; exit}'"
)


def ssh(command: str) -> str:
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12", PROD_APPS_SSH, command],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"ssh exit {result.returncode}")
    return result.stdout.strip()


old_pid = ssh(PS)
if not old_pid.isdigit():
    raise SystemExit(f"ABORT invalid old PID: {old_pid!r}")
print("OLD_PID", old_pid, flush=True)
ssh(f"kill -TERM {old_pid}")

for attempt in range(60):
    time.sleep(5)
    new_pid = ssh(PS)
    if new_pid.isdigit() and new_pid != old_pid:
        print("NEW_PID", new_pid, flush=True)
        print(ssh(f"ps -p {new_pid} -o pid,lstart,args"), flush=True)
        print("WFMLRSVC_JVM_RESTARTED", flush=True)
        break
    if (attempt + 1) % 6 == 0:
        print(f"WAIT_{(attempt + 1) * 5}s pid={new_pid or 'none'}", flush=True)
else:
    raise SystemExit("ABORT no replacement JVM after 300s")

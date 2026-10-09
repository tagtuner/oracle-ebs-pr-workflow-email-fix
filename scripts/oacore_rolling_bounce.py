#!/usr/bin/env python3
"""Rolling OACore bounce on Apps tier (4 managed servers)."""
from __future__ import annotations

import subprocess

from config import EBS_APPS_ENV, PROD_APPS_SSH, WEBLOGIC_ADMIN_PASSWORD

SCRIPT = rf"""
source {EBS_APPS_ENV} run
WLP={WEBLOGIC_ADMIN_PASSWORD!r}
LOG=/tmp/oacore_rolling_bounce_$(date +%Y%m%d_%H%M%S).log
exec > >(tee -a "$LOG") 2>&1
echo "=== OACore rolling bounce start $(date) ==="
for s in oacore_server1 oacore_server2 oacore_server3 oacore_server4; do
  echo "STOP $s"
  echo "$WLP" | "$ADMIN_SCRIPTS_HOME/admanagedsrvctl.sh" stop "$s" -nopromptmsg || true
  sleep 15
  echo "START $s"
  echo "$WLP" | "$ADMIN_SCRIPTS_HOME/admanagedsrvctl.sh" start "$s" -nopromptmsg || true
  sleep 30
done
echo "JVM count:" $(ps -ef | grep weblogic.Name=oacore | grep -v grep | wc -l)
ss -lnt | grep 8000 || netstat -lnt | grep 8000 || true
echo "=== DONE log=$LOG $(date) ==="
"""

res = subprocess.run(
    ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12", PROD_APPS_SSH, SCRIPT],
    capture_output=True,
    text=True,
    timeout=1200,
)
print(res.stdout)
if res.stderr:
    print("stderr:", res.stderr[-3000:])
print("exit:", res.returncode)

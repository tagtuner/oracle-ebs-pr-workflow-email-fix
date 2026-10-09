#!/usr/bin/env python3
"""Read-only: Workflow Notification Mailer component status (no secrets printed)."""
from __future__ import annotations

import os
import sys

import oracledb

COMPONENT_ID = int(os.environ.get("WF_MAILER_COMPONENT_ID", "10006"))
DSN = os.environ["EBS_DB_DSN"]
APPS_USER = os.environ.get("APPS_USER", "APPS")
APPS_PWD = os.environ["APPS_PWD"]
ORACLE_CLIENT_LIB = os.environ.get("ORACLE_CLIENT_LIB", "")

INTERESTING = (
    "OUTBOUND_PASSWORD",
    "INBOUND_PASSWORD",
    "OUTBOUND_SECURE_PROTOCOL",
    "OUTBOUND_AUTH_TYPE",
    "OUTBOUND_SERVER",
    "OUTBOUND_USER",
    "PROCESSOR_IN_THREAD_COUNT",
    "MAILER_SSL_TRUSTSTORE",
)


def classify(name: str, val) -> str:
    s = "" if val is None else str(val)
    if "PASSWORD" in name.upper():
        if s.startswith("V1:"):
            return "V1_ENCRYPTED"
        if not s:
            return "EMPTY"
        return f"PLAIN_LEN_{len(s)}"
    if "USER" in name.upper() or "ACCOUNT" in name.upper() or "SERVER" in name.upper():
        return f"SET_LEN_{len(s)}"
    if name == "OUTBOUND_SECURE_PROTOCOL":
        return s or "EMPTY"
    if name == "OUTBOUND_AUTH_TYPE":
        return s or "EMPTY"
    return f"LEN_{len(s)}"


def main() -> int:
    if ORACLE_CLIENT_LIB:
        oracledb.init_oracle_client(lib_dir=ORACLE_CLIENT_LIB)
    conn = oracledb.connect(user=APPS_USER, password=APPS_PWD, dsn=DSN)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT component_status,
               TO_CHAR(last_update_date,'DD-MON HH24:MI:SS'),
               SUBSTR(NVL(component_status_info,' '),1,120)
          FROM apps.fnd_svc_components WHERE component_id=:c
        """,
        c=COMPONENT_ID,
    )
    st, upd, info = cur.fetchone()
    print(f"status {st} upd {upd}")
    print("info", (info or "").strip()[:80])
    cur.execute(
        """
        SELECT p.parameter_name, TO_CHAR(v.parameter_value)
          FROM apps.fnd_svc_comp_param_vals v
          JOIN apps.fnd_svc_comp_params_b p ON p.parameter_id=v.parameter_id
         WHERE v.component_id=:c
           AND p.parameter_name IN ({names})
         ORDER BY 1
        """.format(
            names=",".join(f"'{n}'" for n in INTERESTING)
        ),
        c=COMPONENT_ID,
    )
    for name, val in cur.fetchall():
        print((name, classify(name, val)))
    cur.close()
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

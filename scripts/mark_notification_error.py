#!/usr/bin/env python3
"""Move a single stuck OPEN/MAIL notification to ERROR (surgical queue cleanup)."""
from __future__ import annotations

import oracledb

from config import APPS_PWD, APPS_USER, EBS_DB_DSN, ORACLE_CLIENT_LIB, POISON_NOTIFICATION_ID, require_env

oracledb.init_oracle_client(lib_dir=ORACLE_CLIENT_LIB)
conn = oracledb.connect(user=APPS_USER, password=require_env("APPS_PWD"), dsn=EBS_DB_DSN)
cur = conn.cursor()
nid = POISON_NOTIFICATION_ID

cur.execute(
    """
    SELECT notification_id, message_type, message_name, recipient_role,
           status, mail_status, subject
      FROM apps.wf_notifications
     WHERE notification_id=:nid
    """,
    nid=nid,
)
print("BEFORE", cur.fetchone())
cur.execute(
    """
    UPDATE apps.wf_notifications
       SET mail_status='ERROR'
     WHERE notification_id=:nid
       AND status='OPEN'
       AND mail_status='MAIL'
    """,
    nid=nid,
)
print("UPDATED", cur.rowcount)
if cur.rowcount != 1:
    conn.rollback()
    raise SystemExit("ABORT: notification not OPEN/MAIL")
conn.commit()
cur.execute(
    "SELECT notification_id, status, mail_status "
    "FROM apps.wf_notifications WHERE notification_id=:nid",
    nid=nid,
)
print("AFTER", cur.fetchone())
conn.close()
print("MARK_ERROR_OK")

#!/usr/bin/env python3
"""Read-only: mailer component, params, and OPEN notification queue."""
from __future__ import annotations

import oracledb

from config import APPS_PWD, APPS_USER, EBS_DB_DSN, ORACLE_CLIENT_LIB, require_env

oracledb.init_oracle_client(lib_dir=ORACLE_CLIENT_LIB)
conn = oracledb.connect(user=APPS_USER, password=require_env("APPS_PWD"), dsn=EBS_DB_DSN)
cur = conn.cursor()

cur.execute(
    """
    SELECT c.component_id, c.component_name, c.component_status,
           c.concurrent_queue_id, c.startup_mode
      FROM apps.fnd_svc_components c
     WHERE c.component_type='WF_MAILER'
    """
)
print("COMP")
for row in cur.fetchall():
    print(row)

cur.execute(
    """
    SELECT COUNT(*), mail_status FROM apps.wf_notifications
     WHERE status='OPEN' AND mail_status IN ('MAIL','ERROR','FAILED')
     GROUP BY mail_status
    """
)
print("QUEUE_COUNTS")
for row in cur.fetchall():
    print(row)

cur.execute(
    """
    SELECT notification_id, recipient_role, status, mail_status,
           TO_CHAR(begin_date,'YYYY-MM-DD HH24:MI:SS'),
           SUBSTR(subject,1,100)
      FROM apps.wf_notifications
     WHERE status='OPEN' AND mail_status='MAIL'
     ORDER BY begin_date
    """
)
print("MAIL_QUEUE_ITEMS")
for row in cur.fetchall():
    print(row)

conn.close()

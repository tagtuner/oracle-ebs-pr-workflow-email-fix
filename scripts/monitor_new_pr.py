#!/usr/bin/env python3
"""Monitor new PO_REQ_APPROVE_JRAD notifications after a timestamp."""
from __future__ import annotations

import oracledb

from config import APPS_PWD, APPS_USER, EBS_DB_DSN, MONITOR_SINCE, ORACLE_CLIENT_LIB, require_env

oracledb.init_oracle_client(lib_dir=ORACLE_CLIENT_LIB)
conn = oracledb.connect(user=APPS_USER, password=require_env("APPS_PWD"), dsn=EBS_DB_DSN)
cur = conn.cursor()
cur.execute(
    f"""
    SELECT notification_id, recipient_role, status, mail_status,
           TO_CHAR(begin_date,'YYYY-MM-DD HH24:MI:SS'),
           SUBSTR(subject,1,120)
      FROM apps.wf_notifications
     WHERE begin_date >= TO_DATE('{MONITOR_SINCE}','YYYY-MM-DD HH24:MI:SS')
       AND message_type='REQAPPRV'
       AND message_name='PO_REQ_APPROVE_JRAD'
     ORDER BY notification_id
    """
)
rows = cur.fetchall()
print("NEW_PR_COUNT", len(rows))
for row in rows:
    print(row)
cur.execute(
    """
    SELECT COUNT(*) FROM apps.wf_notifications
     WHERE status='OPEN' AND mail_status='MAIL'
    """
)
print("OPEN_MAIL_QUEUE", cur.fetchone()[0])
conn.close()

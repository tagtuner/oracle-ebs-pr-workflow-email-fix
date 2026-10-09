#!/usr/bin/env python3
"""Rollback C2b: restore PO_WF_REQ_NOTIFICATION package + template to FWK_RN baseline."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import oracledb

from config import APPS_PWD, APPS_USER, BACKUP_ROOT, EBS_DB_DSN, ORACLE_CLIENT_LIB, require_env

oracledb.init_oracle_client(lib_dir=ORACLE_CLIENT_LIB)
pwd = require_env("APPS_PWD")

ptr = BACKUP_ROOT / "c2b_LATEST.txt"
if ptr.exists():
    out = Path(ptr.read_text(encoding="utf-8").strip())
else:
    candidates = sorted(BACKUP_ROOT.glob("c2b_*"), reverse=True)
    if not candidates:
        raise SystemExit("No c2b backup folder — create backups before apply")
    out = candidates[0]

bak = out / "PO_WF_REQ_NOTIFICATION_BODY_CREATE.bak.sql"
if not bak.exists():
    raise SystemExit(f"Missing {bak}")

conn = oracledb.connect(user=APPS_USER, password=pwd, dsn=EBS_DB_DSN)
cur = conn.cursor()
print("WHEN", datetime.now().isoformat(timespec="seconds"))
print("RESTORE_FROM", out)

ddl = bak.read_text(encoding="utf-8")
print("Restoring package body chars", len(ddl))
cur.execute(ddl)
cur.execute(
    """
    SELECT line, text FROM all_errors
     WHERE owner='APPS' AND name='PO_WF_REQ_NOTIFICATION' AND type='PACKAGE BODY'
     ORDER BY sequence
    """
)
errs = cur.fetchall()
if errs:
    print("COMPILE_ERRORS", errs[:20])
    raise SystemExit("ABORT package restore compile fail")

cur.execute(
    """
    UPDATE apps.wf_messages_tl
       SET body = '&REQ_LINES_FWK_RN',
           html_body = '&REQ_LINES_FWK_RN'
     WHERE type='REQAPPRV' AND name='PO_REQ_APPROVE_JRAD' AND language='US'
    """
)
print("TEMPLATE_ROWS", cur.rowcount)
conn.commit()

cur.execute(
    """
    SELECT status FROM all_objects
     WHERE owner='APPS' AND object_name='PO_WF_REQ_NOTIFICATION'
       AND object_type='PACKAGE BODY'
    """
)
print("PKG", cur.fetchone())
cur.execute(
    """
    SELECT body, html_body FROM apps.wf_messages_tl
     WHERE type='REQAPPRV' AND name='PO_REQ_APPROVE_JRAD' AND language='US'
    """
)
print("BODY", cur.fetchone())
conn.close()
print("ROLLBACK_C2B_OK")

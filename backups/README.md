# Placeholder — local backups only

This folder is **gitignored**. Before any PROD change, export:

1. Full `PO_WF_REQ_NOTIFICATION` package body (`CREATE OR REPLACE ...`)
2. `wf_messages_tl` US body/html/subject for `PO_REQ_APPROVE_JRAD`
3. `wf_message_attributes` rows for message `REQAPPRV` / `PO_REQ_APPROVE_JRAD`

Point `backups/c2b_LATEST.txt` at your timestamped folder for `rollback_c2b.py`.

Never commit real backups to a public repository.

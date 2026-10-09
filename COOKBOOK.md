# Cookbook: Oracle EBS PR Action Required Email Fix

**Environment:** Oracle EBS R12.2.11 PROD (example hosts below are fictional)  
**Dates:** Aug 2026  
**Message:** `PO_REQ_APPROVE_JRAD` (Purchase Requisition — Action Required)  
**Status:** CLOSED — baseline stable post-recovery

> **Note:** All IPs, hostnames, emails, and notification IDs in this document are **sanitized examples** for public sharing. Replace with your environment via `.env`.

---

## 1. Problem statement

### Symptom (Outlook)

PR Action Required email arrives, but the **inline body** shows:

```text
FwkError: Unable to validate access to Notification
(WF_NTF_ACCESS_DENIED)
```

The **`Notification Detail.html` attachment** may still open correctly when the shared JSP attribute is intact.

### Two pipes (do not mix)

| Pipe | How it renders | Attribute / page |
|---|---|---|
| **Inline** | Mailer fetches OAF over HTTP at send time | `REQ_LINES_FWK_RN` → JSP `NotifMailerPG` / `ICX_POR_REQLINES_NTFN` |
| **Attachment** | User opens HTML in browser | Same `REQ_LINES_FWK_RN` slot + `FND_WFNTF_DETAILS` |

Remapping `REQ_LINES_FWK_RN` for inline fixes can **empty the attachment** (observed on PR **5519** in our session).

---

## 2. Environment placeholders

| Role | Example placeholder |
|---|---|
| PROD DB | `10.20.30.40:1521/PRODCDB` |
| PROD Apps / OACore / WFMLRSVC | `10.20.30.41` |
| HTMLAGENT | `http://ebsapps.example.com:8000/` |
| Mail sender | `oracle.workflow@example.com` |
| Approver role | `PR_APPROVER_ROLE` |
| SSH | `oracle@10.20.30.41` |

Configure in `.env` (see `.env.example`).

---

## 3. Pre-flight checks (read-only)

### 3.1 Message attributes snapshot

```sql
SELECT name, type, text_default
  FROM apps.wf_message_attributes
 WHERE message_type = 'REQAPPRV'
   AND message_name = 'PO_REQ_APPROVE_JRAD'
   AND name IN (
         '#HISTORY', 'REQ_LINES_FWK_RN', 'REQ_LINES_DETAILS',
         'ACTION_HISTORY', 'PO_REQ_APPROVE_MSG', 'APPROVAL_SEQUENCE_FWK_RN'
       )
 ORDER BY name;
```

**Example output (baseline):**

```text
('#HISTORY', 'DOCUMENT', 'ACTION_HISTORY')
('ACTION_HISTORY', 'DOCUMENT', 'ACTION_HISTORY')
('APPROVAL_SEQUENCE_FWK_RN', 'DOCUMENT', 'APPROVAL_SEQUENCE_FWK_RN')
('PO_REQ_APPROVE_MSG', 'DOCUMENT', 'PO_REQ_APPROVE_MSG')
('REQ_LINES_DETAILS', 'DOCUMENT', 'REQ_LINES_DETAILS')
('REQ_LINES_FWK_RN', 'DOCUMENT', 'REQ_LINES_FWK_RN')
```

### 3.2 Template body

**Baseline:**

```text
body      = &REQ_LINES_FWK_RN
html_body = &REQ_LINES_FWK_RN
```

### 3.3 Workflow Mailer URL Access Tester

System Administrator → Workflow Mailer URL Access Tester → sample notification → Html/US → Go.

**Example result (broken state):**

```text
Unable to validate access to Notification
```

Same FwkError as Outlook inline.

### 3.4 SQL access check vs HTTP failure

`AccessCheck(nid, access_key)` may return approver role in SQL while mailer HTTP to `NotifMailerPG` still fails — the break is on the **mailer JVM → OAF** path, not missing DB key data.

---

## 4. Experiments that FAILED

### 4.1 C1 — remap `REQ_LINES_FWK_RN` → `REQ_LINES_DETAILS`

**Result:** PR **5519** — attachment **empty**. Rolled back.

**Rule:** Never remap `REQ_LINES_FWK_RN`.

### 4.2 C2 token-only — template change only

**Change:** `body` / `html_body` → `&PO_REQ_APPROVE_MSG` + `&REQ_LINES_DETAILS`. FWK_RN left as JSP.

**Verify PR 6143 / ntf 2103135:**

| Check | Result |
|---|---|
| Validate error | Gone |
| Inline lines | **Empty** |
| Attachment | **Empty** (~551 B) |

**Cause:** `GET_REQ_LINES_DETAILS` returned blank HTML for `text/html`.

### 4.3 C2b FYI-style — package patch + template

**Change:** Patched `GET_PO_REQ_APPROVE_MSG` HTML wipe; `html_body = &PO_REQ_APPROVE_MSG`.

**SQL test looked good:** ~4660 char HTML with lines table.

**Production failed:**

- New PR **5526** / ntf **2103220** → `mail_status=ERROR`
- `ORA-04061: existing state of package body "APPS.PO_WF_REQ_NOTIFICATION" has been invalidated`
- Stale **WFMLRSVC Java PID** after package recompile

**Lesson:** After package recompile, restart **actual WFMLRSVC JVM** — OACore bounce or OAM component toggle alone is insufficient.

---

## 5. Working recovery sequence

### Step 1 — Roll back C2b

```powershell
cd scripts
python rollback_c2b.py
```

**Example output:**

```text
WHEN 2026-08-25T15:44:12
RESTORE_FROM .../backups/c2b_20260825_141807
Restoring package body chars 847123
TEMPLATE_ROWS 1
PKG ('VALID',)
BODY ('&REQ_LINES_FWK_RN', '&REQ_LINES_FWK_RN')
ROLLBACK_C2B_OK
```

**Verify SQL:**

```sql
SELECT status FROM all_objects
 WHERE owner='APPS' AND object_name='PO_WF_REQ_NOTIFICATION'
   AND object_type='PACKAGE BODY';

SELECT body, html_body FROM apps.wf_messages_tl
 WHERE type='REQAPPRV' AND name='PO_REQ_APPROVE_JRAD' AND language='US';
```

**Expected:**

```text
VALID
&REQ_LINES_FWK_RN | &REQ_LINES_FWK_RN
```

### Step 2 — OACore rolling bounce

```powershell
python oacore_rolling_bounce.py
```

**Example output:**

```text
=== OACore rolling bounce start Mon Aug 25 15:50:00 2026 ===
STOP oacore_server1
START oacore_server1
STOP oacore_server2
START oacore_server2
STOP oacore_server3
START oacore_server3
STOP oacore_server4
START oacore_server4
JVM count: 4
LISTEN 0 128 *:8000 *:*
=== DONE log=/tmp/oacore_rolling_bounce_20260825_155500.log ... ===
exit: 0
```

**Optional log tail on Apps:**

```bash
ssh oracle@10.20.30.41 "tail -20 /tmp/oacore_rolling_bounce_*.log"
```

### Step 3 — Restart real WFMLRSVC JVM (critical — **must be done TWICE**)

> **⚠️ Critical rule (confirmed Sep 2026):** Run `restart_wfmlr_jvm.py` **twice**.
> - **Restart #1** — immediately after OACore bounce (clears stale package state).
> - **Wait 30+ min** — let all 4 OACore servers fully warm and accept traffic.
> - **Restart #2** — the JVM must connect to fully-warmed OACore to initialize the ICX session correctly. Without this second restart the inline body still returns the ~4 KB error page ("Unable to validate access to Notification") even though OACore is up.
>
> **Root cause (OHS access log evidence):** Both the working response and the broken response used identical URL format. Working = ~27 KB full PR content; broken = ~4 KB error. The difference is entirely in OACore's internal rendering state at JVM connection time, not in the URL parameters.

```powershell
# Restart #1 — right after OACore bounce
python restart_wfmlr_jvm.py

# Wait 30+ min for all 4 OACore servers to fully warm

# Restart #2 — final; this is the one that fixes inline rendering
python restart_wfmlr_jvm.py
```

**Example outputs from session:**

**Restart #1 (OACore still warming):**

```text
OLD_PID 65232
NEW_PID 71503
  PID     STARTED                  COMMAND
71503   Mon Aug 25 15:58:00 2026  ... GSMSvcComponentContainer ... conc_queue_id=1140 ...
WFMLRSVC_JVM_RESTARTED
```

**Restart #2 (after OACore warm — this is the one that fixed it):**

```text
OLD_PID 71503
NEW_PID 82178
  PID     STARTED                  COMMAND
82178   Mon Aug 25 16:13:00 2026  ... GSMSvcComponentContainer ... conc_queue_id=1140 ...
WFMLRSVC_JVM_RESTARTED
```

**Manual equivalent on Apps (`10.20.30.41`):**

```bash
old_pid=$(ps -eo pid,args | awk '/[c]onc_queue_id=1140/ && /GSMSvcComponentContainer/ {print $1; exit}')
echo "OLD_PID=$old_pid"
kill -TERM "$old_pid"
# poll up to ~300s for new PID != old_pid
new_pid=$(ps -eo pid,args | awk '/[c]onc_queue_id=1140/ && /GSMSvcComponentContainer/ {print $1; exit}')
echo "NEW_PID=$new_pid"
ps -p "$new_pid" -o pid,lstart,args
```

**Component status SQL:**

```sql
SELECT component_name, component_status, component_status_info
  FROM apps.fnd_svc_components
 WHERE component_type = 'WF_MAILER';
```

**Expected:** `Workflow Notification Mailer | RUNNING`

### Step 4 — Inspect mail queue

```powershell
python check_mailer_queue.py
```

**Example output:**

```text
COMP
(10006, 'Workflow Notification Mailer', 'RUNNING', 1140, 'A')

QUEUE_COUNTS
(12, 'ERROR')
(1, 'MAIL')

MAIL_QUEUE_ITEMS
(2103324, 'PR_APPROVER_ROLE', 'OPEN', 'MAIL', '2026-08-25 16:05:00', 'Purchase Requisition ... REQ-7331 ...')
```

Do **not** bulk-update all ERROR/FAILED rows.

### Step 5 — Poison notification (surgical)

One ntf repeatedly timed out during OAF HTTP formatting. Mark **only that row** ERROR:

```powershell
# Set POISON_NOTIFICATION_ID in .env first
python mark_notification_error.py
```

**Example output:**

```text
BEFORE (2103324, 'REQAPPRV', 'PO_REQ_APPROVE_JRAD', 'PR_APPROVER_ROLE', 'OPEN', 'MAIL', 'Purchase Requisition ...')
UPDATED 1
AFTER (2103324, 'OPEN', 'ERROR')
MARK_ERROR_OK
```

EBS Worklist notification remains; email delivery abandoned for that item only.

**RESEND API note:**

```text
ORA-20002: 3234: Mail status 'MAIL' is invalid to resend the e-mail
```

### Step 6 — Verify with new PR

```powershell
python monitor_new_pr.py
```

**Example success:**

```text
NEW_PR_COUNT 1
(2103332, 'PR_APPROVER_ROLE', 'OPEN', 'SENT', '2026-08-25 16:21:24', 'Purchase Requisition ... REQ-5531 ...')
OPEN_MAIL_QUEUE 0
```

User confirmed: inline lines + attachment complete.

---

## 6. Diagnostic SQL cheatsheet

```sql
-- Single notification
SELECT notification_id, recipient_role, status, mail_status,
       TO_CHAR(begin_date,'YYYY-MM-DD HH24:MI:SS') begin_date,
       SUBSTR(subject,1,120) subject
  FROM apps.wf_notifications
 WHERE notification_id = :nid;

-- Recent Action Required PRs
SELECT notification_id, recipient_role, status, mail_status,
       TO_CHAR(begin_date,'YYYY-MM-DD HH24:MI:SS') begin_date,
       SUBSTR(subject,1,120) subject
  FROM apps.wf_notifications
 WHERE message_type = 'REQAPPRV'
   AND message_name = 'PO_REQ_APPROVE_JRAD'
   AND begin_date >= SYSDATE - 7
 ORDER BY notification_id DESC;

-- Queue counts
SELECT mail_status, COUNT(*)
  FROM apps.wf_notifications
 WHERE status = 'OPEN'
   AND mail_status IN ('MAIL','ERROR','FAILED')
 GROUP BY mail_status;
```

**WFMLRSVC process on Apps:**

```bash
ps -eo pid,lstart,args | grep 'conc_queue_id=1140' | grep GSMSvcComponentContainer
```

---

## 7. Decision tree

```text
Inline validate error on PR Action Required?
│
├─ Is REQ_LINES_FWK_RN still self/JSP?
│   └─ NO → restore immediately
│
├─ Recent PO_WF_REQ_NOTIFICATION recompile?
│   └─ YES → restart WFMLRSVC JVM; verify PID changed
│
├─ MAIL queue stuck on one ntf (HTTP timeout in log)?
│   └─ YES → mark ONLY that ntf ERROR
│
├─ Tempted to remap FWK_RN or disable WF_VALIDATE_NTF_ACCESS?
│   └─ STOP — both failed before
│
└─ Verify with NEW PR only
```

---

## 8. Forbidden list

| Action | Why |
|---|---|
| Remap `REQ_LINES_FWK_RN` | Empties attachment |
| C2 / C2b reapply without rollback plan | Empty mail / ORA-04061 |
| `WF_VALIDATE_NTF_ACCESS=N` | Failed historically |
| PROD mailer SMTP / HTMLAGENT change | Out of scope |
| Bulk reset ERROR/FAILED queue | Hides real problems |
| Trust component API bounce alone | PID may not change |

---

## 9. Verification checklist (new PR)

- [ ] New PR → Action Required to approver role
- [ ] `wf_notifications.mail_status = SENT`
- [ ] Outlook inline: item/qty/amount/account visible
- [ ] Attachment complete in browser
- [ ] Approve/Reject mailto links present
- [ ] `OPEN_MAIL_QUEUE = 0` after send

---

## 10. Related Oracle objects

| Object | Role |
|---|---|
| `apps.wf_messages_tl` | Email subject/body/html_body |
| `apps.wf_message_attributes` | Token bindings |
| `apps.PO_WF_REQ_NOTIFICATION` | PL/SQL HTML generators |
| `NotifMailerPG` | OAF mailer inline page |
| `ICX_POR_REQLINES_NTFN` | Requisition lines JSP |
| `FND_WFNTF_DETAILS` | Attachment detail function |
| WFMLRSVC / queue 1140 | Mailer Java container |

---

*Sanitized public runbook — Aug 2026. Adapt for your estate.*

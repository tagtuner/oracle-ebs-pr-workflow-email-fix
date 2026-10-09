# Recovery Checklist

Ordered steps from the production incident. Run on **PROD only with backups** and change approval.

---

## Before any change

- [ ] Export `PO_WF_REQ_NOTIFICATION` package body (full CREATE)
- [ ] Export `wf_messages_tl` US rows for `PO_REQ_APPROVE_JRAD`
- [ ] Export `wf_message_attributes` for message `REQAPPRV` / `PO_REQ_APPROVE_JRAD`
- [ ] Save backups under local `backups/c2b_YYYYMMDD_HHMMSS/` (gitignored)
- [ ] Confirm `REQ_LINES_FWK_RN` text_default = `REQ_LINES_FWK_RN` (self/JSP)
- [ ] Copy `.env.example` → `.env` with real credentials (never commit)

---

## Recovery sequence (what worked)

### 1. Rollback failed experiments

```powershell
cd scripts
python rollback_c2b.py
```

**Pass criteria:**

```text
PKG ('VALID',)
BODY ('&REQ_LINES_FWK_RN', '&REQ_LINES_FWK_RN')
ROLLBACK_C2B_OK
```

### 2. OACore rolling bounce

```powershell
python oacore_rolling_bounce.py
```

**Pass criteria:**

```text
JVM count: 4
*:8000 LISTEN
exit: 0
```

### 3. Restart WFMLRSVC JVM — **TWICE** (mandatory)

> **⚠️ Do this twice.** A single restart may connect the JVM to OACore before all servers are fully warm, leaving the inline body broken (returns ~4 KB error page).

```powershell
# Restart #1
python restart_wfmlr_jvm.py

# Wait 30+ min — let all 4 OACore servers fully warm
# Then:

# Restart #2
python restart_wfmlr_jvm.py
```

**Pass criteria (each run):**

```text
OLD_PID <number>
NEW_PID <different number>
WFMLRSVC_JVM_RESTARTED
```

> Component stop/start in OAM is **not** a substitute — verify Java PID actually changed.

### 4. Queue health check

```powershell
python check_mailer_queue.py
```

**Pass criteria:**

- Component status = `RUNNING`
- No unexpected stuck `MAIL` rows blocking new sends

### 5. Poison item cleanup (if needed)

Only for a **single known-bad** notification with repeated HTTP timeout:

```powershell
# Set POISON_NOTIFICATION_ID in .env
python mark_notification_error.py
```

**Pass criteria:**

```text
UPDATED 1
MARK_ERROR_OK
```

Do **not** bulk-reset historical ERROR/FAILED rows.

### 6. Verify with new PR

```powershell
python monitor_new_pr.py
```

**Pass criteria:**

```text
mail_status = SENT
OPEN_MAIL_QUEUE = 0
```

Plus user visual check: Outlook inline lines + attachment complete.

---

## Post-recovery

- [ ] Leave baseline config unchanged if stable
- [ ] Do not reapply C2/C2b without full test plan
- [ ] Document notification id and PR number of proof test
- [ ] Monitor mail queue for 24h

---

## Rollback of this rollback

If `rollback_c2b.py` itself fails, restore from local backup SQL files manually:

1. `@PO_WF_REQ_NOTIFICATION_BODY_CREATE.bak.sql` in SQL*Plus as APPS
2. Restore `wf_messages_tl` body/html from backup text files
3. OACore bounce + WFMLRSVC JVM restart
4. Verify package VALID

See [backups/README.md](../backups/README.md).

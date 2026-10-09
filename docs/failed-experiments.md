# Failed Experiments — Post-Mortem

What we tried before finding the stable baseline. **Do not repeat** without a new design and full rollback plan.

---

## C1 step 2 — Remap `REQ_LINES_FWK_RN`

| Item | Detail |
|---|---|
| Change | `wf_message_attributes.REQ_LINES_FWK_RN` → point to `REQ_LINES_DETAILS` |
| Goal | Inline lines via PL/SQL instead of JSP |
| Result | PR **5519** — attachment **empty** |
| Rollback | Restored FWK_RN to self (~17:36) |
| Lesson | Shared attribute — attachment pipe breaks |

**Verdict:** ❌ Never remap `REQ_LINES_FWK_RN`

---

## C2 — Token-only template change

| Item | Detail |
|---|---|
| Change | `body` / `html_body` → `&PO_REQ_APPROVE_MSG` + `&REQ_LINES_DETAILS` |
| FWK_RN attr | Unchanged (still JSP) |
| Goal | Bypass JSP validate error for inline |
| Verify PR | **6143** / ntf **2103135** |
| Inline | Validate error gone, **lines empty** |
| Attachment | **Empty** (~551 B) |
| Root cause | `GET_REQ_LINES_DETAILS` returned blank HTML for `text/html` |
| Rollback | 13:36 — restore `&REQ_LINES_FWK_RN` |

**Verdict:** ❌ Do not reapply C2 token-only

---

## C2b — FYI-style package patch + template

| Item | Detail |
|---|---|
| Change | Patch `GET_PO_REQ_APPROVE_MSG` HTML wipe; `html_body = &PO_REQ_APPROVE_MSG` |
| Backup | Full package CREATE + template (local `backups/c2b_*`) |
| SQL test | HTML ~4660 chars with Item Description table |
| Production | PR **5526** / ntf **2103220** → `mail_status=ERROR` |
| Error | `ORA-04061` — package body invalidated in running mailer JVM |
| Rollback | 15:44 — full package restore + template |

**Verdict:** ❌ Do not reapply C2b without JVM restart discipline

---

## GUEST grants — WF_WORKLIST addition (M3)

| Item | Detail |
|---|---|
| Change | Added `WF_WORKLIST` + `WF_WORKLIST_ACCESS` to GUEST menu seq 7–8 |
| SQL function test | PASS |
| OACore bounce | 4/4 OK |
| HTTP curl / mailer | Still *insufficient privileges* / validate fail |
| Lesson | Worklist grant was not the wall |

**Verdict:** ⚪ Harmless probe, not the fix

---

## Phase 7A — `WF_VALIDATE_NTF_ACCESS=N`

| Item | Detail |
|---|---|
| Status | Failed in earlier phase (June) |
| Rule | Do not disable access validation |

**Verdict:** ❌ Forbidden

---

## Component API bounce without JVM PID change

| Item | Detail |
|---|---|
| Symptom | Mailer shows RUNNING but sends fail after package compile |
| Cause | Old WFMLRSVC Java PID still holds invalidated package state |
| Fix | `kill -TERM` old PID; wait for new PID |

**Verdict:** ✅ Operational lesson — always verify PID changed

---

## What actually worked

Baseline JSP template (`&REQ_LINES_FWK_RN`) + OACore bounce + **real WFMLRSVC JVM restart** + surgical queue cleanup + new PR verification.

See [recovery-checklist.md](./recovery-checklist.md).

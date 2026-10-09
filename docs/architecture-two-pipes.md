# Architecture: Two Pipes, One Shared Attribute

Oracle EBS Purchase Requisition **Action Required** notifications (`PO_REQ_APPROVE_JRAD`) render email content through **two independent paths** that share a single workflow message attribute.

Understanding this split is the most important concept in the entire incident — most failed fixes broke one pipe while trying to repair the other.

---

## High-level flow

```text
                    PO Workflow submits PR
                              │
                              ▼
              WF Notification (PO_REQ_APPROVE_JRAD)
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
     ┌─────────────────┐           ┌─────────────────┐
     │  INLINE PIPE    │           │ ATTACHMENT PIPE │
     │  (email body)   │           │ (HTML file)     │
     └────────┬────────┘           └────────┬────────┘
              │                               │
              ▼                               ▼
   WFMLRSVC Java mailer              User opens attachment
   HTTP fetch at send time           in browser later
              │                               │
              ▼                               ▼
        NotifMailerPG                   FND_WFNTF_DETAILS
              │                               │
              ▼                               ▼
   ICX_POR_REQLINES_NTFN              Same underlying data
   (requisition lines JSP)            via wfMailer access key
              │                               │
              └───────────┬───────────────────┘
                          ▼
              Shared attribute:
              REQ_LINES_FWK_RN
              (type DOCUMENT, text_default = self/JSP)
```

---

## Inline pipe (email body)

| Step | Component | Notes |
|---|---|---|
| 1 | Workflow Notification Mailer (WFMLRSVC) | Java process on Apps tier, queue id typically 1140 |
| 2 | Reads `wf_messages_tl.html_body` | Baseline: `&REQ_LINES_FWK_RN` |
| 3 | Resolves `REQ_LINES_FWK_RN` attribute | Points to JSP/OAF region |
| 4 | HTTP GET to HTMLAGENT | Example: `http://ebsapps.example.com:8000/` |
| 5 | OAF page `NotifMailerPG` | Validates notification access |
| 6 | Embeds `ICX_POR_REQLINES_NTFN` | Renders PR lines table in email |

**Failure mode observed:** `WF_NTF_ACCESS_DENIED` — *Unable to validate access to Notification* inside inline HTML. User sees error text instead of lines table.

---

## Attachment pipe (Notification Detail.html)

| Step | Component | Notes |
|---|---|---|
| 1 | Mailer attaches `Notification Detail.html` | Separate from inline body assembly |
| 2 | Link/function `FND_WFNTF_DETAILS` | Browser-openable detail page |
| 3 | Uses same `REQ_LINES_FWK_RN` slot | Must remain JSP/self reference |
| 4 | User opens in browser | Often works when inline fails |

**Failure mode observed:** When `REQ_LINES_FWK_RN` was remapped to PL/SQL (`REQ_LINES_DETAILS`), attachment became **empty** (PR 5519) because FND details expected the JSP path.

---

## Shared attribute — the critical constraint

```sql
SELECT name, type, text_default
  FROM apps.wf_message_attributes
 WHERE message_type = 'REQAPPRV'
   AND message_name = 'PO_REQ_APPROVE_JRAD'
   AND name = 'REQ_LINES_FWK_RN';
```

**Baseline (correct):**

```text
REQ_LINES_FWK_RN | DOCUMENT | REQ_LINES_FWK_RN
```

| Change attempted | Inline effect | Attachment effect |
|---|---|---|
| Remap FWK_RN → PL/SQL | May change inline source | **Attachment empty** |
| Template token-only (C2) | Validate error gone, lines blank | **Attachment empty** |
| Keep FWK_RN as JSP | Uses HTTP validate path | Attachment complete |

**Rule:** Never remap `REQ_LINES_FWK_RN`. Change mail template tokens or PL/SQL generators separately — not the shared JSP binding.

---

## PL/SQL attributes (supporting, not shared)

These generate document HTML but are **not** a safe substitute for `REQ_LINES_FWK_RN` on the attachment path:

| Attribute | Generator procedure | Role |
|---|---|---|
| `PO_REQ_APPROVE_MSG` | `GET_PO_REQ_APPROVE_MSG` | Header / summary text |
| `REQ_LINES_DETAILS` | `GET_REQ_LINES_DETAILS` | Lines as PL/SQL HTML (blank in our C2 test) |
| `ACTION_HISTORY` | `GET_ACTION_HISTORY` | Approval history table |
| `#HISTORY` | Points to `ACTION_HISTORY` | History token alias |

Package: `apps.PO_WF_REQ_NOTIFICATION`

C2b patched `GET_PO_REQ_APPROVE_MSG` to stop wiping HTML — SQL test passed but mailer hit `ORA-04061` until JVM restart.

---

## GUEST / access validation layer

Inline pipe requires OAF to validate notification access when mailer fetches the page:

| Check | Result in our session |
|---|---|
| GUEST ICX grants (PROD vs TEST) | Same 6/6 — not the gap |
| `WF_VALIDATE_NTF_ACCESS` | Y (do not set N) |
| SQL `AccessCheck(nid, key)` | PASS → approver role |
| Mailer HTTP to `NotifMailerPG` | FAIL → FwkError |
| SYSADMIN URL Access Tester | Same FwkError |

Conclusion: break is **mailer send-time HTTP session → OAF validate**, not missing DB key or missing menu grant alone.

---

## Operational components map

```text
┌─────────────────────────────────────────────────────────┐
│  DB tier (example 10.20.30.40)                          │
│  - wf_messages_tl / wf_message_attributes               │
│  - wf_notifications (mail_status: MAIL/SENT/ERROR)      │
│  - PO_WF_REQ_NOTIFICATION (PL/SQL package)              │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  Apps tier (example 10.20.30.41)                        │
│  - OACore (4 JVMs, port 8000)                           │
│  - WFMLRSVC Java (conc_queue_id=1140)  ← must restart   │
│  - NotifMailerPG / ICX JSP pages                        │
└─────────────────────────────────────────────────────────┘
```

After package recompile: **OACore bounce alone is insufficient** — restart WFMLRSVC Java and verify PID changed.

---

## Related docs

- [COOKBOOK.md](../COOKBOOK.md) — step-by-step recovery with command outputs
- [recovery-checklist.md](./recovery-checklist.md) — ordered recovery steps
- [failed-experiments.md](./failed-experiments.md) — C1/C2/C2b post-mortem

# Oracle EBS Workflow Notification Mailer — Production Runbooks

Sanitized public cookbooks from real PROD recoveries. **No passwords, no real IPs, no real mailbox names** — use `.env`.

---

## ★ Oct 2026 — SMTP 587/TLS + ECX `V1:` restore (NEW)

**Big win:** Mailer component returned to **RUNNING** after mailbox AUTH failure + plaintext password mistake. Same recovery also cleared Outlook **"Unable to validate access to Notification"** on new PR Action Required mail — without Path-B template rewrites.

| Doc | Purpose |
|---|---|
| **[docs/mailer-smtp-ecx-restore-2026-10/COOKBOOK.md](./docs/mailer-smtp-ecx-restore-2026-10/COOKBOOK.md)** | Full commands + **actual sanitized outputs** + terminal PNGs |
| **[LINKEDIN_POST_2026-10-09.md](./LINKEDIN_POST_2026-10-09.md)** | LinkedIn draft for this achievement |
| `scripts/apply_mailer_smtp_ecx_restore.py` | Env-based restore (AUTH → ECX encrypt → JVM bounce → start) |
| `scripts/ro_mailer_status.py` | RO status (passwords classified, never printed) |
| `scripts/render_terminal_pngs.py` | Rebuild terminal screenshot PNGs |

**Root cause (short):** mailbox AUTH break + EBS stored plaintext SMTP password while Java expects `ECX_OBFUSCATE` ciphertext (`V1:…`) on **587/TLS**.

**One-liner:** `python scripts/apply_mailer_smtp_ecx_restore.py` (after `.env`)

---

## Aug 2026 — Inline Unable + attachment (JSP / JVM path)

Production runbook when **Purchase Requisition Action Required** emails (`PO_REQ_APPROVE_JRAD`) show:

- Inline body: *Unable to validate access to Notification* (`WF_NTF_ACCESS_DENIED`)
- Attachment incomplete or empty after bad template experiments

**Outcome:** Baseline JSP path restored + real WFMLRSVC JVM restart → new PR delivered with inline lines and complete attachment.

---

## Start here

| Doc | Purpose |
|---|---|
| **[docs/mailer-smtp-ecx-restore-2026-10/COOKBOOK.md](./docs/mailer-smtp-ecx-restore-2026-10/COOKBOOK.md)** | **Latest** — SMTP/ECX mailer restore |
| **[COOKBOOK.md](./COOKBOOK.md)** | Aug 2026 JSP/Unable recovery steps + outputs |
| **[REPO_STRUCTURE.md](./REPO_STRUCTURE.md)** | Published folder layout and reading order |
| **[docs/architecture-two-pipes.md](./docs/architecture-two-pipes.md)** | Why inline vs attachment breaks |
| **[docs/recovery-checklist.md](./docs/recovery-checklist.md)** | Ordered recovery checklist |
| **[docs/failed-experiments.md](./docs/failed-experiments.md)** | C1/C2/C2b post-mortem |
| **[LINKEDIN_POST_2026-10-09.md](./LINKEDIN_POST_2026-10-09.md)** | LinkedIn draft (Oct 2026) |
| **[LINKEDIN_POST.md](./LINKEDIN_POST.md)** | LinkedIn draft (Aug 2026) |
| **[scripts/](./scripts/)** | Python helpers (env-based, no hardcoded secrets) |
| **[.env.example](./.env.example)** | Copy to `.env` locally — never commit |

---

## Repository structure

```text
oracle-ebs-pr-workflow-email-fix/
├── README.md
├── COOKBOOK.md                          # Aug 2026 JSP path
├── LINKEDIN_POST.md
├── LINKEDIN_POST_2026-10-09.md          # Oct 2026 achievement
├── REPO_STRUCTURE.md
├── LICENSE
├── requirements.txt
├── .env.example
├── docs/
│   ├── architecture-two-pipes.md
│   ├── recovery-checklist.md
│   ├── failed-experiments.md
│   └── mailer-smtp-ecx-restore-2026-10/
│       ├── COOKBOOK.md                  # Oct 2026 full runbook
│       └── assets/                      # terminal result PNGs
├── scripts/
│   ├── apply_mailer_smtp_ecx_restore.py
│   ├── ro_mailer_status.py
│   ├── render_terminal_pngs.py
│   ├── config.py
│   ├── rollback_c2b.py
│   ├── oacore_rolling_bounce.py
│   ├── restart_wfmlr_jvm.py
│   ├── check_mailer_queue.py
│   ├── monitor_new_pr.py
│   └── mark_notification_error.py
└── backups/
    └── README.md          # local backups only (gitignored)
```

See [REPO_STRUCTURE.md](./REPO_STRUCTURE.md) for reading order and script mapping.

---

## Quick facts (example placeholders)

| Item | Example value |
|---|---|
| Message | `PO_REQ_APPROVE_JRAD` / type `REQAPPRV` |
| Sender | `oracle.workflow@example.com` |
| Inline engine | `NotifMailerPG` + `ICX_POR_REQLINES_NTFN` (JSP via `REQ_LINES_FWK_RN`) |
| Attachment engine | `FND_WFNTF_DETAILS` (same shared attribute) |
| PROD DB | `10.20.30.40:1521/PRODCDB` |
| PROD Apps | `10.20.30.41` — `http://ebsapps.example.com:8000/` |

Replace with your estate values in `.env`.

---

## What actually fixed it

1. Roll back failed template/package experiments (C2/C2b)
2. Restore `BODY` / `HTML_BODY` = `&REQ_LINES_FWK_RN`
3. OACore rolling bounce (4 JVMs)
4. **Restart the real WFMLRSVC Java PID — TWICE** (component API stop/start is not enough)
   - Restart #1 right after OACore bounce
   - Wait 30+ min for all OACore servers to fully warm
   - Restart #2 — JVM must connect to warm OACore or inline stays broken
5. Clear poison queue items surgically — no bulk reset
6. Verify with a **new** PR only

---

## Quick start

```powershell
copy .env.example .env
# Edit .env with your DB/SSH credentials (local only)

pip install oracledb

cd scripts
python rollback_c2b.py
python oacore_rolling_bounce.py
python restart_wfmlr_jvm.py
python check_mailer_queue.py
python monitor_new_pr.py
```

---

## Hard rules

- **Never remap** `REQ_LINES_FWK_RN` — breaks attachment
- **Do not** set `WF_VALIDATE_NTF_ACCESS=N`
- **Do not** trust mailer component API bounce unless WFMLRSVC PID changes
- **Do not** bulk-reset historical `ERROR`/`FAILED` notifications
- Old sent emails never change — test only **new** PRs

---

## Security

All IPs, hostnames, and credentials in this repo are **fictional examples**. Never commit real `.env` files or production backups containing customer data.

---

## License

MIT — use at your own risk. Test on non-PROD first.

**Author:** OmniTech / Tanveer — documented from Oracle EBS R12.2.11 production incident, Aug 2026.

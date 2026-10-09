# Repository structure

Published layout for **oracle-ebs-pr-workflow-email-fix**.

```text
oracle-ebs-pr-workflow-email-fix/
├── README.md                 # Start here — overview + quick start
├── COOKBOOK.md               # Full runbook: commands + example outputs
├── LINKEDIN_POST.md          # Ready-to-edit social post drafts
├── REPO_STRUCTURE.md         # This file
├── LICENSE                   # MIT
├── requirements.txt          # Python: oracledb
├── .env.example              # Copy → .env locally (never commit)
├── .gitignore
│
├── docs/
│   ├── architecture-two-pipes.md   # Inline vs attachment — shared attribute
│   ├── recovery-checklist.md       # Ordered recovery steps + pass criteria
│   └── failed-experiments.md       # C1/C2/C2b post-mortem
│
├── scripts/
│   ├── config.py                   # Shared env loader
│   ├── rollback_c2b.py             # Restore package + template baseline
│   ├── oacore_rolling_bounce.py    # Rolling bounce 4 OACore JVMs
│   ├── restart_wfmlr_jvm.py        # Kill/replace WFMLRSVC Java PID
│   ├── check_mailer_queue.py       # RO: component + MAIL queue
│   ├── monitor_new_pr.py           # Watch new PO_REQ_APPROVE_JRAD mail
│   └── mark_notification_error.py  # Surgical: one stuck ntf → ERROR
│
└── backups/
    └── README.md               # How to create local backups (folder gitignored)
```

---

## Reading order

1. [README.md](./README.md) — problem summary
2. [docs/architecture-two-pipes.md](./docs/architecture-two-pipes.md) — why fixes fail
3. [docs/failed-experiments.md](./docs/failed-experiments.md) — what not to repeat
4. [COOKBOOK.md](./COOKBOOK.md) — full command replay
5. [docs/recovery-checklist.md](./docs/recovery-checklist.md) — checklist for live recovery

---

## Script mapping (internal → public names)

| Public script | Original internal name |
|---|---|
| `rollback_c2b.py` | `rollback_prod_c2b.py` |
| `restart_wfmlr_jvm.py` | `restart_prod_wfmlr_jvm.py` |
| `oacore_rolling_bounce.py` | `m7_c2_oacore_bounce.py` |
| `check_mailer_queue.py` | `ro_mailer_queue_stuck.py` |
| `monitor_new_pr.py` | `ro_monitor_new_pr.py` |
| `mark_notification_error.py` | `mark_ntf_2103324_error.py` |

All public scripts use `.env` — no hardcoded passwords or production hostnames.

---

## Not included (intentionally)

| Item | Reason |
|---|---|
| Real backup SQL/HTML | Contains customer URLs and data |
| `apply_c2*.py` | Failed experiments — documented only in post-mortem |
| Production IPs/hostnames | Replaced with `10.20.30.x` / `example.com` in all docs |

Store real backups locally under `backups/` (gitignored).

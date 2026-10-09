# LinkedIn Post Draft

Repo: https://github.com/tagtuner/oracle-ebs-pr-workflow-email-fix

---

## Version A — Story post (recommended)

**First line (feed preview):**

We fixed Oracle EBS Purchase Requisition "Action Required" emails where Outlook showed *Unable to validate access to Notification* — without breaking the HTML attachment.

**Body:**

If you run Oracle E-Business Suite Workflow Notification Mailer, you may know this pain:

📧 The email arrives  
❌ Inline body: *Unable to validate access to Notification*  
✅ Attachment sometimes still opens fine  

We hit this on PROD for message `PO_REQ_APPROVE_JRAD` (PR Action Required).

**What we learned the hard way**

1️⃣ **Two pipes, one attribute**  
Inline uses OAF HTTP (`NotifMailerPG` + JSP). Attachment uses `FND_WFNTF_DETAILS`. Both share `REQ_LINES_FWK_RN`. Remap it for a "quick fix" → attachment goes empty.

2️⃣ **Not every fix is a fix**  
Template-only changes and a package patch mimicking FYI mail looked great in SQL tests. Production mail still failed — including `ORA-04061` because the WFMLRSVC Java process was stale after package recompile.

3️⃣ **Recovery = operational discipline**  
✅ Rollback to baseline JSP template  
✅ OACore rolling bounce (4 JVMs)  
✅ Restart the **actual WFMLRSVC JVM** — verify PID changed  
✅ Surgically clear poison queue items  
✅ Verify with a **new PR only**

**Proof:** New PR → notification `SENT`. Inline lines + attachment both complete. Still running excellent days later.

Full cookbook with commands, SQL, and example outputs on GitHub (sanitized — no production secrets):

🔗 https://github.com/tagtuner/oracle-ebs-pr-workflow-email-fix

#OracleEBS #OracleApps #Workflow #EBS #DBA #SysAdmin #EnterpriseIT #DevOps

---

## Version B — Short technical

Fixed Oracle EBS PR Action Required emails (`PO_REQ_APPROVE_JRAD`):

**Symptom:** Inline `WF_NTF_ACCESS_DENIED`; attachment uses separate path.

**Failed:** Remapping `REQ_LINES_FWK_RN`; token-only template; package patch without JVM recycle.

**Worked:** JSP baseline rollback + OACore bounce + real WFMLRSVC PID restart + targeted queue cleanup.

Runbook: https://github.com/tagtuner/oracle-ebs-pr-workflow-email-fix

#OracleEBS #WorkflowMailer #R12

---

## Version C — Urdu/English mix

Oracle EBS PROD pe PR Action Required email ka inline body error de raha tha.

Teen rollbacks baad lesson clear hua:

🔴 `REQ_LINES_FWK_RN` remap mat karo  
🔴 Package compile ke baad sirf OAM bounce kaafi nahi — **WFMLRSVC Java PID** verify karo  
🟢 Baseline + JVM restart + new PR test = stable fix  

Poora cookbook GitHub pe (sanitized, no secrets):

https://github.com/tagtuner/oracle-ebs-pr-workflow-email-fix

#OracleEBS #EBS

---

## Published repo structure

```text
oracle-ebs-pr-workflow-email-fix/
├── README.md
├── COOKBOOK.md
├── LINKEDIN_POST.md
├── REPO_STRUCTURE.md
├── LICENSE
├── docs/
│   ├── architecture-two-pipes.md
│   ├── recovery-checklist.md
│   └── failed-experiments.md
├── scripts/          (6 Python tools + config.py)
└── backups/README.md (local only)
```

https://github.com/tagtuner/oracle-ebs-pr-workflow-email-fix

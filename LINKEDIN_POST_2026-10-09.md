# LinkedIn Post — Oct 2026 Workflow Mailer + Unable Fix

Paste into LinkedIn. Attach the PNGs from `docs/mailer-smtp-ecx-restore-2026-10/assets/` (and a **redacted** Outlook screenshot if you want).  
Repo link: https://github.com/tagtuner/oracle-ebs-pr-workflow-email-fix

---

## Version A — Story (recommended)

We just brought Oracle E-Business Suite **Workflow Notification Mailer** back from the dead — and cleared Outlook **"Unable to validate access to Notification"** on Purchase Requisition Action Required emails in the same recovery.

This was a solid production recovery: ops discipline + deep Java/PLSQL mailer forensics.

**What broke**

📧 Mailbox AUTH for the WF mailer account failed  
❌ Component went `DEACTIVATED_SYSTEM` — no notifications  
🧩 Someone (us, earlier) stored the SMTP password as **plaintext** in `fnd_svc_comp_param_vals`  
🔐 Java mailer calls `SecurityUtils.decrypt` → `ECX_OBFUSCATE` and expects `V1:…` ciphertext — plaintext never decrypts cleanly

**Wrong rabbit holes we avoided**

- Anonymous SMTP `:25` (AUTH unsupported on our path)  
- Jumping straight to template Path-B / PL/SQL body rewrites  
- Trusting OAM “stop/start” without verifying the **real WFMLRSVC JVM PID**

**What actually fixed it**

1️⃣ Prove AUTH from the apps tier to **SMTP 587 + STARTTLS**  
2️⃣ Encrypt mailbox password with `ECX_OBFUSCATE.ECX_DATA_ENCRYPT` → store `V1:…` for OUTBOUND + INBOUND  
3️⃣ Keep **TLS / BASIC / JDK cacerts**; inbound threads `0` until outbound is stable  
4️⃣ **JVM-first bounce** of the concurrent queue container, then start the component  
5️⃣ Watch until `RUNNING` — then prove with a **new** PR email

**Proof (terminal — sanitized images in the repo)**

- `auth_probe: OK`  
- `enc_len=92 prefix='V1:****'` · `roundtrip: OK`  
- `OLD_JVM` → `NEW_JVM`  
- `t+20s RUNNING`  
- RO check: `OUTBOUND_PASSWORD = V1_ENCRYPTED`

Bonus: with a healthy mailer JVM again, the FWK_RN inline body path rendered fully — **Unable cleared** without Path-B.

Full cookbook (every command + sanitized outputs + PNGs + env-based script):

🔗 https://github.com/tagtuner/oracle-ebs-pr-workflow-email-fix  
📁 `docs/mailer-smtp-ecx-restore-2026-10/COOKBOOK.md`

#OracleEBS #OracleApps #WorkflowMailer #EBS #R12 #DBA #SysAdmin #EnterpriseIT #DevOps #ITOperations #ProductionSupport #SMTP #TLS

---

## Version B — Short

Oracle EBS WF Notification Mailer restored:

**Root:** mailbox AUTH break + plaintext SMTP password (mailer needs `ECX_OBFUSCATE` `V1:` encrypt) on **587/TLS**.  
**Fix:** AUTH probe → ECX encrypt → JVM-first bounce → component `RUNNING`.  
**Side effect:** Outlook "Unable to validate access" cleared on new PR Action Required mail.

Cookbook + terminal screenshots (sanitized):  
https://github.com/tagtuner/oracle-ebs-pr-workflow-email-fix

#OracleEBS #WorkflowMailer #SMTP

---

## Version C — Urdu/English (personal)

PROD pe Workflow Mailer down tha — notifications nahi ja rahi thin, aur kabhi Outlook pe *Unable to validate access* bhi aa jata tha.

Root cause simple nikla, fix deep:

🔴 Mailbox AUTH toot gaya  
🔴 Password DB mein plaintext — Java `V1:` decrypt expect karti hai (`ECX_OBFUSCATE`)  
🟢 587 + TLS + ECX encrypt + real JVM bounce → **RUNNING**  
🟢 Nayi PR email full body — Unable bhi clear

Ye hum dono ki bari achievement hai — full runbook GitHub pe (secrets/IPs hata ke).

🔗 https://github.com/tagtuner/oracle-ebs-pr-workflow-email-fix

#OracleEBS #Workflow #DevOps

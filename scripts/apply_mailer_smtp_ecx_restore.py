#!/usr/bin/env python3
"""
Restore Oracle EBS Workflow Notification Mailer on SMTP 587/TLS with
ECX_OBFUSCATE-encrypted passwords (V1:…).

All hosts / users / passwords come from environment variables.
Never hardcode secrets. See .env.example and the Oct 2026 cookbook.
"""
from __future__ import annotations

import base64
import os
import subprocess
import sys
import time

import oracledb

COMPONENT_ID = int(os.environ.get("WF_MAILER_COMPONENT_ID", "10006"))
DSN = os.environ["EBS_DB_DSN"]  # e.g. ebs-db.example.local:1521/PROD
APPS_USER = os.environ.get("APPS_USER", "APPS")
APPS_PWD = os.environ["APPS_PWD"]
ORACLE_CLIENT_LIB = os.environ.get("ORACLE_CLIENT_LIB", "")
SSH_HOST = os.environ["PROD_APPS_SSH"]  # e.g. oracle@ebs-apps.example.local
MAIL_HOST = os.environ["MAIL_HOST"]  # e.g. mail.example.com
MAIL_USER = os.environ["MAIL_USER"]  # e.g. workflow.mailer@example.com
MAIL_PWD = os.environ["MAIL_PWD"]
CACERTS = os.environ.get(
    "MAILER_SSL_TRUSTSTORE",
    "/u01/oracle/EBS/fs2/EBSapps/comn/util/jdk64/jre/lib/security/cacerts",
)
HTMLAGENT = os.environ.get("HTMLAGENT", "http://ebs-apps.example.local:8000/")
QUEUE_ID = os.environ.get("WFMLR_QUEUE_ID", "1140")
PS = (
    "ps -eo pid,args | "
    f"awk '/[c]onc_queue_id={QUEUE_ID}/ && /GSMSvcComponentContainer/ {{print $1; exit}}'"
)


def ssh(cmd: str, timeout: int = 45) -> str:
    r = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12", SSH_HOST, cmd],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return (r.stdout or "").strip()


def test_auth_from_apps() -> bool:
    plain = base64.b64encode(
        b"\0" + MAIL_USER.encode() + b"\0" + MAIL_PWD.encode()
    ).decode()
    cmd = (
        "{ sleep 1; echo EHLO ebs-apps; sleep 1; "
        f"echo 'AUTH PLAIN {plain}'; "
        "sleep 1; echo QUIT; } | "
        f"timeout 20 openssl s_client -connect {MAIL_HOST}:587 "
        "-starttls smtp -quiet 2>/dev/null | tail -20"
    )
    out = ssh(cmd, timeout=60)
    ok = "Authentication successful" in out
    print("auth_probe:", "OK" if ok else "FAIL", flush=True)
    return ok


def ecx_encrypt(cur, plaintext: str) -> str:
    out = cur.var(oracledb.DB_TYPE_VARCHAR)
    err = cur.var(oracledb.DB_TYPE_VARCHAR)
    ret = cur.var(oracledb.DB_TYPE_NUMBER)
    cur.execute(
        """
        BEGIN
          apps.ecx_obfuscate.ecx_data_encrypt(
            l_input_string  => :inp,
            l_output_string => :out,
            errmsg          => :err,
            retcode         => :ret);
        END;
        """,
        inp=plaintext,
        out=out,
        err=err,
        ret=ret,
    )
    code = ret.getvalue()
    enc = out.getvalue()
    if code not in (0, "0", None) or not enc:
        raise RuntimeError(f"encrypt fail ret={code} err={err.getvalue()!r}")
    return enc


def ecx_decrypt(cur, ciphertext: str) -> str:
    out = cur.var(oracledb.DB_TYPE_VARCHAR)
    err = cur.var(oracledb.DB_TYPE_VARCHAR)
    ret = cur.var(oracledb.DB_TYPE_NUMBER)
    cur.execute(
        """
        BEGIN
          apps.ecx_obfuscate.ecx_data_encrypt(
            l_input_string  => :inp,
            l_qual_code     => 'D',
            l_output_string => :out,
            errmsg          => :err,
            retcode         => :ret);
        END;
        """,
        inp=ciphertext,
        out=out,
        err=err,
        ret=ret,
    )
    return out.getvalue() or ""


def setp(cur, name: str, value: str) -> None:
    cur.execute(
        """
        UPDATE apps.fnd_svc_comp_param_vals v
           SET parameter_value = :v,
               last_update_date = SYSDATE,
               last_updated_by = 0
         WHERE v.component_id = :c
           AND EXISTS (
             SELECT 1 FROM apps.fnd_svc_comp_params_b p
              WHERE p.parameter_id = v.parameter_id
                AND p.parameter_name = :n
           )
        """,
        v=value,
        c=COMPONENT_ID,
        n=name,
    )
    show = f"ENC_LEN_{len(value)}" if "PASS" in name.upper() else repr(value)
    print(f"SET {name}={show} rows={cur.rowcount}", flush=True)


def status(cur):
    cur.execute(
        """
        SELECT component_status, SUBSTR(NVL(component_status_info,' '),1,700)
          FROM apps.fnd_svc_components WHERE component_id=:c
        """,
        c=COMPONENT_ID,
    )
    return cur.fetchone()


def bounce_jvm() -> str:
    old = ssh(PS)
    print("OLD_JVM", old, flush=True)
    if old.isdigit():
        ssh(f"kill -TERM {old}")
    for i in range(40):
        time.sleep(5)
        new = ssh(PS)
        if new.isdigit() and (not old.isdigit() or new != old):
            print("NEW_JVM", new, flush=True)
            return new
        if (i + 1) % 6 == 0:
            print(f"wait_jvm {(i+1)*5}s pid={new or 'none'}", flush=True)
    return ssh(PS) or "NONE"


def main() -> int:
    print("=== probe 587 AUTH from apps ===", flush=True)
    if not test_auth_from_apps():
        print("ABORT: mailbox AUTH fail — fix Mailcow/password first", flush=True)
        return 3

    if ORACLE_CLIENT_LIB:
        oracledb.init_oracle_client(lib_dir=ORACLE_CLIENT_LIB)
    conn = oracledb.connect(user=APPS_USER, password=APPS_PWD, dsn=DSN)
    cur = conn.cursor()

    print("=== ECX encrypt + roundtrip ===", flush=True)
    enc = ecx_encrypt(cur, MAIL_PWD)
    print(f"enc_len={len(enc)} prefix='V1:****'", flush=True)
    back = ecx_decrypt(cur, enc)
    print("roundtrip:", "OK" if back == MAIL_PWD else "MISMATCH", flush=True)
    if back != MAIL_PWD:
        return 4

    print("=== JVM kill first ===", flush=True)
    bounce_jvm()
    time.sleep(5)
    print("status after kill", status(cur), flush=True)

    setp(cur, "OUTBOUND_SERVER", MAIL_HOST)
    setp(cur, "OUTBOUND_PROTOCOL", "SMTP")
    setp(cur, "OUTBOUND_SECURE_PROTOCOL", "TLS")
    setp(cur, "OUTBOUND_AUTH_TYPE", "BASIC")
    setp(cur, "OUTBOUND_USER", MAIL_USER)
    setp(cur, "OUTBOUND_PASSWORD", enc)
    setp(cur, "MAILER_SSL_TRUSTSTORE", CACERTS)
    setp(cur, "REPLYTO", MAIL_USER)
    setp(cur, "HTMLAGENT", HTMLAGENT)
    setp(cur, "ACCOUNT", MAIL_USER)
    setp(cur, "INBOUND_SERVER", MAIL_HOST)
    setp(cur, "INBOUND_PROTOCOL", "IMAP")
    setp(cur, "INBOUND_SECURE_PROTOCOL", "TLS")
    setp(cur, "INBOUND_PASSWORD", enc)
    setp(cur, "PROCESSOR_IN_THREAD_COUNT", "0")
    setp(cur, "PROCESSOR_OUT_THREAD_COUNT", "1")
    conn.commit()

    cur.execute(
        """
        UPDATE apps.fnd_svc_components
           SET component_status='STOPPED',
               last_update_date=SYSDATE,
               last_updated_by=0
         WHERE component_id=:c
        """,
        c=COMPONENT_ID,
    )
    conn.commit()
    print("SQL STOPPED", status(cur)[0], flush=True)
    time.sleep(10)

    ret, err = cur.var(oracledb.DB_TYPE_NUMBER), cur.var(oracledb.DB_TYPE_VARCHAR)
    cur.execute(
        """
        BEGIN
          fnd_global.apps_initialize(0,20420,1);
          apps.fnd_svc_component.start_component(
            p_component_id=>:cid, p_retcode=>:r, p_errbuf=>:e);
        END;
        """,
        cid=COMPONENT_ID,
        r=ret,
        e=err,
    )
    conn.commit()
    print("start ret", ret.getvalue(), err.getvalue(), flush=True)

    final = None
    for i in range(36):
        time.sleep(5)
        st, info = status(cur)
        print(f"t+{(i+1)*5}s {st}", flush=True)
        final = st
        if st in ("RUNNING", "STOPPED_ERROR", "DEACTIVATED_SYSTEM"):
            break

    print("AFTER", status(cur)[0], "jvm", ssh(PS) or "NONE", flush=True)
    cur.close()
    conn.close()
    print("OK" if final == "RUNNING" else "FAIL", flush=True)
    return 0 if final == "RUNNING" else 1


if __name__ == "__main__":
    raise SystemExit(main())

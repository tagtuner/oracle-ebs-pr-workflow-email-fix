#!/usr/bin/env python3
"""Render dark-terminal PNGs from sanitized session transcripts (no secrets)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / "docs" / "mailer-smtp-ecx-restore-2026-10" / "assets"

FRAMES = {
    "01-auth-probe.png": """$ python apply_mailer_smtp_ecx_restore.py
=== probe 587 AUTH from apps ===
auth_probe: OK
""",
    "02-ecx-encrypt-roundtrip.png": """=== ECX encrypt + roundtrip ===
enc_len=92 prefix='V1:****'
roundtrip: OK
""",
    "03-jvm-bounce.png": """=== JVM kill first ===
OLD_JVM 42093
wait_jvm 30s pid=none
wait_jvm 60s pid=none
NEW_JVM 74405
status after kill ('STARTING', ' ')
""",
    "04-params-set.png": """SET OUTBOUND_SERVER='mail.example.com' rows=1
SET OUTBOUND_PROTOCOL='SMTP' rows=1
SET OUTBOUND_SECURE_PROTOCOL='TLS' rows=1
SET OUTBOUND_AUTH_TYPE='BASIC' rows=1
SET OUTBOUND_USER='workflow.mailer@example.com' rows=1
SET OUTBOUND_PASSWORD=ENC_LEN_92 rows=1
SET MAILER_SSL_TRUSTSTORE='.../jre/lib/security/cacerts' rows=1
SET INBOUND_PASSWORD=ENC_LEN_92 rows=1
SET PROCESSOR_IN_THREAD_COUNT='0' rows=1
SET PROCESSOR_OUT_THREAD_COUNT='1' rows=1
SQL STOPPED STOPPED
""",
    "05-start-running.png": """start ret 7001 The specified action is invalid given the Component's current status.
t+5s STARTING
t+10s STARTING
t+15s STARTING
t+20s RUNNING
pwd_form [('OUTBOUND_PASSWORD', 'ENC_LEN_92'), ('INBOUND_PASSWORD', 'ENC_LEN_92')]
AFTER RUNNING jvm 74405
OK
""",
    "06-status-ro.png": """$ python ro_mailer_status.py
status RUNNING upd 09-OCT 17:22:51
info
('OUTBOUND_PASSWORD', 'V1_ENCRYPTED')
('INBOUND_PASSWORD', 'V1_ENCRYPTED')
('OUTBOUND_SECURE_PROTOCOL', 'TLS')
('OUTBOUND_AUTH_TYPE', 'BASIC')
""",
}


def font(size: int = 15):
    for name in (
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/CascadiaMono.ttf",
        "C:/Windows/Fonts/lucon.ttf",
    ):
        p = Path(name)
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def render(text: str, path: Path) -> None:
    lines = text.strip("\n").splitlines() or [""]
    f = font(15)
    pad_x, pad_y, line_h = 22, 22, 22
    # measure
    widths = []
    for ln in lines:
        bbox = f.getbbox(ln if ln else " ")
        widths.append(bbox[2] - bbox[0])
    w = max(widths + [640]) + pad_x * 2
    h = pad_y * 2 + line_h * len(lines) + 36
    img = Image.new("RGB", (w, h), (12, 16, 24))
    draw = ImageDraw.Draw(img)
    # title bar
    draw.rectangle((0, 0, w, 28), fill=(30, 36, 48))
    draw.text((14, 6), "ebs-apps · mailer restore · sanitized", fill=(160, 170, 190), font=font(12))
    y = 36
    for ln in lines:
        color = (200, 210, 220)
        if ln.startswith("$") or ln.startswith("==="):
            color = (120, 200, 255)
        elif "OK" in ln or "RUNNING" in ln or "roundtrip: OK" in ln or "auth_probe: OK" in ln:
            color = (80, 220, 140)
        elif "FAIL" in ln or "ABORT" in ln:
            color = (255, 100, 100)
        elif "ENC_LEN" in ln or "V1" in ln or "PASSWORD" in ln:
            color = (240, 200, 100)
        draw.text((pad_x, y), ln, fill=color, font=f)
        y += line_h
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG")
    print("wrote", path)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, text in FRAMES.items():
        render(text, OUT / name)
    print("done", len(FRAMES), "pngs ->", OUT)


if __name__ == "__main__":
    main()

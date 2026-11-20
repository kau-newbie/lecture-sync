#!/usr/bin/env python3
"""Gmail로 알림 메일을 보낸다.

사용: notify.py --to 주소 --subject 제목 --body-file 본문.txt [--dry-run]

환경 변수:
  GMAIL_APP_PASSWORD  필수. Gmail 앱 비밀번호(16자리). 값을 출력하거나 기록하지 않는다.
  GMAIL_USER          발신 계정. 기본값은 --to 와 같은 주소.
비밀번호가 없으면 종료 코드 3으로 끝난다.
"""
import argparse
import os
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--body-file", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    body = Path(a.body_file).read_text(encoding="utf-8")
    sender = os.environ.get("GMAIL_USER") or a.to
    msg = EmailMessage()
    msg["Subject"] = a.subject
    msg["From"] = sender
    msg["To"] = a.to
    msg.set_content(body)

    if a.dry_run:
        print(f"[dry-run] 받는 사람: {a.to}\n제목: {a.subject}\n\n{body}")
        return
    password = os.environ.get("GMAIL_APP_PASSWORD")
    if not password:
        print("GMAIL_APP_PASSWORD가 설정되지 않아 발송하지 않았습니다.", file=sys.stderr)
        sys.exit(3)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as s:
            s.login(sender, password)
            s.send_message(msg)
    except (smtplib.SMTPException, OSError) as e:
        print(f"발송 실패: {type(e).__name__}", file=sys.stderr)
        sys.exit(4)
    print(f"발송 완료: {a.to}")


if __name__ == "__main__":
    main()

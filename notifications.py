from __future__ import annotations

import base64
import smtplib
import sys
from email import policy as _email_policy
from email.message import EmailMessage

import config
from utils import html_escape, now_utc


def send_notification_email(subject: str, html_body: str, text_body: str = None):
    if not config.SEND_EMAILS:
        print("ℹ️  Envío de emails desactivado (SEND_EMAILS=false). Se omite el envío.")
        return False
    if not all([config.SMTP_HOST, config.SMTP_PORT, config.SMTP_USER, config.SMTP_PASS, config.FROM_EMAIL, config.TO_EMAIL]):
        print("⚠️  Faltan variables SMTP para enviar el correo. Se omite el envío.")
        return False
    try:
        msg = EmailMessage(policy=_email_policy.SMTP)
        msg["Subject"] = subject
        msg["From"] = config.FROM_EMAIL
        msg["To"] = config.TO_EMAIL
        text_body = text_body or "Notificación del proceso."
        msg.set_content(text_body, charset="utf-8")
        msg.add_alternative(html_body, subtype="html", charset="utf-8")
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT,
                          local_hostname="localhost") as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            try:
                smtp.login(config.SMTP_USER, config.SMTP_PASS)
            except UnicodeEncodeError:
                auth = f"\0{config.SMTP_USER}\0{config.SMTP_PASS}".encode("utf-8")
                auth_b64 = base64.b64encode(auth).decode("ascii")
                code, resp = smtp.docmd("AUTH", f"PLAIN {auth_b64}")
                if code != 235:
                    raise smtplib.SMTPAuthenticationError(code, resp)
            smtp.send_message(msg)
        print(f"📧 Notificación enviada a {config.TO_EMAIL}: {subject}")
        return True
    except Exception as e:
        print(f"❌ Error enviando el correo: {e}", file=sys.stderr)
        return False

def notify(subject: str, message: str, level: str = "info", always_email: bool = True):
    """
    Centraliza impresión y envío de email. Si NOTIFY_VERBOSE es False,
    sólo envía emails para level in ['error','warning'] salvo que always_email=True.
    """
    stamp = now_utc().isoformat()
    prefix = {"info":"ℹ️","success":"✅","warning":"⚠️","error":"❌"}.get(level, "ℹ️")
    line = f"{prefix} [{stamp}] {subject} :: {message}"
    print(line)
    should_email = always_email or config.NOTIFY_VERBOSE or (level in ("error","warning"))
    if should_email:
        html = f"<p><b>{html_escape(subject)}</b></p><p>{html_escape(message)}</p><p><small>{stamp} UTC</small></p>"
        send_notification_email(subject=f"[{level.upper()}] {subject}", html_body=html, text_body=f"{subject}\n\n{message}\n\n{stamp} UTC")

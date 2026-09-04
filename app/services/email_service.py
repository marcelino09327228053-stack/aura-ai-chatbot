"""Transactional email delivery with SMTP and a local-development fallback."""

import os
import smtplib
from email.message import EmailMessage

from app.core.config import get_aura_env


def send_login_code(email: str, code: str) -> bool:
    host = os.getenv("SMTP_HOST", "").strip()
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("SMTP_FROM_EMAIL", username).strip()

    if not host or not sender:
        if get_aura_env() == "production":
            raise RuntimeError("Email delivery is not configured.")
        return False

    message = EmailMessage()
    message["Subject"] = "Your MB Future Tech AI Chatbot confirmation code"
    message["From"] = sender
    message["To"] = email
    message.set_content(
        f"Your MB Future Tech AI Chatbot confirmation code is {code}.\n\n"
        "This code expires in 10 minutes. If you did not request it, ignore this email."
    )

    port = int(os.getenv("SMTP_PORT", "587"))
    use_ssl = os.getenv("SMTP_USE_SSL", "false").lower() in ("1", "true", "yes")
    if use_ssl:
        with smtplib.SMTP_SSL(host, port, timeout=15) as smtp:
            if username:
                smtp.login(username, password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.starttls()
            if username:
                smtp.login(username, password)
            smtp.send_message(message)
    return True

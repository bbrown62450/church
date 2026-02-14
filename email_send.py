#!/usr/bin/env python3
"""
Send email via Gmail SMTP (e.g. secretary doc + message).
Uses GMAIL_ADDRESS and GMAIL_APP_PASSWORD from env.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional


def send_gmail(
    to_email: str,
    subject: str,
    body_plain: str,
    *,
    attachment_bytes: Optional[bytes] = None,
    attachment_filename: Optional[str] = None,
) -> Optional[str]:
    """
    Send an email via Gmail SMTP. Returns None on success, or an error message string on failure.
    """
    from_addr = os.getenv("GMAIL_ADDRESS")
    password = os.getenv("GMAIL_APP_PASSWORD")
    if not from_addr or not password:
        return "Gmail not configured. Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env"
    to_email = (to_email or "").strip()
    if not to_email:
        return "Recipient email is required."

    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body_plain, "plain"))

    if attachment_bytes and attachment_filename:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment_bytes)
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            "attachment",
            filename=attachment_filename,
        )
        msg.attach(part)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(from_addr, password)
            server.sendmail(from_addr, to_email, msg.as_string())
        return None
    except Exception as e:
        return str(e)

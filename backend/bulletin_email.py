"""The bulletin email itself (slice 5b spec, "service_output.py additions",
amended 2026-10-06; slice 5b-2). Pure: no database, no network, no FastAPI,
Starlette or Streamlit.

- bulletin_email_subject: "Worship service for October 4, 2026" (the printed
  bulletin's date form, no zero padding; owner answer 5).
- default_bulletin_message: "Hi! Here's the worship bulletin for this Sunday.",
  or "... for Wednesday, February 10." for a service on another day. The
  dialog prefills it, and a message left blank is sent as it.
- plan_bulletin_addressing: one recipient is in To; two or more are in Bcc
  with the sender in To (owner decision 9), the sender never twice.
- compose_bulletin_email: the plain-text message with its attachments (the
  bulletin copy's Word file and/or the printed bulletin's PDF).
Every header holds only addresses email_addresses.normalize_address accepted
and strings built here, so there is no header injection.
The shared fixture tests/fixtures/shared/bulletin_email.json pins the subject
and the message for frontend/src/lib/email.ts too.
"""
from __future__ import annotations

import datetime
from collections.abc import Sequence
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Optional

from printed_bulletin import printed_date
from service_output import MONTHS

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
BULLETIN_EMAIL_FALLBACK = "Hi! Here's the worship bulletin for this Sunday."


@dataclass(frozen=True)
class Addressing:
    to: tuple[str, ...]
    bcc: tuple[str, ...]


@dataclass(frozen=True)
class Attachment:
    content: bytes
    filename: str
    mime_type: str


def bulletin_email_subject(d: datetime.date) -> str:
    return f"Worship service for {printed_date(d)}"


def default_bulletin_message(d: datetime.date) -> str:
    if d.weekday() == 6:
        return BULLETIN_EMAIL_FALLBACK
    return f"Hi! Here's the worship bulletin for {WEEKDAYS[d.weekday()]}, {MONTHS[d.month - 1]} {d.day}."


def plan_bulletin_addressing(sender: str, recipients: Sequence[str]) -> Addressing:
    """`sender` and `recipients` already through normalize_address, the
    recipients without duplicates; the sender is left out of Bcc ignoring case."""
    if len(recipients) == 1:
        return Addressing(to=(recipients[0],), bcc=())
    me = sender.strip().lower()
    return Addressing(to=(sender,), bcc=tuple(r for r in recipients if r.strip().lower() != me))


def compose_bulletin_email(*, sender: str, recipients: Sequence[str], service_date: datetime.date,
                           message: Optional[str], attachments: Sequence[Attachment]) -> EmailMessage:
    plan = plan_bulletin_addressing(sender, recipients)
    composed = EmailMessage()
    composed["From"] = sender
    composed["To"] = ", ".join(plan.to)
    if plan.bcc:
        composed["Bcc"] = ", ".join(plan.bcc)
    composed["Subject"] = bulletin_email_subject(service_date)
    composed.set_content((message or "").strip() or default_bulletin_message(service_date))
    for attachment in attachments:
        maintype, subtype = attachment.mime_type.split("/", 1)
        composed.add_attachment(attachment.content, maintype=maintype, subtype=subtype, filename=attachment.filename)
    return composed

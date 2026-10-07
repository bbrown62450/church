"""POST /bulletin-emails: email the bulletin from the caller's own Gmail
(slice 5b spec, API; owner's 5b answers of 2026-10-06; slice 5b-2).

Church-scoped; any member may send (owner decision 5). The body is the
service as it is on screen (built into the files on the server, never
uploaded), the chosen contacts by id and any other addresses, the message,
the attachments ("docx": the bulletin copy, "pdf": the printed bulletin; at
least one) and, for the PDF, the draft's translation, as POST
/documents/printed takes it.

An Idempotency-Key is required. FastAPI runs the dependencies in the order
declared (sign-in and church, then the key) and checks the body after them;
run_idempotent comes next, then the usecase's own order. A retry with the
same key and body gets the first answer: the success, any 4xx, and an
answer that says the email may already have been sent (details.send_uncertain,
kept by `store_error`), so a lost connection or a second tap never sends twice.
The `email` bucket (10 an hour) is charged inside the usecase right before
Google, so a typo, a missing contact or a replay costs nothing; the PDF's
readings charge the `scripture` bucket as the printed download does. Plain
`def`, one usecase call, no SQL and no try/except (F §2.2 rule 1).
"""
import uuid
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from api import ratelimit
from api.deps import ActiveChurch, CurrentUser, get_current_user, get_google_config, require_church
from api.errors import error_responses
from api.idempotency import idempotency_key, run_idempotent
from api.schemas import ServiceDraft
from domain_errors import DomainError
from google_oauth import GoogleOAuthConfig
from usecases import email

router = APIRouter()


class BulletinEmailIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: ServiceDraft
    # The list caps only guard the body's size; the usecase applies the 50-recipient rule after de-duplication.
    contact_ids: list[uuid.UUID] = Field(default_factory=list, max_length=200)
    additional_emails: list[Annotated[str, StringConstraints(max_length=320)]] = Field(default_factory=list,
                                                                                       max_length=200)
    message: Optional[str] = Field(default=None, max_length=5000)
    attachments: list[Literal["docx", "pdf"]] = Field(max_length=2, description="docx: the bulletin copy; "
                                                      "pdf: the printed bulletin. At least one.")
    # The printed bulletin's readings print in it when this deployment offers it, else in the church's.
    translation: Optional[Annotated[str, StringConstraints(strip_whitespace=True, max_length=20)]] = None


class BulletinEmailOut(BaseModel):
    sent: Literal[True]
    recipient_count: int


def _maybe_sent(error: DomainError) -> bool:
    """Keep an answer that says the email may already have gone out."""
    return bool((error.details or {}).get("send_uncertain"))


@router.post("/bulletin-emails", response_model=BulletinEmailOut,
             responses=error_responses(401, 403, 404, 409, 422, 429, 502, 503, 504))
def send_bulletin_email(
    payload: BulletinEmailIn,
    church: ActiveChurch = Depends(require_church),
    user: CurrentUser = Depends(get_current_user),
    key: Optional[uuid.UUID] = Depends(idempotency_key(required=True)),
    config: GoogleOAuthConfig = Depends(get_google_config),
) -> Response:
    return run_idempotent(
        user_id=user.id, church_id=church.id, route="/bulletin-emails", key=key, payload=payload, status_code=200,
        store_error=_maybe_sent,
        call=lambda: BulletinEmailOut(sent=True, recipient_count=email.send_bulletin_email(
            church.id, user.id, payload.service.to_input(), contact_ids=payload.contact_ids,
            additional_emails=payload.additional_emails, message=payload.message, attachments=payload.attachments,
            translation=payload.translation, config=config,
            charge=lambda: ratelimit.consume("email", user_id=user.id),
            charge_scripture=lambda parts: ratelimit.consume("scripture", user_id=user.id, cost=parts))))

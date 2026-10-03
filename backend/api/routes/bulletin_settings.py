"""GET and PUT /church/bulletin-settings (printed bulletin spec, PR 2a; PR 2
planning answers 1 and 2): the church's standing bulletin settings, which
every member's printed bulletin uses.

GET: any member (require_church); a church that never saved them reads the
defaults. PUT: admins and owners only (require_admin; a member's PUT is the
role 403 "Only church admins can do this."), the whole object every time
(extra="forbid", every field required), each text trimmed and within its
limit, every text but the Gloria Patri words on one line (no line break, tab
or other control character: a 422 naming the field), the starred elements and the leaders from bulletin_settings'
ELEMENT_KEYS and ROLES. It answers what is stored. No Idempotency-Key (a PUT
of the same body stores the same value) and no If-Match: the later of two
saves wins (plan clarification 6). Plain `def`, no SQL, no try/except
(F §2.2 rule 1).
"""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

import bulletin_settings as bs
from api.deps import ActiveChurch, require_admin, require_church
from api.errors import error_responses
from usecases import church_bulletin

router = APIRouter()

ElementKey = Literal[bs.ELEMENT_KEYS]
Role = Literal[bs.ROLES]


# One printed line: no control character (a line break or a tab would break the cover or the header).
ONE_LINE = r"^[^\x00-\x1f\x7f]*$"


def _text(field: str):
    pattern = None if field == "gloria_patri_words" else ONE_LINE
    return Annotated[str, StringConstraints(strip_whitespace=True, max_length=bs.MAX_LENGTH[field], pattern=pattern)]


class BulletinSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address_lines: list[_text("address_line")] = Field(max_length=bs.MAX_ADDRESS_LINES)
    phone: _text("phone")
    email: _text("email")
    website: _text("website")
    facebook: _text("facebook")
    service_time: _text("service_time")
    worship_leader: _text("person")
    liturgist: _text("person")
    organist: _text("person")
    stand_note: _text("stand_note")
    starred: list[ElementKey] = Field(max_length=len(bs.ELEMENT_KEYS))
    gloria_patri_words: _text("gloria_patri_words")
    leaders: dict[ElementKey, Role]


@router.get("/church/bulletin-settings", response_model=BulletinSettings,
            responses=error_responses(401, 403, 422, 503))
def read_bulletin_settings(church: ActiveChurch = Depends(require_church)) -> BulletinSettings:
    return BulletinSettings(**church_bulletin.get_bulletin_settings(church.id).to_json())


@router.put("/church/bulletin-settings", response_model=BulletinSettings,
            responses=error_responses(401, 403, 422, 503))
def save_bulletin_settings(payload: BulletinSettings,
                           church: ActiveChurch = Depends(require_admin)) -> BulletinSettings:
    return BulletinSettings(**church_bulletin.save_bulletin_settings(church.id, payload.model_dump()).to_json())

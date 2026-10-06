"""/contacts: the church's contacts (slice 5b-1; 5b spec GET /contacts, 6a
spec POST, PATCH and DELETE /contacts).

Every member reads the list (`require_church`); owners and admins add, edit
and delete (`require_admin`, then the role re-read under the church-row lock
in usecases.contacts). Plain `def` routes that each make one usecase call
(F §2.2 rule 1), with no SQL and no try/except. No Idempotency-Key: the
duplicate check runs under the lock, so a double tap or a retry gets a 409,
never a second contact (6a spec, API).
"""
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_admin, require_church
from api.errors import error_responses
from api.schemas import DeletedOut
from usecases import contacts

router = APIRouter()


class ContactOut(BaseModel):
    id: uuid.UUID
    name: str | None = Field(description="null when the stored name is NULL or blank")
    email: str
    email_valid: bool = Field(description="false when the stored address fails the send-time check "
                                          "(email_addresses.normalize_address): an admin should fix it")


class ContactList(BaseModel):
    items: list[ContactOut]


class ContactIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, max_length=200)
    email: str = Field("", max_length=320)        # "" default: the usecase says "Email is required." (F §1.3)


class ContactPatchIn(BaseModel):
    """Omitted = unchanged (model_fields_set); a null or blank name clears it;
    a null or blank email is "Email is required."."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, max_length=200)
    email: str | None = Field(None, max_length=320)


@router.get("/contacts", response_model=ContactList, responses=error_responses(401, 403, 422, 503))
def list_contacts(church: ActiveChurch = Depends(require_church)) -> ContactList:
    return ContactList(items=[ContactOut(**c) for c in contacts.list_contacts(church.id)])


@router.post("/contacts", status_code=201, response_model=ContactOut,
             responses=error_responses(401, 403, 409, 422, 503))
def add_contact(payload: ContactIn, church: ActiveChurch = Depends(require_admin),
                user: CurrentUser = Depends(get_current_user)) -> ContactOut:
    return ContactOut(**contacts.add_contact(church.id, user.id, name=payload.name, email=payload.email))


@router.patch("/contacts/{contact_id}", response_model=ContactOut,
              responses=error_responses(401, 403, 404, 409, 422, 503))
def update_contact(contact_id: uuid.UUID, payload: ContactPatchIn, church: ActiveChurch = Depends(require_admin),
                   user: CurrentUser = Depends(get_current_user)) -> ContactOut:
    return ContactOut(**contacts.update_contact(church.id, user.id, contact_id,
                                                payload.model_dump(include=payload.model_fields_set)))


@router.delete("/contacts/{contact_id}", response_model=DeletedOut,
               responses=error_responses(401, 403, 404, 422, 503))
def delete_contact(contact_id: uuid.UUID, church: ActiveChurch = Depends(require_admin),
                   user: CurrentUser = Depends(get_current_user)) -> DeletedOut:
    contacts.delete_contact(church.id, user.id, contact_id)
    return DeletedOut()

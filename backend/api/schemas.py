"""Request and response models (also documented at /docs)."""
import uuid
from datetime import datetime
from typing import Generic, Literal, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from api.errors import ErrorBody  # noqa: F401  (re-exported: every error response's body, F §1.5)

T = TypeVar("T")


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None


class ChurchOut(BaseModel):
    id: uuid.UUID
    name: str
    role: Literal["owner", "admin", "member"]


class MeOut(BaseModel):
    user: UserOut
    churches: list[ChurchOut]


class Page(BaseModel, Generic[T]):
    """One page of a paginated list (F §1.4): the page's items and the full total."""

    items: list[T]
    total: int
    limit: int
    offset: int


class ItemList(BaseModel, Generic[T]):
    """An unpaginated list (F §1.3): always an object, never a bare array."""

    items: list[T]


class RubricModel(BaseModel):
    hymns: dict[str, list[str]]
    prayers: dict[str, list[str]]
    prefer_before_year: int
    prefer_familiar: bool


class RubricOut(BaseModel):
    rubric: RubricModel
    customized: list[str]


class CreateChurchIn(BaseModel):
    """The body of POST /churches. A blank name or time zone is left to the
    usecase, whose 422 names the field."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field("", max_length=200)
    timezone: str = Field("", max_length=64)


class InviteCodeIn(BaseModel):
    """POST /invites/preview and /invites/accept: the code, only ever in the body (AC9)."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field("", max_length=256)


class InvitePreviewOut(BaseModel):
    """What an invite offers. Never its id, code, church id, creator or bound email (F §7.4)."""

    church_name: str
    role: Literal["member", "admin"]
    expires_at: datetime
    email_bound: bool
    already_member: bool


class InviteAcceptOut(BaseModel):
    church: ChurchOut
    already_member: bool
    message: str

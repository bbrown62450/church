"""Request and response models (also documented at /docs)."""
import re
import uuid
from datetime import date as DateType   # `datetime.date` would be a method here (2a clarification 6)
from datetime import datetime
from typing import Annotated, Generic, Literal, Optional, TypeVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints

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


class ChurchProfileOut(ChurchOut):
    """GET /church: the active church and its profile. A superset of ChurchOut,
    which the church list in GET /me keeps."""

    timezone: str
    timezone_valid: bool                    # an exact, case-sensitive IANA name
    bible_translation: Optional[str]        # the stored default, or null when unset
    effective_translation: str              # the stored default if offered here, else "web"
    effective_translation_label: str        # its label, for when GET /translations fails
    default_hymnal: Optional[str]           # slice 3: the stored default hymnal (read only), or null
    effective_hymnal: Optional[str]         # slice 3: the hymnal the builder opens; null with no hymns


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
    """The body of POST /churches. A blank name, or a blank or unknown time
    zone, passes this model and gets a 422 that names the field."""

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


class TranslationOut(BaseModel):
    id: str
    label: str


class TranslationsOut(BaseModel):
    """GET /translations: the translations this deployment offers, in display
    order. "default" is "web"; "esv" is listed, last, only when it is configured."""

    default: str
    esv_available: bool
    items: list[TranslationOut]


# --- slice 2a: readings (S Schemas) ---

_ISO_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def _iso_date_only(value: object) -> object:
    """Let only a whole YYYY-MM-DD string through to Pydantic's date parsing.

    Pydantic's lax `date` reads "0" as 1970-01-01 and "2026-03-29T00:00:00"
    as its day, which would answer for a date nobody asked about. A string of
    the right shape that is no real date ("2026-02-30") still fails in
    Pydantic's own parsing. Every failure is "Not a valid value." (api/errors.py).
    """
    if isinstance(value, str) and _ISO_DATE.fullmatch(value):
        return value
    raise ValueError("Expected a YYYY-MM-DD date.")


# A strict calendar date for a query parameter; OpenAPI still says `format: date`.
IsoDate = Annotated[DateType, BeforeValidator(_iso_date_only)]


class ReadingSetOut(BaseModel):
    """One set of readings. `scriptures` is in display order (first, psalm,
    second, gospel) with compound cells split; the usecase guarantees 1-20
    lines of 1-200 characters and a name of 1-300 (fits_draft_limits)."""

    name: str
    scriptures: list[str]
    source: Literal["lectio", "vanderbilt", "merged"]


class LectionaryOut(BaseModel):
    """GET /lectionary/readings. `date` echoes the request and is never
    normalized; `partial` means sets were found but one source failed;
    `default_index` is None exactly when `reading_sets` is empty."""

    date: DateType
    status: Literal["ok", "no_readings"]
    partial: bool
    reading_sets: list[ReadingSetOut]
    default_index: Optional[int]


# --- slice 2a: passages (S Schemas; POST /scripture/passages) ---

PartStatus = Literal["ok", "not_found", "unavailable"]


class PassagesIn(BaseModel):
    """POST /scripture/passages. An empty list, a blank ref and more than 20
    parts in all are the usecase's 422s, with its exact messages (S Schemas)."""

    model_config = ConfigDict(extra="forbid")

    refs: list[Annotated[str, StringConstraints(max_length=200)]] = Field(max_length=4)   # the UI sends 1
    translation: str = Field(max_length=20)


class PassageSectionOut(BaseModel):
    """One " or " alternative: `ok` only when every part loaded; `text` joins the
    parts that did, or is null when none did (S Status rules)."""

    reference: str
    status: PartStatus
    text: Optional[str]


class PassageOut(BaseModel):
    """One ref as sent (trimmed), with every section, whatever loaded."""

    reference: str
    status: PartStatus
    sections: list[PassageSectionOut]


class PassagesOut(BaseModel):
    translation: str
    translation_label: str
    passages: list[PassageOut]          # same order as the request's refs


# --- slice 3a: shared hymn and liturgy models (F §1.3, frozen; S "API Models") ---
# Created here because slice 3 lands first. No slice-3 route uses them, so they
# stay out of the OpenAPI snapshot until slice 4 adds a route that does. Slices
# 4 and 5a import them unchanged and never redefine, tighten or loosen them.

SectionKey = Literal["call_to_worship", "opening_prayer", "prayer_of_confession", "assurance",
                     "prayer_for_illumination", "prayers_of_the_people", "offertory_prayer",
                     "benediction"]


class HymnRef(BaseModel):
    """One slot's hymn (F §1.3). hymn_id null = an archived snapshot, used as
    sent; for a non-null id the server reads title, number and hymnal from
    the database and ignores the client's copy."""

    model_config = ConfigDict(extra="forbid")

    hymn_id: Optional[uuid.UUID] = None
    title: str = Field(default="", max_length=300)
    number: Optional[int] = Field(default=None, ge=0, le=100_000)
    # No pattern: a pick echoes hymns.hymnal from the database, and codes written
    # by CLI imports were never pattern-checked (F §1.3).
    hymnal: Optional[str] = Field(default=None, max_length=20)


class SlotHymns(BaseModel):
    """The three hymn slots (F §1.3): slice 4's GenerateLiturgyIn.hymns, 5a's ServiceDraft.hymns."""

    model_config = ConfigDict(extra="forbid")

    opening: Optional[HymnRef] = None
    response: Optional[HymnRef] = None
    closing: Optional[HymnRef] = None


# Only for parameters that name a NEW or admin-managed hymnal code (6a). Never
# on HymnRef and never on slice 3's read filters, which accept any stored code.
HymnalCode = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{2,20}$")]

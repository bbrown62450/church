"""Request and response models (also documented at /docs)."""
import re
import uuid
from datetime import date as DateType   # `datetime.date` would be a method here (2a clarification 6)
from datetime import datetime
from typing import Annotated, Generic, Literal, Optional, TypeVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints

import bulletin_settings
import liturgy_config
import service_bulletin
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
    default_benediction: str                # slice 4: the church's default; full Halverson text when unset or "Halverson"; "" = none


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


# --- slice 4a: the sermon text sent with liturgy requests (F §1.3 amendment
# 2026-09-26; shared with the reviewer add-on's /liturgy/review and /liturgy/revise) ---

class SermonText(BaseModel):
    """The effective NT reading and its passage text (never ESV); the server keeps
    the first 2 000 characters (liturgy_prompts.SERMON_TEXT_LIMIT)."""

    model_config = ConfigDict(extra="forbid")

    ref: str = Field(max_length=200)
    text: str = Field(max_length=20_000)


# --- slice 5a: the service a member builds (5a spec, "Schemas"; shared with 5b's
# POST /bulletin-emails). 5a-1 uses it for POST /documents; 5a-2 for /services. ---

# The 17 placement keys, liturgy_config.CUSTOM_PLACEMENTS' order (= PLACEMENT_KEYS).
Placement = Literal[tuple(key for key, _label in liturgy_config.CUSTOM_PLACEMENTS)]


class CustomElementIn(BaseModel):
    """A custom element as the builder sends it. A label that is blank after
    trimming is the usecase's 422 ("Give each custom element a label.")."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(max_length=liturgy_config.LIMITS.max_custom_label)
    text: str = Field(default="", max_length=liturgy_config.LIMITS.max_custom_text)
    insert_after: Placement


class CustomElementOut(BaseModel):
    """A custom element as a saved service returns it. No input limits or
    extra="forbid": a stored row is shown as read (the usecase normalizes it),
    never rejected on the way out."""

    label: str
    text: str
    insert_after: Placement


# --- printed bulletin PR 2b: the week's bulletin fields (service_bulletin; spec "Data model") ---

def _bulletin_text(name: str):
    return Annotated[str, Field(max_length=service_bulletin.MAX_LENGTH[name])]


class BulletinMusic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: _bulletin_text("title")
    composer: _bulletin_text("composer")


class BulletinPeople(BaseModel):
    """This week's people: null prints the standing name from the bulletin settings, "" no one."""

    model_config = ConfigDict(extra="forbid")

    worship_leader: Optional[_bulletin_text("person")]
    liturgist: Optional[_bulletin_text("person")]
    organist: Optional[_bulletin_text("person")]


class BulletinAnnouncements(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ushers: _bulletin_text("ushers")
    deacon: _bulletin_text("deacon")
    coffee_hour: _bulletin_text("coffee_hour")
    activities: _bulletin_text("activities")
    prayer_concerns: _bulletin_text("prayer_concerns")
    collection: _bulletin_text("collection")
    other: _bulletin_text("other")


class BulletinReadingText(BaseModel):
    """Pasted text of the first and New Testament readings ("" = fetch it)."""

    model_config = ConfigDict(extra="forbid")

    ot: _bulletin_text("reading_text")
    nt: _bulletin_text("reading_text")


class ServiceBulletin(BaseModel):
    """The printed bulletin's weekly fields (PR 2b), every field present. Texts
    are not checked for line breaks: the server reads them tolerantly
    (service_bulletin.read: a one-line field's line breaks become spaces), so a
    download never meets a 422 for one. `unchecked` names the boxes whose text
    came from last week and is not checked yet."""

    model_config = ConfigDict(extra="forbid")

    prelude: BulletinMusic
    postlude: BulletinMusic
    people: BulletinPeople
    leaders: dict[Literal[bulletin_settings.ELEMENT_KEYS], _bulletin_text("person")]
    announcements: BulletinAnnouncements
    reading_text: BulletinReadingText
    # The boxes still holding last week's text, not checked yet (saved, so the marks come back on open).
    unchecked: list[Literal[service_bulletin.CARRY_KEYS]] = Field(max_length=len(service_bulletin.CARRY_KEYS))


class ServiceDraft(BaseModel):
    """One service (inventory §2.1 plus hymnal, F §1.3). The limits are slice
    4's (GenerateLiturgyIn, liturgy_config.LIMITS); HymnRef, SlotHymns and
    SectionKey are imported unchanged. Usecases take `to_input()`.
    `bulletin` (printed bulletin PR 2b) is optional, so a client from before
    2b keeps working: a POST without it saves no bulletin, a PUT without it
    keeps the saved one."""

    model_config = ConfigDict(extra="forbid")

    service_date_iso: IsoDate
    occasion: str = Field(default="", max_length=300)
    scriptures: list[Annotated[str, Field(max_length=200)]] = Field(default_factory=list, max_length=20)
    hymns: SlotHymns = Field(default_factory=SlotHymns)
    # null = the church's effective hymnal (5a-2 stores it); documents ignore it.
    hymnal: Optional[Annotated[str, StringConstraints(strip_whitespace=True, max_length=20)]] = None
    liturgy: dict[SectionKey, Annotated[str, Field(max_length=liturgy_config.LIMITS.max_section_text)]] = Field(
        default_factory=dict)
    sermon_title: str = Field(default="", max_length=liturgy_config.LIMITS.max_sermon_title)
    selected_ot_ref: str = Field(default="", max_length=200)
    selected_nt_ref: str = Field(default="", max_length=200)
    include_communion: bool = False
    custom_elements: list[CustomElementIn] = Field(default_factory=list,
                                                   max_length=liturgy_config.LIMITS.max_custom_elements)
    bulletin: Optional[ServiceBulletin] = None

    def to_input(self):
        """The usecases' copy (usecases.archive.ServiceInput); usecases never import api/*."""
        from service_output import CustomElement
        from usecases.archive import ServiceInput
        from usecases.liturgy import HymnRefData

        def hymn(ref: Optional[HymnRef]) -> Optional[HymnRefData]:
            return None if ref is None else HymnRefData(ref.hymn_id, ref.title, ref.number, ref.hymnal)

        return ServiceInput(
            service_date=self.service_date_iso, occasion=self.occasion, scriptures=tuple(self.scriptures),
            hymns={slot: hymn(getattr(self.hymns, slot)) for slot in ("opening", "response", "closing")},
            hymnal=self.hymnal, liturgy=dict(self.liturgy), sermon_title=self.sermon_title,
            selected_ot_ref=self.selected_ot_ref, selected_nt_ref=self.selected_nt_ref,
            include_communion=self.include_communion,
            custom_elements=tuple(CustomElement(e.label, e.text, e.insert_after) for e in self.custom_elements),
            bulletin=None if self.bulletin is None else service_bulletin.read(self.bulletin.model_dump()))


# --- slice 5a-2: the archive (5a spec, "Schemas"; GET/POST/PUT/DELETE /services) ---

class DeletedOut(BaseModel):
    """DELETE /services/{id}; 6a and 6b reuse it for their deletes."""

    deleted: Literal[True] = True


class AuthorOut(BaseModel):
    """Who first saved a service: the member's name, else their email (owner decision 5)."""

    id: uuid.UUID
    name: str


class ArchivedHymn(BaseModel):
    """A saved slot's hymn. in_hymnal: the hymn is in the church's hymnal now
    (by its id, else by title and number), with its current title, number and
    hymnal; otherwise the stored snapshot, hymn_id null."""

    hymn_id: Optional[uuid.UUID]
    title: str
    number: Optional[int]
    hymnal: Optional[str]
    in_hymnal: bool


class ArchivedHymns(BaseModel):
    """The three slots of a saved service, each always present (null = empty)."""

    opening: Optional[ArchivedHymn]
    response: Optional[ArchivedHymn]
    closing: Optional[ArchivedHymn]


class ServiceOut(BaseModel):
    """A saved service as the builder opens it (GET, POST and PUT /services)."""

    id: uuid.UUID
    service_date_iso: Optional[str]     # YYYY-MM-DD; null for an undated legacy row
    service_date: str                   # the stored display date ("October 04, 2026")
    occasion: str
    scriptures: list[str]
    hymns: ArchivedHymns
    hymnal: Optional[str]
    liturgy: dict[SectionKey, str]
    sermon_title: str
    selected_ot_ref: str
    selected_nt_ref: str
    include_communion: bool
    custom_elements: list[CustomElementOut]
    bulletin: ServiceBulletin           # PR 2b; nothing filled in for a service saved without one
    created_by: Optional[AuthorOut]     # null when the author's account was removed
    saved_at: str                       # ISO 8601 with "+00:00"; send it back as If-Match


class ServiceSummary(BaseModel):
    """One row of GET /services."""

    id: uuid.UUID
    service_date_iso: Optional[str]
    service_date: str
    occasion: str
    sermon_title: str
    saved_at: str
    created_by: Optional[AuthorOut]


class PreviousBulletinOut(BaseModel):
    """GET /services/previous-bulletin (PR 2b, carry forward): the music and the
    announcements of the church's latest service dated before the date (the
    people, part leaders and pasted texts empty), or nulls and an empty
    bulletin when there is none."""

    service_id: Optional[uuid.UUID]
    service_date_iso: Optional[str]
    bulletin: ServiceBulletin

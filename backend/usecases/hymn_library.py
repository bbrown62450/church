"""The church's hymn library in Settings → Hymns (6a spec, `usecases/hymn_library.py`;
slice 6a-2; owner's 6a-2 answers of 2026-10-07).

Any member adds and edits hymns; only owners and admins delete a hymn, set a
hymn's year or familiarity (`text_year`, `hymnal_count`), list the bundled
hymnals, add one, or remove a whole hymnal (never the only one or the
default). Every write opens one session and starts with
usecases.members.lock_and_read_actor (the church-row lock and the caller's
role re-read under it), so a removed member or a deleted church gets
`no_church_access`, an admin demoted meanwhile gets the role 403 on an admin
write, and the duplicate check and the write run under the lock: two members
adding the same hymn at once get one hymn and one 409.

Separate from usecases.hymns (the builder's reads and suggestions). No
FastAPI, Starlette or Streamlit here (usecases/__init__.py).
"""
import re
import uuid
from collections.abc import Mapping
from datetime import date
from typing import Any, Optional

import hymnal_sources
from db import session_scope
from domain_errors import Conflict, InvalidInput, NotFound
from repos import hymns as hymn_repo
from repos.hymns import HymnRecord, title_key
from usecases import hymns
from usecases.church_admin import require_admin_role
from usecases.members import lock_and_read_actor

TITLE_REQUIRED = "Hymn title is required."
NUMBER_INVALID = "Hymn number must be a whole number."
HYMNAL_INVALID = "Choose one of your church's hymnals."
LINK_INVALID = "Links must start with https://."
LINK_SPACES = "Links can't contain spaces."
COUNT_INVALID = "Number of hymnals must be a whole number from 0 to 100000."
HYMN_NOT_FOUND = "Hymn not found."
SOURCE_UNAVAILABLE = "That hymnal isn't available to add."
HYMNAL_NOT_FOUND = "Your church doesn't have that hymnal."
ONLY_HYMNAL = "You can't remove your only hymnal."

MAX_NUMBER = 99999
MAX_COUNT = 100000
# A new church with no hymns adds to Streamlit's hymnal (repos/hymns.py add_hymn's default).
FIRST_HYMNAL = "GG2013"
HYMNAL_CODE = re.compile(r"[A-Za-z0-9_-]{2,20}")
# Control characters (C0, DEL, C1) and the two noncharacters a Word file cannot hold.
_CONTROL = re.compile("[\x00-\x1f\x7f-\x9f\ufffe\uffff]")
_FACTS = ("text_year", "hymnal_count")


def year_message(this_year: int) -> str:
    return f"Year must be a whole number from 1 to {this_year}."


def duplicate_message(hymnal: str, number: Optional[int], title: str) -> str:
    return (f"{hymnal} already has #{number} {title}." if number is not None
            else f"{hymnal} already has {title}.")


def default_message(code: str) -> str:
    return f"{code} is your default hymnal. Choose a different default in Church profile first."


def one_line(value: Optional[str]) -> str:
    """`value` on one line: each control character a space, every run of
    whitespace one space, trimmed ("" for None). A pasted line break or tab is
    tidied, not refused."""
    return " ".join(_CONTROL.sub(" ", value or "").split())


def clean_title(value: Optional[str]) -> str:
    title = one_line(value)
    if not title:
        raise InvalidInput(TITLE_REQUIRED, field="title")
    return title


def clean_number(value: Optional[int]) -> Optional[int]:
    if value is not None and not 1 <= value <= MAX_NUMBER:
        raise InvalidInput(NUMBER_INVALID, field="number")
    return value


def clean_text(value: Optional[str]) -> Optional[str]:
    """Scripture references and themes: one line, blank = None."""
    return one_line(value) or None


def clean_link(value: Optional[str]) -> Optional[str]:
    """Blank = None; otherwise https:// (any case) and something after it, with no space inside."""
    link = (value or "").strip()
    if not link:
        return None
    if any(ch.isspace() or _CONTROL.match(ch) for ch in link):
        raise InvalidInput(LINK_SPACES, field="link")
    if not link.lower().startswith("https://") or len(link) == len("https://"):
        raise InvalidInput(LINK_INVALID, field="link")
    return link


def clean_year(value: Optional[int], *, this_year: int) -> Optional[int]:
    if value is not None and not 1 <= value <= this_year:
        raise InvalidInput(year_message(this_year), field="text_year")
    return value


def clean_count(value: Optional[int]) -> Optional[int]:
    if value is not None and not 0 <= value <= MAX_COUNT:
        raise InvalidInput(COUNT_INVALID, field="hymnal_count")
    return value


def hymn_out(record: HymnRecord) -> dict:
    """HymnDetailOut's fields."""
    return {"id": record.id, "hymnal": record.hymnal, "title": (record.title or "").strip(),
            "number": record.number, "scripture_refs": record.scripture_refs, "theme": record.theme,
            "link": record.link, "text_year": record.text_year, "hymnal_count": record.hymnal_count}


def hymnal_label(code: str) -> Optional[str]:
    """The name shown beside a hymnal code (GET /hymnals' `label`), or None."""
    return hymnal_sources.label_for(code)


def _codes(church_id: uuid.UUID, s) -> list[str]:
    return [summary.code for summary in hymn_repo.hymnal_summaries(church_id, session=s)]


def _chosen_hymnal(church_id: uuid.UUID, requested: Optional[str], s) -> str:
    """POST's hymnal: null or blank = the effective default (FIRST_HYMNAL for a
    church with no hymns). It must be one of the church's hymnals, or, while
    the church has none, any code of 2-20 letters, digits, "_" or "-"."""
    codes = _codes(church_id, s)
    wanted = (requested or "").strip()
    if not wanted:
        return hymns.resolve_default_hymnal(church_id, session=s).effective_hymnal or FIRST_HYMNAL
    if wanted in codes or (not codes and HYMNAL_CODE.fullmatch(wanted)):
        return wanted
    raise InvalidInput(HYMNAL_INVALID, field="hymnal")


def _require_admin_for_facts(role: str, sent: Mapping[str, Any], *, present: bool) -> None:
    """The year and familiarity are admins' (owner, 2026-09-26): on POST a
    non-null value, on PATCH the key itself (null included)."""
    if any((name in sent) if present else (sent.get(name) is not None) for name in _FACTS):
        require_admin_role(role)


def create_hymn(church_id: uuid.UUID, actor_id: uuid.UUID, data: Mapping[str, Any]) -> dict:
    """POST /hymns: `data` has HymnIn's keys (None for each one not sent).
    Checks in the order title, number, hymnal, link, year, count; then the
    duplicate (the same hymnal, number and title words) is a 409."""
    this_year = date.today().year
    with session_scope() as s:
        role = lock_and_read_actor(s, church_id, actor_id)
        _require_admin_for_facts(role, data, present=False)
        values = {
            "title": clean_title(data.get("title")),
            "number": clean_number(data.get("number")),
            "hymnal": _chosen_hymnal(church_id, data.get("hymnal"), s),
            "scripture_refs": clean_text(data.get("scripture_refs")),
            "theme": clean_text(data.get("theme")),
            "link": clean_link(data.get("link")),
            "text_year": clean_year(data.get("text_year"), this_year=this_year),
            "hymnal_count": clean_count(data.get("hymnal_count")),
        }
        if hymn_repo.find_duplicate(church_id, values["hymnal"], values["number"], values["title"], session=s):
            raise Conflict(duplicate_message(values["hymnal"], values["number"], values["title"]))
        return hymn_out(hymn_repo.create_hymn(church_id, values, session=s))


def update_hymn(church_id: uuid.UUID, actor_id: uuid.UUID, hymn_id: uuid.UUID,
                changes: Mapping[str, Any]) -> dict:
    """PATCH /hymns/{id}: only the keys sent. A null title or hymnal is
    refused; a null number, refs, theme, link, year or count clears it. An
    unknown id, or another church's, is a 404 before any field is checked.
    The duplicate check runs only when the hymnal, number or title words
    change and the title is not blank, and leaves the hymn itself out."""
    this_year = date.today().year
    with session_scope() as s:
        role = lock_and_read_actor(s, church_id, actor_id)
        _require_admin_for_facts(role, changes, present=True)
        current = hymn_repo.get_hymn(hymn_id, church_id, session=s)
        if current is None:
            raise NotFound(HYMN_NOT_FOUND)
        clean: dict[str, Any] = {}
        if "title" in changes:
            clean["title"] = clean_title(changes["title"])
        if "number" in changes:
            clean["number"] = clean_number(changes["number"])
        if "hymnal" in changes:
            wanted = (changes["hymnal"] or "").strip()
            if wanted not in _codes(church_id, s):
                raise InvalidInput(HYMNAL_INVALID, field="hymnal")
            clean["hymnal"] = wanted
        for name in ("scripture_refs", "theme"):
            if name in changes:
                clean[name] = clean_text(changes[name])
        if "link" in changes:
            clean["link"] = clean_link(changes["link"])
        if "text_year" in changes:
            clean["text_year"] = clean_year(changes["text_year"], this_year=this_year)
        if "hymnal_count" in changes:
            clean["hymnal_count"] = clean_count(changes["hymnal_count"])
        hymnal = clean.get("hymnal", current.hymnal)
        number = clean.get("number", current.number)
        title = clean.get("title", current.title or "")
        # An old hymn with a blank title (the old app allowed one) is never a duplicate:
        # "GG2013 already has #5 ." would name nothing (plan review M8).
        if (title_key(title)
                and (hymnal, number, title_key(title)) != (current.hymnal, current.number, title_key(current.title))
                and hymn_repo.find_duplicate(church_id, hymnal, number, title, exclude_id=hymn_id, session=s)):
            raise Conflict(duplicate_message(hymnal, number, title))
        return hymn_out(hymn_repo.patch_hymn(hymn_id, church_id, clean, session=s))


def delete_hymn(church_id: uuid.UUID, actor_id: uuid.UUID, hymn_id: uuid.UUID) -> None:
    """DELETE /hymns/{id} (owners and admins; owner, 2026-10-05). Saved
    services keep the hymn as it was saved; a draft that picked it asks for a
    replacement."""
    with session_scope() as s:
        require_admin_role(lock_and_read_actor(s, church_id, actor_id))
        if not hymn_repo.delete_hymn(hymn_id, church_id, session=s):
            raise NotFound(HYMN_NOT_FOUND)


def list_sources(church_id: uuid.UUID) -> list[dict]:
    """GET /hymnal-sources: every hymnal an admin can add, with whether the
    church has it already (`present`)."""
    with session_scope() as s:
        codes = set(_codes(church_id, s))
        bundled = hymnal_sources.list_bundled(session=s)
    return [{"code": b.code, "label": b.label, "hymn_count": b.hymn_count,
             "has_scripture_refs": b.has_scripture_refs, "present": b.code in codes} for b in bundled]


def add_hymnal(church_id: uuid.UUID, actor_id: uuid.UUID, code: str) -> dict:
    """POST /hymnals: import a bundled hymnal (repos.hymns.import_hymns: a hymn
    the church has is kept, only its blanks filled). Adding it again is
    allowed and usually inserts nothing."""
    with session_scope() as s:
        require_admin_role(lock_and_read_actor(s, church_id, actor_id))
        wanted = code.strip()
        try:
            rows = hymnal_sources.rows_for(wanted, session=s)
        except KeyError:
            raise InvalidInput(SOURCE_UNAVAILABLE, field="code") from None
        report = hymn_repo.import_hymns(church_id, wanted, rows, session=s)
    return {"code": wanted, "label": hymnal_sources.label_for(wanted),
            "inserted": report["inserted"], "updated": report["updated"]}


def remove_hymnal(church_id: uuid.UUID, actor_id: uuid.UUID, code: str) -> int:
    """DELETE /hymnals/{code}: delete every hymn of the church in `code` and
    return how many. A code the church lacks is a 404; its only hymnal, or the
    effective default, a 409. Saved services, recent use and drafts are not
    touched."""
    with session_scope() as s:
        require_admin_role(lock_and_read_actor(s, church_id, actor_id))
        codes = _codes(church_id, s)
        if code not in codes:
            raise NotFound(HYMNAL_NOT_FOUND)
        if len(codes) == 1:
            raise Conflict(ONLY_HYMNAL)
        if hymns.resolve_default_hymnal(church_id, session=s).effective_hymnal == code:
            raise Conflict(default_message(code))
        return hymn_repo.delete_hymnal(church_id, code, session=s)

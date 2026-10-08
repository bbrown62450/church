"""GET /hymnals: the active church's hymnals and its default (slice 3 spec,
API row 1 and Models; Backend 3.1-3.2), and the bundled hymnals an admin adds
or a hymnal an admin removes in Settings → Hymns (6a spec, GET
/hymnal-sources, POST /hymnals, DELETE /hymnals/{code}; slice 6a-2). Thin
routes (F §2.2.1): GET /hymnals for any member, the rest for owners and
admins (usecases.hymn_library re-reads the role under the church-row lock)."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, ConfigDict, Field

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_admin, require_church
from api.errors import error_responses
from usecases import hymn_library, hymns

router = APIRouter()


class HymnalOut(BaseModel):
    code: str                          # e.g. "GG2013"
    label: Optional[str] = None        # e.g. "Glory to God (2013)"; null for a code without a known name
    hymn_count: int
    scripture_ref_count: int           # hymns with non-blank scripture_refs


class HymnalListOut(BaseModel):
    items: list[HymnalOut]             # by code, in codepoint order
    default_hymnal: Optional[str]      # churches.settings["default_hymnal"] verbatim, or null
    effective_hymnal: Optional[str]    # default_hymnal if it is in items; else items[0].code; else null


class HymnalSourceOut(BaseModel):
    code: str
    label: Optional[str]
    hymn_count: int
    has_scripture_refs: bool           # false: "Hymns for the readings" and AI suggestions work less well
    present: bool                      # the church has at least one hymn in this hymnal


class HymnalSourceList(BaseModel):
    items: list[HymnalSourceOut]       # by code


class HymnalIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(max_length=20)


class HymnalAddedOut(BaseModel):
    code: str
    label: Optional[str]
    inserted: int                      # hymns added; 0 when the church already had them all
    updated: int                       # hymns the church had whose blank details were filled in


class HymnalRemovedOut(BaseModel):
    deleted: Literal[True] = True
    hymns_deleted: int


@router.get("/hymnals", response_model=HymnalListOut, responses=error_responses(401, 403, 422, 503))
def list_hymnals(church: ActiveChurch = Depends(require_church)) -> HymnalListOut:
    overview = hymns.hymnal_overview(church.id)
    return HymnalListOut(
        items=[HymnalOut(code=i.code, label=hymn_library.hymnal_label(i.code), hymn_count=i.hymn_count,
                         scripture_ref_count=i.scripture_ref_count)
               for i in overview.items],
        default_hymnal=overview.default_hymnal,
        effective_hymnal=overview.effective_hymnal,
    )


@router.get("/hymnal-sources", response_model=HymnalSourceList, responses=error_responses(401, 403, 422, 503))
def list_hymnal_sources(church: ActiveChurch = Depends(require_admin)) -> HymnalSourceList:
    return HymnalSourceList(items=[HymnalSourceOut(**s) for s in hymn_library.list_sources(church.id)])


@router.post("/hymnals", response_model=HymnalAddedOut, responses=error_responses(401, 403, 422, 503))
def add_hymnal(payload: HymnalIn, church: ActiveChurch = Depends(require_admin),
               user: CurrentUser = Depends(get_current_user)) -> HymnalAddedOut:
    """Idempotent: adding a hymnal the church has again inserts nothing new (no Idempotency-Key)."""
    return HymnalAddedOut(**hymn_library.add_hymnal(church.id, user.id, payload.code))


@router.delete("/hymnals/{code}", response_model=HymnalRemovedOut,
               responses=error_responses(401, 403, 404, 409, 422, 503))
def remove_hymnal(code: str = Path(pattern=r"^[A-Za-z0-9_-]{2,20}$"),
                  church: ActiveChurch = Depends(require_admin),
                  user: CurrentUser = Depends(get_current_user)) -> HymnalRemovedOut:
    return HymnalRemovedOut(hymns_deleted=hymn_library.remove_hymnal(church.id, user.id, code))

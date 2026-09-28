"""GET /lectionary/readings: the reading sets for one date (S API, Status rules).

User-scoped: the lectionary is global data, so the route depends on
get_current_user (through the lectionary bucket's dependency) and never on
require_church, and X-Church-Id is ignored (F §1.2). `date` must be a whole
YYYY-MM-DD (IsoDate) and is looked up as itself, never moved to a Sunday.
The bucket's dependency runs before FastAPI validates the query, so a 422
also spends a token, as on POST /churches (F §1.8). Plain `def`: the usecase
blocks on upstream HTTP.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from api.errors import error_responses
from api.ratelimit import rate_limit
from api.schemas import IsoDate, LectionaryOut, ReadingSetOut
from usecases import lectionary

router = APIRouter()


@router.get("/lectionary/readings", response_model=LectionaryOut,
            responses=error_responses(401, 422, 429, 502, 503, 504))
def lectionary_readings(
    on: Annotated[IsoDate, Query(alias="date")],
    _rl: None = Depends(rate_limit("lectionary")),
) -> LectionaryOut:
    result = lectionary.readings_for_date(on)
    return LectionaryOut(
        date=result.date,
        status=result.status,
        partial=result.partial,
        reading_sets=[ReadingSetOut(name=s.name, scriptures=list(s.scriptures), source=s.source)
                      for s in result.reading_sets],
        default_index=result.default_index,
    )

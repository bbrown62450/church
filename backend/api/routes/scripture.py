"""POST /scripture/passages (S API row 3, "Passages", Rate-limit buckets
`scripture`; F §1.8; slice 2a).

The one route that charges its bucket itself, because the cost is the number
of upstream parts and is known only after validation (S; F §1.8). It plans
(a 422 charges nothing), then consumes one `scripture` token per part (a 429
fetches nothing), then loads. Upstream failures never become 5xx: every
passage and section carries its own status. X-Church-Id is ignored.
"""
from fastapi import APIRouter, Depends

from api import ratelimit
from api.deps import CurrentUser, get_current_user
from api.errors import error_responses
from api.schemas import PassageOut, PassageSectionOut, PassagesIn, PassagesOut
from usecases.passages import load_passages, plan_passages

router = APIRouter()


@router.post("/scripture/passages", response_model=PassagesOut,
             responses=error_responses(401, 422, 429, 503))
def scripture_passages(payload: PassagesIn, user: CurrentUser = Depends(get_current_user)) -> PassagesOut:
    plan = plan_passages(payload.refs, payload.translation)
    ratelimit.consume("scripture", user_id=user.id, cost=len(plan.parts))
    result = load_passages(plan)
    return PassagesOut(
        translation=result.translation,
        translation_label=result.translation_label,
        passages=[
            PassageOut(
                reference=passage.reference,
                status=passage.status,
                sections=[PassageSectionOut(reference=s.reference, status=s.status, text=s.text)
                          for s in passage.sections],
            )
            for passage in result.passages
        ],
    )

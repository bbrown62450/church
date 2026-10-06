"""/gmail-connection: the caller's own Gmail connection (slice 5b spec, API;
slice 5b-2).

User-scoped: every route reads only the signed-in user's connection and
ignores X-Church-Id (test_route_guards USER_SCOPED), since one connection
works in every church. Plain `def` routes, each one usecase call, no SQL and
no try/except (F §2.2 rule 1). The Google client comes from get_google_config
(Railway's GOOGLE_* variables; tests override it).

- GET: configured, connected and the Google address.
- POST /auth-url: Google's consent URL with a new single-use state; the page
  sends the browser there in the same tab. Each request stores a state, so
  the `gmail_connect` bucket allows 10 in 10 minutes per user (429 after).
- POST: the code and the state Google sent back to /gmail/callback; 200 with
  the new status, or the 5b spec's error table.
- DELETE: forgets the connection and revokes it at Google (best effort).
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from api.deps import CurrentUser, get_current_user, get_google_config
from api.ratelimit import rate_limit
from api.errors import error_responses
from google_oauth import GoogleOAuthConfig
from usecases import email

router = APIRouter()


class GmailConnectionOut(BaseModel):
    configured: bool = Field(description="false when this deployment has no Google client: nobody can connect")
    connected: bool
    google_email: str | None = Field(description="the connected Google address; null when not connected")


class GmailAuthUrlOut(BaseModel):
    auth_url: str


class GmailConnectIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(max_length=2048)
    state: str = Field(max_length=256)


def _out(status: email.GmailStatus) -> GmailConnectionOut:
    return GmailConnectionOut(configured=status.configured, connected=status.connected,
                              google_email=status.google_email)


@router.get("/gmail-connection", response_model=GmailConnectionOut, responses=error_responses(401, 422, 503))
def get_gmail_connection(user: CurrentUser = Depends(get_current_user),
                         config: GoogleOAuthConfig = Depends(get_google_config)) -> GmailConnectionOut:
    return _out(email.gmail_status(user.id, config))


@router.post("/gmail-connection/auth-url", response_model=GmailAuthUrlOut,
             responses=error_responses(401, 422, 429, 503))
def start_gmail_connect(user: CurrentUser = Depends(get_current_user),
                        config: GoogleOAuthConfig = Depends(get_google_config),
                        _limit: None = Depends(rate_limit("gmail_connect"))) -> GmailAuthUrlOut:
    return GmailAuthUrlOut(auth_url=email.start_gmail_connect(user.id, user.email, config))


@router.post("/gmail-connection", response_model=GmailConnectionOut,
             responses=error_responses(400, 401, 422, 502, 503, 504))
def finish_gmail_connect(payload: GmailConnectIn, user: CurrentUser = Depends(get_current_user),
                         config: GoogleOAuthConfig = Depends(get_google_config)) -> GmailConnectionOut:
    return _out(email.finish_gmail_connect(user.id, user.email, payload.code, payload.state, config))


@router.delete("/gmail-connection", response_model=GmailConnectionOut, responses=error_responses(401, 422, 503))
def disconnect_gmail(user: CurrentUser = Depends(get_current_user),
                     config: GoogleOAuthConfig = Depends(get_google_config)) -> GmailConnectionOut:
    return _out(email.disconnect_gmail(user.id, config))

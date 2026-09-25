"""Request guards: who is calling (get_current_user) and for which church
(require_church). Every church-scoped route must depend on require_church."""
import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from fastapi import Depends, Header

from api.errors import auth_unavailable, forbidden, unauthenticated
from api.security import (
    AuthUnavailable,
    InvalidToken,
    TokenVerifier,
    claims_to_profile,
    jwks_key_resolver,
)
from api.settings import get_settings
from auth import upsert_from_claims
from tenancy import is_admin, validate_active_church


@dataclass(frozen=True)
class CurrentUser:
    id: uuid.UUID
    email: str
    name: Optional[str]
    picture: Optional[str]


@dataclass(frozen=True)
class ActiveChurch:
    id: uuid.UUID
    name: str
    role: str


@lru_cache
def get_verifier() -> TokenVerifier:
    settings = get_settings()
    if not settings.supabase_url:
        # Misconfigured deploy: fail closed with a clear 503 (not cached, so a
        # fixed environment takes effect on the next restart).
        raise auth_unavailable()
    return TokenVerifier(jwks_key_resolver(settings.jwks_url), issuer=settings.token_issuer)


def _bearer_token(authorization: Optional[str]) -> str:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise unauthenticated()
    return token.strip()


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    verifier: TokenVerifier = Depends(get_verifier),
) -> CurrentUser:
    token = _bearer_token(authorization)
    try:
        claims = verifier.verify(token)
    except AuthUnavailable:
        raise auth_unavailable() from None
    except InvalidToken:
        raise unauthenticated() from None
    profile = claims_to_profile(claims)
    try:
        user_id = upsert_from_claims(profile)
    except ValueError:  # token carried no email
        raise unauthenticated() from None
    return CurrentUser(
        id=user_id,
        email=profile["email"].strip().lower(),
        name=profile["name"],
        picture=profile["picture"],
    )


def require_church(
    user: CurrentUser = Depends(get_current_user),
    x_church_id: Optional[str] = Header(default=None),
) -> ActiveChurch:
    validated = validate_active_church(x_church_id, user.id)
    if validated is None:
        raise forbidden()
    return ActiveChurch(id=validated["church_id"], name=validated["name"], role=validated["role"])


def require_admin(church: ActiveChurch = Depends(require_church)) -> ActiveChurch:
    if not is_admin(church.role):
        raise forbidden("Only church admins can do this.")
    return church

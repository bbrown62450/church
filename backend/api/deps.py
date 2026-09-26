"""Request guards: who is calling (get_current_user) and for which church
(require_church). Every church-scoped route must depend on require_church."""
import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from fastapi import Depends, Header

from api.errors import auth_unavailable, forbidden, unauthenticated
from api.identity_cache import CachedIdentity, IdentityCache
from api.security import (
    AuthUnavailable,
    InvalidToken,
    TokenVerifier,
    claims_to_profile,
    jwks_key_resolver,
)
from api.settings import get_settings
from repos.users import ensure_user
from tenancy import is_admin, validate_active_church

# Normalized email -> the user id and profile last written (F §2.4). Read as a
# module attribute on every call, so tests can swap in one on a fake clock.
_identity_cache = IdentityCache(maxsize=1024, ttl=300)


def clear_identity_cache() -> None:
    """Forget every cached identity (tests; see backend/tests/conftest.py)."""
    _identity_cache.clear()


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
    email = (profile["email"] or "").strip().lower()
    if not email:  # token carried no email
        raise unauthenticated()
    user_id = _user_id_for(email, _clean(profile["name"]), _clean(profile["picture"]))
    return CurrentUser(id=user_id, email=email, name=profile["name"], picture=profile["picture"])


def _clean(value: Optional[str]) -> Optional[str]:
    return (value or "").strip() or None


def _user_id_for(email: str, name: Optional[str], picture: Optional[str]) -> uuid.UUID:
    """The caller's user id: from the cache when the profile is unchanged, else ensure_user.

    Token verification has already run: it runs on every request and is never
    cached. Tenancy (require_church) is never cached either.
    """
    cache = _identity_cache
    cached = cache.get(email)
    if cached is not None and name in (None, cached.name) and picture in (None, cached.picture):
        return cached.user_id                       # no database work for identity
    row = ensure_user(email, name, picture)         # never google_sub (security.claims_to_profile)
    cache.put(email, CachedIdentity(user_id=row.id, name=row.name, picture=row.picture))
    return row.id


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

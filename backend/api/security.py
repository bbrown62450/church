"""Verify Supabase access tokens and map them to our identity claims.

Supabase signs access tokens with an asymmetric key and publishes the public
keys at {SUPABASE_URL}/auth/v1/.well-known/jwks.json. We verify signature,
expiry, audience and issuer, and accept only Google sign-ins: users are keyed
by email, so a password signup using someone else's address must never pass.
"""
from typing import Any, Callable

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError, PyJWKSetError

ALGORITHMS = ["RS256", "ES256"]

# Tolerate small clock differences between us and Supabase so a token whose
# `iat` is a second or two ahead of our clock isn't rejected as "not yet valid".
LEEWAY_SECONDS = 30

KeyResolver = Callable[[str], Any]


class InvalidToken(Exception):
    """Missing, malformed, forged, expired, or not a Google sign-in."""


class AuthUnavailable(Exception):
    """The signing keys could not be fetched. Callers must fail closed."""


def jwks_key_resolver(jwks_url: str) -> KeyResolver:
    """Resolve a token's key from Supabase's JWKS (cached; refetched on unknown kid).

    PyJWKClient forces a refresh from the endpoint when it sees an unknown
    `kid` (subject to its refetch cooldown), so a just-rotated Supabase
    signing key may briefly be rejected with a 401 until that refresh fires.

    We first fetch the signing key set on its own (`get_signing_keys`, which
    reads from PyJWKClient's cache when warm — no extra network call) so a
    malformed or unusable JWKS response (not a JSON object, or no keys
    usable for signing) is reported as a server-side outage before we ever
    look at the token's `kid`. Only then do we look up the key for this
    token's `kid`, so an unknown `kid` or malformed token still surfaces as
    a per-token failure to `verify`, not an outage.
    """
    client = PyJWKClient(jwks_url, cache_keys=True)

    def resolve(token: str):
        try:
            client.get_signing_keys()
        except (PyJWKClientError, PyJWKSetError, ValueError) as exc:
            raise AuthUnavailable(str(exc)) from exc
        return client.get_signing_key_from_jwt(token).key

    return resolve


class TokenVerifier:
    def __init__(self, key_resolver: KeyResolver, issuer: str, audience: str = "authenticated"):
        self._resolve_key = key_resolver
        self._issuer = issuer
        self._audience = audience

    def verify(self, token: str) -> dict:
        try:
            key = self._resolve_key(token)
        except PyJWKClientConnectionError as exc:
            raise AuthUnavailable(str(exc)) from exc
        except (PyJWKSetError, ValueError) as exc:
            # `jwks_key_resolver`'s resolver already converts a malformed or
            # unusable JWKS response into `AuthUnavailable` itself, before
            # this point. This clause is a safety net for any other
            # `key_resolver` that raises PyJWKSetError/ValueError directly
            # (e.g. one built straight on PyJWKClient without that check) —
            # such a failure is still Supabase's outage, not the caller's,
            # so fail closed the same way as a connection failure.
            raise AuthUnavailable(str(exc)) from exc
        except (PyJWKClientError, jwt.PyJWTError) as exc:
            # A per-token failure: no key matches this token's `kid`, or the
            # token itself is malformed. `AuthUnavailable` raised inside a
            # resolver (e.g. `jwks_key_resolver`'s) is a different exception
            # type and passes through this clause untouched.
            raise InvalidToken(str(exc)) from exc
        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=ALGORITHMS,
                audience=self._audience,
                issuer=self._issuer,
                leeway=LEEWAY_SECONDS,
                options={"require": ["exp", "sub", "aud", "iss"]},
            )
        except jwt.PyJWTError as exc:
            raise InvalidToken(str(exc)) from exc
        if (claims.get("app_metadata") or {}).get("provider") != "google":
            raise InvalidToken("Only Google sign-in is allowed.")
        email = claims.get("email")
        if not isinstance(email, str) or not email.strip():
            raise InvalidToken("Token has no email.")
        return claims


def claims_to_profile(claims: dict) -> dict:
    """Shape Supabase claims for auth.upsert_from_claims.

    `sub` is always None: `user_metadata` is editable by the signed-in user
    (it's account metadata, not an identity claim we control), so it must
    never be trusted as a source of identity. `google_sub` is only used to
    key rows created by the old Streamlit login, not for lookups here, so
    `auth.upsert_from_claims` simply leaves it alone (it only writes
    `google_sub` when `sub` is truthy) and those rows keep the value
    Streamlit stored. `name` and `picture` stay sourced from
    `user_metadata` because they're display-only, not used for identity.
    """
    meta = claims.get("user_metadata") or {}
    return {
        "email": claims.get("email"),
        "sub": None,
        "name": meta.get("full_name") or meta.get("name"),
        "picture": meta.get("avatar_url") or meta.get("picture"),
    }

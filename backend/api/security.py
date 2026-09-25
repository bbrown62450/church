"""Verify Supabase access tokens and map them to our identity claims.

Supabase signs access tokens with an asymmetric key and publishes the public
keys at {SUPABASE_URL}/auth/v1/.well-known/jwks.json. We verify signature,
expiry, audience and issuer, and accept only Google sign-ins: users are keyed
by email, so a password signup using someone else's address must never pass.
"""
from typing import Any, Callable

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError

ALGORITHMS = ["RS256", "ES256"]

KeyResolver = Callable[[str], Any]


class InvalidToken(Exception):
    """Missing, malformed, forged, expired, or not a Google sign-in."""


class AuthUnavailable(Exception):
    """The signing keys could not be fetched. Callers must fail closed."""


def jwks_key_resolver(jwks_url: str) -> KeyResolver:
    """Resolve a token's key from Supabase's JWKS (cached; refetched on unknown kid)."""
    client = PyJWKClient(jwks_url, cache_keys=True)

    def resolve(token: str):
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
        except (PyJWKClientError, jwt.PyJWTError) as exc:
            raise InvalidToken(str(exc)) from exc
        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=ALGORITHMS,
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp", "sub", "aud", "iss"]},
            )
        except jwt.PyJWTError as exc:
            raise InvalidToken(str(exc)) from exc
        if (claims.get("app_metadata") or {}).get("provider") != "google":
            raise InvalidToken("Only Google sign-in is allowed.")
        return claims


def claims_to_profile(claims: dict) -> dict:
    """Shape Supabase claims for auth.upsert_from_claims.

    `sub` is Google's subject id (user_metadata.provider_id), matching what the
    Streamlit login stored in users.google_sub — not Supabase's own user id.
    """
    meta = claims.get("user_metadata") or {}
    return {
        "email": claims.get("email") or meta.get("email"),
        "sub": meta.get("provider_id") or meta.get("sub"),
        "name": meta.get("full_name") or meta.get("name"),
        "picture": meta.get("avatar_url") or meta.get("picture"),
    }

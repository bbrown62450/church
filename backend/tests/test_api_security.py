import json

import jwt
import pytest
from jwt import PyJWKClient
from jwt.algorithms import RSAAlgorithm
from jwt.exceptions import PyJWKClientConnectionError

from api.security import (
    AuthUnavailable,
    InvalidToken,
    TokenVerifier,
    claims_to_profile,
    jwks_key_resolver,
)
from tests.jwt_helpers import ISSUER, SIGNING_KEY, make_token, new_rsa_key


def _verifier():
    return TokenVerifier(lambda _token: SIGNING_KEY.public_key(), issuer=ISSUER)


def test_valid_google_token_returns_claims():
    claims = _verifier().verify(make_token(email="a@b.com"))
    assert claims["email"] == "a@b.com"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"expires_in": -60},
        {"aud": "anon"},
        {"iss": "https://someone-else.supabase.co/auth/v1"},
        {"provider": "email"},
        {"key": new_rsa_key()},
    ],
    ids=["expired", "wrong-audience", "wrong-issuer", "non-google-provider", "bad-signature"],
)
def test_rejects_bad_tokens(kwargs):
    with pytest.raises(InvalidToken):
        _verifier().verify(make_token(**kwargs))


def test_rejects_garbage():
    with pytest.raises(InvalidToken):
        _verifier().verify("not-a-jwt")


def test_rejects_hmac_signed_token():
    """Algorithm confusion: only RS256/ES256 are accepted."""
    forged = jwt.encode(
        {"aud": "authenticated", "iss": ISSUER, "sub": "x", "exp": 9999999999,
         "app_metadata": {"provider": "google"}},
        "x" * 32,
        algorithm="HS256",
    )
    with pytest.raises(InvalidToken):
        _verifier().verify(forged)


def test_tolerates_small_clock_skew():
    """A token whose iat is a few seconds ahead of our clock still verifies."""
    claims = _verifier().verify(make_token(iat_offset=20))
    assert claims["email"] == "pastor@example.com"


def test_rejects_token_missing_top_level_email():
    """Only the Supabase-controlled top-level `email` claim counts, never
    user_metadata.email (which the signed-in user can edit)."""
    token = make_token(email=None)
    claims = jwt.decode(token, options={"verify_signature": False})
    assert "email" not in claims
    assert claims["user_metadata"]["email"] == "pastor@example.com"
    with pytest.raises(InvalidToken):
        _verifier().verify(token)


def test_rejects_token_with_no_exp():
    """A token missing `exp` entirely must be rejected."""
    claims = {
        "sub": "x",
        "aud": "authenticated",
        "iss": ISSUER,
        "email": "pastor@example.com",
        "app_metadata": {"provider": "google"},
    }
    forged = jwt.encode(claims, SIGNING_KEY, algorithm="RS256", headers={"kid": "test-key"})
    with pytest.raises(InvalidToken):
        _verifier().verify(forged)


def test_key_fetch_failure_fails_closed():
    def unreachable(_token):
        raise PyJWKClientConnectionError("jwks down")

    with pytest.raises(AuthUnavailable):
        TokenVerifier(unreachable, issuer=ISSUER).verify(make_token())


def test_jwks_resolver_finds_key_by_kid(monkeypatch):
    jwk = RSAAlgorithm.to_jwk(SIGNING_KEY.public_key(), as_dict=True)
    jwk.update({"kid": "test-key", "alg": "RS256", "use": "sig"})
    monkeypatch.setattr(PyJWKClient, "fetch_data", lambda self: {"keys": [jwk]})
    resolve = jwks_key_resolver("https://test-project.supabase.co/auth/v1/.well-known/jwks.json")
    claims = TokenVerifier(resolve, issuer=ISSUER).verify(make_token())
    assert claims["email"] == "pastor@example.com"


def test_claims_to_profile_maps_google_identity():
    token = make_token(email="p@x.com", google_sub="g-123", name="Pat", picture="https://x/p.png")
    claims = jwt.decode(token, options={"verify_signature": False})
    assert claims_to_profile(claims) == {
        "email": "p@x.com",
        "sub": None,
        "name": "Pat",
        "picture": "https://x/p.png",
    }


def test_jwks_resolver_bad_json_fails_closed(monkeypatch):
    def broken_fetch(self):
        raise json.JSONDecodeError("bad", "", 0)

    monkeypatch.setattr(PyJWKClient, "fetch_data", broken_fetch)
    resolve = jwks_key_resolver("https://test-project.supabase.co/auth/v1/.well-known/jwks.json")
    with pytest.raises(AuthUnavailable):
        TokenVerifier(resolve, issuer=ISSUER).verify(make_token())


def test_jwks_resolver_empty_key_set_fails_closed(monkeypatch):
    monkeypatch.setattr(PyJWKClient, "fetch_data", lambda self: {"keys": []})
    resolve = jwks_key_resolver("https://test-project.supabase.co/auth/v1/.well-known/jwks.json")
    with pytest.raises(AuthUnavailable):
        TokenVerifier(resolve, issuer=ISSUER).verify(make_token())


def test_jwks_resolver_no_matching_kid_is_invalid_token(monkeypatch):
    jwk = RSAAlgorithm.to_jwk(SIGNING_KEY.public_key(), as_dict=True)
    jwk.update({"kid": "other-key", "alg": "RS256", "use": "sig"})
    monkeypatch.setattr(PyJWKClient, "fetch_data", lambda self: {"keys": [jwk]})
    resolve = jwks_key_resolver("https://test-project.supabase.co/auth/v1/.well-known/jwks.json")
    with pytest.raises(InvalidToken):
        TokenVerifier(resolve, issuer=ISSUER).verify(make_token())


def test_jwks_resolver_rejects_garbage_token_as_invalid(monkeypatch):
    jwk = RSAAlgorithm.to_jwk(SIGNING_KEY.public_key(), as_dict=True)
    jwk.update({"kid": "test-key", "alg": "RS256", "use": "sig"})
    monkeypatch.setattr(PyJWKClient, "fetch_data", lambda self: {"keys": [jwk]})
    resolve = jwks_key_resolver("https://test-project.supabase.co/auth/v1/.well-known/jwks.json")
    with pytest.raises(InvalidToken):
        TokenVerifier(resolve, issuer=ISSUER).verify("not-a-jwt")


def test_jwks_resolver_non_object_body_fails_closed(monkeypatch):
    """A JWKS body that is valid JSON but not an object (e.g. `[]`) is a
    malformed-server response, not a per-token problem."""
    monkeypatch.setattr(PyJWKClient, "fetch_data", lambda self: [])
    resolve = jwks_key_resolver("https://test-project.supabase.co/auth/v1/.well-known/jwks.json")
    with pytest.raises(AuthUnavailable):
        TokenVerifier(resolve, issuer=ISSUER).verify(make_token())


def test_jwks_resolver_no_usable_signing_keys_fails_closed(monkeypatch):
    """Every key present but none usable for signing (e.g. all `use: enc`)
    is a server-side outage, not an invalid token."""
    jwk = RSAAlgorithm.to_jwk(SIGNING_KEY.public_key(), as_dict=True)
    jwk.update({"kid": "test-key", "alg": "RS256", "use": "enc"})
    monkeypatch.setattr(PyJWKClient, "fetch_data", lambda self: {"keys": [jwk]})
    resolve = jwks_key_resolver("https://test-project.supabase.co/auth/v1/.well-known/jwks.json")
    with pytest.raises(AuthUnavailable):
        TokenVerifier(resolve, issuer=ISSUER).verify(make_token())


def test_rejects_iat_beyond_leeway():
    """iat 60s in the future exceeds the 30s leeway window."""
    with pytest.raises(InvalidToken):
        _verifier().verify(make_token(iat_offset=60))


def test_accepts_expiry_within_leeway():
    """A token expired 10s ago is still within the 30s leeway."""
    claims = _verifier().verify(make_token(expires_in=-10))
    assert claims["email"] == "pastor@example.com"


def test_rejects_non_string_email():
    """A non-string top-level `email` claim must not crash with AttributeError."""
    claims = {
        "sub": "x",
        "aud": "authenticated",
        "iss": ISSUER,
        "exp": int(__import__("time").time()) + 3600,
        "email": 123,
        "app_metadata": {"provider": "google"},
    }
    forged = jwt.encode(claims, SIGNING_KEY, algorithm="RS256", headers={"kid": "test-key"})
    with pytest.raises(InvalidToken):
        _verifier().verify(forged)


def test_rejects_token_missing_app_metadata():
    """A validly signed token with no `app_metadata` key at all must be rejected."""
    claims = {
        "sub": "x",
        "aud": "authenticated",
        "iss": ISSUER,
        "exp": int(__import__("time").time()) + 3600,
        "email": "pastor@example.com",
    }
    forged = jwt.encode(claims, SIGNING_KEY, algorithm="RS256", headers={"kid": "test-key"})
    with pytest.raises(InvalidToken):
        _verifier().verify(forged)

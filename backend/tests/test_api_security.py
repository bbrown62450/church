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
        "shared-secret",
        algorithm="HS256",
    )
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
        "sub": "g-123",
        "name": "Pat",
        "picture": "https://x/p.png",
    }

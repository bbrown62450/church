"""Mint Supabase-shaped access tokens signed with a local test key."""
import time
import uuid

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

ISSUER = "https://test-project.supabase.co/auth/v1"


def new_rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


SIGNING_KEY = new_rsa_key()


def make_token(
    *,
    email="pastor@example.com",
    provider="google",
    google_sub="google-sub-1",
    name="Pat Tor",
    picture="https://x/p.png",
    aud="authenticated",
    iss=ISSUER,
    expires_in=3600,
    iat_offset=0,
    key=None,
) -> str:
    now = int(time.time())
    claims = {
        "sub": str(uuid.uuid4()),          # Supabase's own user id (not used by us)
        "aud": aud,
        "iss": iss,
        "iat": now + iat_offset,
        "exp": now + expires_in,
        "role": "authenticated",
        "app_metadata": {"provider": provider, "providers": [provider]},
        "user_metadata": {
            "email": email if email is not None else "pastor@example.com",
            "provider_id": google_sub,
            "sub": google_sub,
            "full_name": name,
            "name": name,
            "avatar_url": picture,
            "picture": picture,
        },
    }
    # `email=None` omits the top-level (Supabase-controlled) email claim
    # while user_metadata.email (user-editable) still carries a value, so
    # tests can exercise "no trustworthy email" without touching user_metadata.
    if email is not None:
        claims["email"] = email
    return jwt.encode(claims, key or SIGNING_KEY, algorithm="RS256", headers={"kid": "test-key"})

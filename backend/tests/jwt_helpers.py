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
    key=None,
) -> str:
    now = int(time.time())
    claims = {
        "sub": str(uuid.uuid4()),          # Supabase's own user id (not used by us)
        "aud": aud,
        "iss": iss,
        "iat": now,
        "exp": now + expires_in,
        "role": "authenticated",
        "email": email,
        "app_metadata": {"provider": provider, "providers": [provider]},
        "user_metadata": {
            "email": email,
            "provider_id": google_sub,
            "sub": google_sub,
            "full_name": name,
            "name": name,
            "avatar_url": picture,
            "picture": picture,
        },
    }
    return jwt.encode(claims, key or SIGNING_KEY, algorithm="RS256", headers={"kid": "test-key"})

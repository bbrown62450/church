import uuid

import pytest
from sqlalchemy import func, select

import auth
from db import session_scope
from db.models import User


def _claims(email="Pastor@Example.com", sub="google-sub-1",
            name="Pat Tor", picture="http://x/p.png"):
    return {"email": email, "sub": sub, "name": name, "picture": picture}


def test_upsert_creates_user_with_normalized_email(tmp_db):
    uid = auth.upsert_from_claims(_claims())
    assert isinstance(uid, uuid.UUID)
    with session_scope() as s:
        user = s.execute(select(User).where(User.id == uid)).scalar_one()
        assert user.email == "pastor@example.com"      # lower-cased
        assert user.google_sub == "google-sub-1"
        assert user.name == "Pat Tor"
        assert user.last_login_at is not None


def test_upsert_is_idempotent_by_normalized_email(tmp_db):
    first = auth.upsert_from_claims(_claims(email="Pastor@Example.com"))
    second = auth.upsert_from_claims(
        _claims(email="pastor@example.com", name="New Name", picture="http://x/q.png")
    )
    assert first == second                              # same row, not a duplicate
    with session_scope() as s:
        count = s.execute(select(func.count()).select_from(User)).scalar_one()
        assert count == 1
        user = s.execute(select(User).where(User.id == first)).scalar_one()
        assert user.name == "New Name"                  # updated in place
        assert user.picture == "http://x/q.png"


def test_upsert_requires_email(tmp_db):
    with pytest.raises(ValueError):
        auth.upsert_from_claims({"email": "  ", "sub": "x"})

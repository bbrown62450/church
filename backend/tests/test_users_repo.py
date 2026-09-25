import uuid

from repos.users import upsert_user, get_user, get_user_by_email


def test_upsert_user_lowercases_and_creates(tmp_db):
    uid = upsert_user(email="Beau.Brown@Example.COM", name="Beau", google_sub="sub-1")
    assert isinstance(uid, uuid.UUID)
    row = get_user(uid)
    assert row["email"] == "beau.brown@example.com"
    assert row["name"] == "Beau"
    assert row["google_sub"] == "sub-1"


def test_upsert_user_is_idempotent_on_normalized_email(tmp_db):
    uid1 = upsert_user(email="a@b.com", name="First")
    uid2 = upsert_user(email="A@B.COM", name="Second", picture="http://x/y.png")
    assert uid1 == uid2
    row = get_user(uid1)
    assert row["name"] == "Second"            # updated in place
    assert row["picture"] == "http://x/y.png"


def test_get_user_by_email_matches_normalized(tmp_db):
    uid = upsert_user(email="Carol@Example.com")
    assert get_user_by_email("carol@example.com")["id"] == uid
    assert get_user_by_email("  CAROL@EXAMPLE.COM ")["id"] == uid


def test_get_user_missing_returns_none(tmp_db):
    assert get_user(uuid.uuid4()) is None
    assert get_user_by_email("nobody@example.com") is None


def test_upsert_user_rejects_empty_email(tmp_db):
    import pytest
    with pytest.raises(ValueError):
        upsert_user(email="   ")

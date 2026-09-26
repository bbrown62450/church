import uuid

import pytest

from repos.users import UserRow, ensure_user, get_user, get_user_by_email


def test_ensure_user_lowercases_and_creates(tmp_db):
    row = ensure_user("Beau.Brown@Example.COM", "Beau", google_sub="sub-1")
    assert isinstance(row, UserRow)
    assert isinstance(row.id, uuid.UUID)
    stored = get_user(row.id)
    assert stored["email"] == "beau.brown@example.com"
    assert stored["name"] == "Beau"
    assert stored["google_sub"] == "sub-1"


def test_ensure_user_is_idempotent_on_normalized_email(tmp_db):
    first = ensure_user("a@b.com", "First")
    second = ensure_user("A@B.COM", "Second", "http://x/y.png")
    assert first.id == second.id
    stored = get_user(first.id)
    assert stored["name"] == "Second"            # updated in place
    assert stored["picture"] == "http://x/y.png"


def test_get_user_by_email_matches_normalized(tmp_db):
    uid = ensure_user("Carol@Example.com").id
    assert get_user_by_email("carol@example.com")["id"] == uid
    assert get_user_by_email("  CAROL@EXAMPLE.COM ")["id"] == uid


def test_get_user_missing_returns_none(tmp_db):
    assert get_user(uuid.uuid4()) is None
    assert get_user_by_email("nobody@example.com") is None


def test_ensure_user_rejects_empty_email(tmp_db):
    with pytest.raises(ValueError):
        ensure_user("   ")


def test_upsert_user_is_folded_into_ensure_user():
    # ops spec S14: one identity write path. Its "overwrite when not None" rule
    # is gone; ensure_user overwrites only with truthy values.
    import repos.users

    assert not hasattr(repos.users, "upsert_user")

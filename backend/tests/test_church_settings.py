from contextlib import contextmanager

import pytest
from sqlalchemy import event
from sqlalchemy.dialects import postgresql

from db import SessionLocal
from db.models import Church
from repos.churches import (
    create_church,
    get_church_prompts, set_church_prompts,
    get_church_translation, set_church_translation,
    get_church_rubric, get_church_rubric_overrides, update_church_rubric,
)
from service_rubric import default_rubric


@contextmanager
def _record_church_row_access():
    """Yield (reads, writes): each load of a churches row as (session, locked)
    and each flush that changes one as its session.

    SQLite drops FOR UPDATE from the SQL it runs, so each load is compiled for
    Postgres to see whether it asks for the row lock.
    """
    reads, writes = [], []

    def on_execute(state):
        if state.is_select and any(m.class_ is Church for m in state.all_mappers):
            sql = str(state.statement.compile(dialect=postgresql.dialect()))
            reads.append((state.session, "FOR UPDATE" in sql))

    def on_flush(session, _flush_context, _instances):
        if any(isinstance(obj, Church) for obj in session.dirty):
            writes.append(session)

    event.listen(SessionLocal, "do_orm_execute", on_execute)
    event.listen(SessionLocal, "before_flush", on_flush)
    try:
        yield reads, writes
    finally:
        event.remove(SessionLocal, "do_orm_execute", on_execute)
        event.remove(SessionLocal, "before_flush", on_flush)


def test_prompts_default_empty_then_store_and_reset(tmp_db, make_user):
    owner = make_user(email="o@x.org")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    assert get_church_prompts(cid) == {}

    set_church_prompts(cid, {"system": "My voice.", "benediction": "  ", "bogus": "x"})
    stored = get_church_prompts(cid)
    assert stored == {"system": "My voice."}     # blank dropped, unknown key dropped

    # Clearing a key resets it (blank -> not persisted)
    set_church_prompts(cid, {"system": ""})
    assert get_church_prompts(cid) == {}


def test_translation_default_none_then_set(tmp_db, make_user):
    owner = make_user(email="o2@x.org")
    cid = create_church(name="C2", timezone="UTC", owner_user_id=owner)
    assert get_church_translation(cid) is None
    set_church_translation(cid, "esv")
    assert get_church_translation(cid) == "esv"


def test_settings_keys_are_independent(tmp_db, make_user):
    owner = make_user(email="o3@x.org")
    cid = create_church(name="C3", timezone="UTC", owner_user_id=owner)
    set_church_translation(cid, "kjv")
    set_church_prompts(cid, {"benediction": "Go in peace."})
    # writing prompts must not clobber the translation, and vice versa
    assert get_church_translation(cid) == "kjv"
    assert get_church_prompts(cid) == {"benediction": "Go in peace."}


def test_rubric_defaults_until_edited(tmp_db, make_user):
    cid = create_church(name="R", timezone="UTC", owner_user_id=make_user(email="r@x.org"))
    assert get_church_rubric_overrides(cid) == {}
    assert get_church_rubric(cid) == default_rubric()


def test_rubric_update_stores_only_overrides_and_resets(tmp_db, make_user):
    cid = create_church(name="R2", timezone="UTC", owner_user_id=make_user(email="r2@x.org"))
    merged = update_church_rubric(cid, {"hymns": {"closing": [" Joyful. "]}, "prefer_before_year": 1900})
    assert merged["hymns"]["closing"] == ["Joyful."]
    assert merged["prefer_before_year"] == 1900
    assert get_church_rubric_overrides(cid) == {"hymns": {"closing": ["Joyful."]}, "prefer_before_year": 1900}

    update_church_rubric(cid, {"hymns": {"closing": None}})
    assert get_church_rubric_overrides(cid) == {"prefer_before_year": 1900}
    assert get_church_rubric(cid)["hymns"]["closing"] == default_rubric()["hymns"]["closing"]


def test_rubric_invalid_update_raises_and_stores_nothing(tmp_db, make_user):
    cid = create_church(name="R3", timezone="UTC", owner_user_id=make_user(email="r3@x.org"))
    with pytest.raises(ValueError):
        update_church_rubric(cid, {"prefer_before_year": 1400})
    assert get_church_rubric_overrides(cid) == {}


def test_rubric_does_not_clobber_other_settings(tmp_db, make_user):
    cid = create_church(name="R4", timezone="UTC", owner_user_id=make_user(email="r4@x.org"))
    set_church_translation(cid, "nrsvue")
    set_church_prompts(cid, {"benediction": "Go in peace."})
    update_church_rubric(cid, {"prefer_familiar": False})
    assert get_church_translation(cid) == "nrsvue"
    assert get_church_prompts(cid) == {"benediction": "Go in peace."}
    assert get_church_rubric(cid)["prefer_familiar"] is False


def test_rubric_edits_stay_in_their_church(tmp_db, make_user):
    a = create_church(name="A", timezone="UTC", owner_user_id=make_user(email="a@x.org"))
    b = create_church(name="B", timezone="UTC", owner_user_id=make_user(email="b@x.org"))
    update_church_rubric(a, {"prayers": {"benediction": ["Only in A."]}})
    assert get_church_rubric_overrides(a) == {"prayers": {"benediction": ["Only in A."]}}
    assert get_church_rubric(b) == default_rubric()
    assert get_church_rubric_overrides(b) == {}


def test_rubric_update_reads_and_writes_under_one_row_lock(tmp_db, make_user):
    """Two admins patching at once must not drop either change: the overrides
    are read from the row the same transaction locks and then rewrites."""
    cid = create_church(name="L", timezone="UTC", owner_user_id=make_user(email="l@x.org"))
    with _record_church_row_access() as (reads, writes):
        update_church_rubric(cid, {"prefer_familiar": False})
    assert len(writes) == 1
    assert reads == [(writes[0], True)]


def test_settings_writes_lock_the_church_row(tmp_db, make_user):
    """Writes to different settings keys (e.g. a Streamlit translation change
    and a rubric PATCH) are serialized, so neither overwrites the other."""
    cid = create_church(name="L2", timezone="UTC", owner_user_id=make_user(email="l2@x.org"))
    for write in (lambda: set_church_translation(cid, "esv"),
                  lambda: set_church_prompts(cid, {"benediction": "Go in peace."})):
        with _record_church_row_access() as (reads, writes):
            write()
        assert len(writes) == 1
        assert reads == [(writes[0], True)]

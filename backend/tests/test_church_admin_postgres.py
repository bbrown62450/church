"""PATCH /church's write on real Postgres (6a spec, "Semantics" → Locking;
slice 6a-1; slice 6a-3a adds the prompts and the rubric below): while a
profile save holds the church-row lock, the other
locked settings writers (the bulletin settings, the rubric) wait for it, and
when it commits every key survives.

Skipped without TEST_DATABASE_URL; CI's backend-postgres job runs it. SQLite
ignores FOR UPDATE, so test_church_admin.py can only check that the lock is
asked for; this is the proof that the profile's merge reads the row after the
lock. Forcing the race: clean_profile_patch, which update_profile calls
through the module attribute after taking the lock, waits until the test lets
it go. A save that never gets there makes the test fail after 10 s instead
of passing vacuously.
"""
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from repos import churches
from repos.churches import create_church
from repos.users import ensure_user
from usecases import church_admin

pytestmark = pytest.mark.postgres


@pytest.fixture
def world(pg_db):
    owner = ensure_user("owner@example.com", "Owner").id
    return owner, create_church(name="Grace", timezone="America/New_York", owner_user_id=owner)


def test_other_settings_writers_wait_for_a_profile_save_and_every_key_survives(world, monkeypatch):
    owner, church_id = world
    inside, release = threading.Event(), threading.Event()
    clean = church_admin.clean_profile_patch

    def held(*args, **kwargs):
        inside.set()                   # update_profile holds the church-row lock here
        assert release.wait(10), "the test never released the profile save"
        return clean(*args, **kwargs)

    monkeypatch.setattr(church_admin, "clean_profile_patch", held)
    with ThreadPoolExecutor(3) as pool:
        profile = pool.submit(church_admin.update_profile, church_id, owner, {"default_benediction": "Go in peace."})
        assert inside.wait(10), "the profile save never took the lock"
        bulletin = pool.submit(churches.set_bulletin_settings, church_id, {"phone": "555-0100"})
        rubric = pool.submit(churches.update_church_rubric, church_id, {"prefer_familiar": False})
        done = threading.Event()
        done.wait(1)                   # time for either writer to finish if nothing held it
        assert not bulletin.done() and not rubric.done(), "the other settings writers did not wait for the lock"
        release.set()
        profile.result(10)
        bulletin.result(10)
        rubric.result(10)
    settings = churches.get_church(church_id)["settings"]
    assert settings["default_benediction"] == "Go in peace."
    assert settings["bulletin"] == {"phone": "555-0100"}
    assert settings["rubric"] == {"prefer_familiar": False}


# --- slice 6a-3a: the prompts and the rubric take the same lock --------------------------------------------------


def test_the_other_settings_writers_wait_for_a_prompts_save_and_every_key_survives(world, monkeypatch):
    """PUT /church/liturgy-prompts' write (church_admin.save_prompts) holds the
    church-row lock from its role re-read to its commit: a profile save, a
    rubric save and a bulletin settings save started meanwhile wait, and every
    key is there afterwards (6a spec, Testing → Postgres, without 6a-3b's
    prayer library)."""
    owner, church_id = world
    inside, release = threading.Event(), threading.Event()
    clean = church_admin.liturgy_prompts.clean_prompt_overrides

    def held(*args, **kwargs):
        inside.set()                   # save_prompts holds the church-row lock here
        assert release.wait(10), "the test never released the prompts save"
        return clean(*args, **kwargs)

    monkeypatch.setattr(church_admin.liturgy_prompts, "clean_prompt_overrides", held)
    with ThreadPoolExecutor(4) as pool:
        prompts = pool.submit(church_admin.save_prompts, church_id, owner, {"benediction": "Go."})
        assert inside.wait(10), "the prompts save never took the lock"
        profile = pool.submit(church_admin.update_profile, church_id, owner, {"bible_translation": "kjv"})
        rubric = pool.submit(church_admin.update_rubric, church_id, owner, {"prefer_before_year": 1900})
        bulletin = pool.submit(churches.set_bulletin_settings, church_id, {"phone": "555-0100"})
        threading.Event().wait(1)      # time for any writer to finish if nothing held it
        waiting = [f for f in (profile, rubric, bulletin) if not f.done()]
        assert len(waiting) == 3, "the other settings writers did not wait for the lock"
        release.set()
        for future in (prompts, profile, rubric, bulletin):
            future.result(10)
    settings = churches.get_church(church_id)["settings"]
    assert settings["liturgy_prompts"] == {"benediction": "Go."}
    assert settings["bible_translation"] == "kjv"
    assert settings["rubric"] == {"prefer_before_year": 1900}
    assert settings["bulletin"] == {"phone": "555-0100"}


def test_two_rubric_saves_at_once_keep_both_checklists(world, monkeypatch):
    """Two PATCH /rubric writes on different checklists (church_admin.update_rubric):
    the second reads the stored overrides only after the first commits, so
    neither checklist is lost."""
    owner, church_id = world
    inside, release = threading.Event(), threading.Event()
    write = churches.update_church_rubric
    calls = []

    def held(church, patch, **kwargs):
        calls.append(patch)
        if len(calls) == 1:
            inside.set()               # the first update_rubric holds the church-row lock here
            assert release.wait(10), "the test never released the first rubric save"
        return write(church, patch, **kwargs)

    monkeypatch.setattr(church_admin.churches, "update_church_rubric", held)
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(church_admin.update_rubric, church_id, owner, {"hymns": {"closing": ["Joyful."]}})
        assert inside.wait(10), "the first rubric save never took the lock"
        second = pool.submit(church_admin.update_rubric, church_id, owner,
                             {"prayers": {"benediction": ["Sends the people out."]}})
        threading.Event().wait(1)
        assert not second.done(), "the second rubric save did not wait for the lock"
        release.set()
        first.result(10)
        out = second.result(10)
    assert out["customized"] == ["hymns.closing", "prayers.benediction"]
    assert churches.get_church_rubric_overrides(church_id) == {
        "hymns": {"closing": ["Joyful."]}, "prayers": {"benediction": ["Sends the people out."]}}

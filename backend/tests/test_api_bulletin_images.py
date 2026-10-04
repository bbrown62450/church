"""/bulletin-images (printed bulletin spec, API; PR 3 planning answers 5, 8,
9; PR 3a): upload a cover picture, see it, church-scoped, the removal of
unused pictures after 60 days, a church's 160 pictures, the storage budget,
and a save and a removal waiting for each other (plan review C3, I4, I5).
Invented pictures only."""
import datetime
import logging
import uuid

import pytest
from sqlalchemy import select, text, update
from sqlalchemy.exc import OperationalError

import bulletin_image
from api import ratelimit
from db import SessionLocal, session_scope
from db.models import BulletinImage, Service
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    church_headers,
    isolation_world,
    make_api_client,
)
from tests.picture_helpers import BLUE, GREEN, RED, opened, picture, stripes

EMAIL = "pastor@example.com"
GONE = "That picture is no longer available."


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def pastor(make_user):
    return make_user(email=EMAIL)


@pytest.fixture
def church(pastor, make_church):
    return make_church(name="Grace", owner_user_id=pastor)


def upload(client, church_id, data, *, email=EMAIL, content_type="image/jpeg"):
    return client.post("/bulletin-images", content=data,
                       headers={**church_headers(email, church_id), "Content-Type": content_type})


def stored_ids() -> set[str]:
    with session_scope() as s:
        return {str(i) for i in s.execute(select(BulletinImage.id)).scalars()}


def test_any_member_uploads_a_picture_and_sees_it(client, church, make_user, caplog):
    member = make_user(email="member@example.com")
    add_membership(member, church, "member")
    caplog.set_level(logging.INFO, logger="usecases.bulletin_images")
    r = upload(client, church, stripes((4000, 3000), [RED, GREEN, BLUE]), email="member@example.com")
    assert r.status_code == 201, r.text
    made = r.json()
    assert set(made) == {"id", "width", "height"} and (made["width"], made["height"]) == (1600, 1200)
    got = client.get(f"/bulletin-images/{made['id']}", headers=church_headers(EMAIL, church))
    assert got.status_code == 200, got.text
    assert got.headers["content-type"] == "image/jpeg"
    assert (got.headers["cache-control"], got.headers["x-content-type-options"], got.headers["etag"]) == (
        "private, no-cache", "nosniff", f'"{made["id"]}"')
    assert got.headers["vary"].startswith("Authorization, X-Church-Id")              # CORS adds Origin
    assert opened(got.content).size == (1600, 1200)
    again = client.get(f"/bulletin-images/{made['id']}",
                       headers={**church_headers(EMAIL, church), "If-None-Match": got.headers["etag"]})
    assert (again.status_code, again.content, again.headers["etag"]) == (304, b"", got.headers["etag"])
    with session_scope() as s:
        row = s.get(BulletinImage, uuid.UUID(made["id"]))
        assert (row.content_type, row.width, row.height, row.created_by) == ("image/jpeg", 1600, 1200, member)
        assert bytes(row.bytes) == got.content
    (record,) = [r for r in caplog.records if r.getMessage().startswith("bulletin_images.upload")]
    assert f"image={made['id']}" in record.getMessage() and "size=1600x1200 removed=0" in record.getMessage()
    png = upload(client, church, picture((300, 200), fmt="PNG"), content_type="image/png")
    assert (png.status_code, png.json()["width"]) == (201, 300)


@pytest.mark.parametrize("data, content_type, message", [
    (picture(fmt="GIF", mode="P", color=1), "image/gif", bulletin_image.NOT_A_PICTURE_MESSAGE),
    (b"not a picture", "image/jpeg", bulletin_image.NOT_A_PICTURE_MESSAGE),
    (b"\xff" * (10 * 1024 * 1024 + 1), "image/jpeg", bulletin_image.TOO_LARGE_MESSAGE),
])
def test_only_a_jpeg_or_png_of_at_most_10_mb_is_taken(client, church, data, content_type, message):
    r = upload(client, church, data, content_type=content_type)
    assert r.status_code == 422, r.text
    assert (r.json()["error"]["code"], r.json()["error"]["fields"]) == ("invalid_request", {"image": message})
    assert stored_ids() == set()


def test_a_body_without_its_size_is_refused_before_it_is_read(client, church):
    """UploadSizeMiddleware: a chunked body (no Content-Length) could be any size."""
    def chunks():
        yield picture()

    r = client.post("/bulletin-images", content=chunks(), headers={**church_headers(EMAIL, church),
                                                                   "Content-Type": "image/jpeg"})
    assert r.status_code == 422, r.text
    assert r.json()["error"]["fields"] == {"image": "Send the picture with its size (Content-Length)."}
    empty = upload(client, church, b"")                     # an iCloud photo not downloaded yet
    assert (empty.status_code, empty.json()["error"]["fields"]) == (422, {"image": bulletin_image.NOT_A_PICTURE_MESSAGE})
    assert stored_ids() == set()


def test_every_route_is_church_isolated(client, isolation_world):
    w = isolation_world
    mine = upload(client, w.church_a, picture(), email=w.a).json()["id"]
    theirs = upload(client, w.church_b, picture(), email=w.b).json()["id"]
    assert_church_isolated(client, "POST", "/bulletin-images", world=w)
    assert_church_isolated(client, "GET", f"/bulletin-images/{mine}", world=w,
                           resource_path_b=f"/bulletin-images/{theirs}")
    r = client.get(f"/bulletin-images/{uuid.uuid4()}", headers=church_headers(w.a, w.church_a))
    assert (r.status_code, r.json()["error"]["message"]) == (404, GONE)
    r = client.get(f"/bulletin-images/{theirs}", headers={**church_headers(w.a, w.church_a),
                                                           "If-None-Match": f'"{theirs}"'})
    assert (r.status_code, r.json()["error"]["message"]) == (404, GONE)
    r = client.get("/bulletin-images/not-an-id", headers=church_headers(w.a, w.church_a))
    assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_request")


def test_the_picture_bucket_takes_20_an_hour_a_member(client, church, pastor):
    ratelimit.consume("picture", user_id=pastor, church_id=church, cost=20)
    r = upload(client, church, picture())
    assert (r.status_code, r.json()["error"]["code"]) == (429, "rate_limited")
    assert int(r.headers["retry-after"]) > 0
    assert stored_ids() == set()


def add_picture(church_id, user_id, *, age_days=0, data=None) -> str:
    with session_scope() as s:
        row = BulletinImage(church_id=church_id, content_type="image/jpeg", bytes=data or picture(), width=400,
                            height=300, created_by=user_id, created_at=datetime.datetime.now(datetime.timezone.utc)
                            - datetime.timedelta(days=age_days))
        s.add(row)
        s.flush()
        return str(row.id)


def add_service(church_id, image_id, day="2026-01-04"):
    with session_scope() as s:
        s.add(Service(church_id=church_id, service_date_iso=day, occasion="", hymns=[], liturgy={}, scriptures=[],
                      bulletin={"cover_image_id": image_id}))


def test_an_upload_removes_any_church_s_pictures_unused_for_60_days(client, church, pastor, make_church, caplog,
                                                                    monkeypatch):
    """Planning answer 9: a picture no saved service of its church points at goes 60 days after its upload,
    on any church's next upload (a church that stops uploading loses its own too), at most REMOVE_BATCH at a
    time. Kept: one a saved service points at (any age), one uploaded within 60 days (a draft may point at
    it), one another church's service points at in that church."""
    from usecases import bulletin_images

    other = make_church(name="Other", owner_user_id=pastor)
    ids = {"old": add_picture(church, pastor, age_days=61), "used": add_picture(church, pastor, age_days=400),
           "recent": add_picture(church, pastor, age_days=59), "elsewhere": add_picture(other, pastor, age_days=70),
           "elsewhere_too": add_picture(other, pastor, age_days=65),
           "used_elsewhere": add_picture(other, pastor, age_days=90)}
    add_service(church, ids["used"])
    add_service(other, ids["used_elsewhere"])
    add_service(other, ids["old"], day="2026-01-11")          # another church's service: not a use of this one
    monkeypatch.setattr(bulletin_images, "REMOVE_BATCH", 2)
    caplog.set_level(logging.INFO, logger="usecases.bulletin_images")
    first = upload(client, church, picture())
    assert first.status_code == 201, first.text
    # The church with the oldest picture first ("used", 400 days): its "old"; then the other's oldest unused,
    # "elsewhere", and the batch of 2 is full.
    assert stored_ids() == {ids["used"], ids["recent"], ids["elsewhere_too"], ids["used_elsewhere"],
                            first.json()["id"]}
    assert "removed=2" in caplog.records[-1].getMessage()
    second = upload(client, church, picture())
    assert stored_ids() == {ids["used"], ids["recent"], ids["used_elsewhere"], first.json()["id"],
                            second.json()["id"]}
    assert "removed=1" in caplog.records[-1].getMessage()


def test_a_church_keeps_at_most_its_quota_of_pictures(client, church, pastor, monkeypatch):
    """Plan review C3: past MAX_PICTURES, the church's oldest pictures no saved service points at make room,
    whatever their age; when every one is in a saved service, the upload is refused and nothing changes."""
    from usecases import bulletin_images

    monkeypatch.setattr(bulletin_images, "MAX_PICTURES", 3)
    first, second, third = (add_picture(church, pastor, age_days=days) for days in (3, 2, 1))
    add_service(church, first)
    made = upload(client, church, picture())
    assert made.status_code == 201, made.text
    assert stored_ids() == {first, third, made.json()["id"]}                  # the oldest unused one went
    add_service(church, third, day="2026-01-11")
    add_service(church, made.json()["id"], day="2026-01-18")
    full = upload(client, church, picture())
    assert (full.status_code, full.json()["error"]["fields"]) == (422, {"image": bulletin_images.CHURCH_FULL_MESSAGE})
    assert stored_ids() == {first, third, made.json()["id"]}
    assert bulletin_images.CHURCH_FULL_MESSAGE.startswith("Your church keeps 160 pictures, all in saved services.")


def test_uploads_stop_when_every_church_s_pictures_reach_the_storage_budget(client, church, pastor, make_church,
                                                                            monkeypatch, caplog):
    """Plan review C3: any Google account can make a church, so a budget for all churches together keeps the
    database's free plan from filling; past it the upload is refused and the log says so."""
    from usecases import bulletin_images

    other = make_church(name="Other", owner_user_id=pastor)
    add_picture(other, pastor, data=b"\xff" * 5000)
    monkeypatch.setattr(bulletin_images, "STORAGE_BUDGET", 5000 + len(bulletin_image.prepare(picture()).content))
    assert upload(client, church, picture()).status_code == 201
    caplog.set_level(logging.WARNING, logger="usecases.bulletin_images")
    r = upload(client, church, picture())
    assert (r.status_code, r.json()["error"]["fields"]) == (422, {"image": bulletin_images.STORAGE_FULL_MESSAGE})
    assert len(stored_ids()) == 2
    assert caplog.records[-1].getMessage().startswith(f"bulletin_images.storage_full church={church} total=")


def test_the_removal_reads_the_saved_services_after_it_locks_its_candidates(client, church, pastor, monkeypatch):
    """Plan review I5: a save that points at an old picture while the removal runs keeps it. The removal
    locks its candidates first (FOR UPDATE on Postgres) and only then reads which pictures the saved services
    point at, so a save that got there first is seen (the Postgres test below checks the locks themselves)."""
    from repos import bulletin_images as images_repo

    old = add_picture(church, pastor, age_days=61)
    add_service(church, None)
    original = images_repo.ids_created_before

    def a_save_in_between(church_id, cutoff=None, *, session, lock=False):
        found = original(church_id, cutoff, session=session, lock=lock)
        session.execute(update(Service).where(Service.church_id == church_id).values(bulletin={"cover_image_id": old}))
        return found

    monkeypatch.setattr(images_repo, "ids_created_before", a_save_in_between)
    assert upload(client, church, picture()).status_code == 201
    assert old in stored_ids()


@pytest.mark.postgres
def test_a_save_and_the_removal_wait_for_each_other(pg_db):
    """Plan review I5, on Postgres: the removal's FOR UPDATE on a picture and a save's FOR SHARE on it
    exclude each other, whichever comes first (the other waits; here it gives up after 200 ms)."""
    from repos import bulletin_images as images_repo
    from repos.churches import create_church
    from repos.users import ensure_user

    user = ensure_user("pastor@example.com", "Pastor").id
    church_id = create_church(name="Grace", timezone="America/New_York", owner_user_id=user)
    image = add_picture(church_id, user, age_days=61)
    for first, second in (("remove", "save"), ("save", "remove")):
        holder, waiter = SessionLocal(), SessionLocal()
        try:
            take = {"remove": lambda s: images_repo.ids_created_before(church_id, None, session=s, lock=True),
                    "save": lambda s: images_repo.has_image(church_id, image, session=s, lock=True)}
            assert take[first](holder)
            waiter.execute(text("SET LOCAL lock_timeout = '200ms'"))
            with pytest.raises(OperationalError, match="lock timeout"):
                take[second](waiter)
        finally:
            waiter.rollback()
            holder.rollback()
            waiter.close()
            holder.close()

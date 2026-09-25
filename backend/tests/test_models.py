import uuid

import pytest
from sqlalchemy.exc import IntegrityError


def test_church_user_membership_service_roundtrip(tmp_db):
    from db import session_scope
    from db.models import User, Church, Membership, Service

    uid = uuid.uuid4()
    cid = uuid.uuid4()
    sid = uuid.uuid4()

    with session_scope() as s:
        s.add(User(id=uid, email="pastor@example.com", name="Pastor"))
        s.add(Church(id=cid, name="Grace Church", timezone="America/New_York"))
        s.flush()  # persist parent rows before FK-referencing children
        s.add(Membership(church_id=cid, user_id=uid, role="owner"))
        s.add(Service(
            id=sid,
            church_id=cid,
            created_by=uid,
            service_date_iso="2026-07-26",
            service_date_display="Sunday, July 26, 2026",
            occasion="Ordinary Time",
            scriptures=["Ps 23", "John 10:1-10"],
            hymns=[{"title": "Amazing Grace", "number": 649}],
            liturgy={"opening": "Let us worship God."},
            sermon_title="The Good Shepherd",
            selected_ot_ref="Ps 23",
            selected_nt_ref="John 10:1-10",
            include_communion=True,
        ))

    with session_scope() as s:
        svc = s.get(Service, sid)
        assert svc.church_id == cid
        assert svc.created_by == uid
        assert svc.service_date_iso == "2026-07-26"
        assert svc.service_date_display == "Sunday, July 26, 2026"
        assert svc.scriptures == ["Ps 23", "John 10:1-10"]
        assert svc.hymns[0]["number"] == 649
        assert svc.liturgy["opening"] == "Let us worship God."
        assert svc.include_communion is True

        mem = s.get(Membership, {"church_id": cid, "user_id": uid})
        assert mem.role == "owner"
        assert s.get(Church, cid).name == "Grace Church"
        assert s.get(User, uid).email == "pastor@example.com"


def test_membership_role_check_constraint_rejects_bad_role(tmp_db):
    from db import session_scope
    from db.models import User, Church, Membership

    uid = uuid.uuid4()
    cid = uuid.uuid4()
    with session_scope() as s:
        s.add(User(id=uid, email="a@example.com", name="A"))
        s.add(Church(id=cid, name="C", timezone="America/New_York"))

    with pytest.raises(IntegrityError):
        with session_scope() as s:
            s.add(Membership(church_id=cid, user_id=uid, role="superadmin"))


def test_seed_catalog_fixture_populates_enrichment(tmp_db, seed_catalog):
    from db import session_scope
    from db.models import HymnCatalog

    assert seed_catalog(4) == 4
    with session_scope() as s:
        rows = s.query(HymnCatalog).all()
    assert len(rows) == 4
    assert all(r.scripture_refs for r in rows)
    assert all(r.theme for r in rows)

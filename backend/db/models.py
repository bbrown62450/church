"""ORM models — one relational schema serving SQLite (dev) and Postgres (prod).

Portability rules (both backends): generic types only (Uuid, JSON), Python-side
defaults (uuid4, utcnow) rather than server defaults. One exception: a NOT NULL
column added while the frozen Streamlit app still shares the database (until
slice 7) also declares a server default, because Streamlit's ORM does not map
the column and its inserts must still succeed (F §3.4; Invite.reusable,
revision 0004_invites_reusable). A new nullable column needs none. Church
content cascades to the CHURCH; authorship FKs (created_by) SET NULL so history
survives a departing author.
"""
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)

from db.engine import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True)  # normalized lower-case
    google_sub = Column(String, unique=True)
    name = Column(String)
    picture = Column(String)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    # Last seen, to the hour (see repos.users.LAST_SEEN_RESOLUTION).
    last_login_at = Column(DateTime(timezone=True))


class Church(Base):
    __tablename__ = "churches"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    timezone = Column(String, nullable=False)
    settings = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    deleted_at = Column(DateTime(timezone=True))  # soft delete


class Membership(Base):
    __tablename__ = "memberships"

    church_id = Column(
        Uuid, ForeignKey("churches.id", ondelete="CASCADE"), primary_key=True
    )
    user_id = Column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        CheckConstraint(
            "role IN ('owner','admin','member')", name="ck_memberships_role"
        ),
        Index("ix_memberships_user_id", "user_id"),
        # Revision 0009_memberships_one_owner (slice 6b-2a): at most one owner
        # per church. Ownership moves only by a transfer, which demotes the
        # owner before it promotes the new one (repos.memberships.transfer_ownership).
        Index(
            "uq_memberships_one_owner", "church_id", unique=True,
            postgresql_where=sa.text("role = 'owner'"), sqlite_where=sa.text("role = 'owner'"),
        ),
    )


# An invite still waiting to be used: email-bound, not revoked, not accepted
# (uq_invites_pending_email's predicate; revision 0008_invites_integrity).
PENDING_INVITE = "email IS NOT NULL AND NOT revoked AND accepted_at IS NULL"


class Invite(Base):
    __tablename__ = "invites"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    church_id = Column(
        Uuid, ForeignKey("churches.id", ondelete="CASCADE"), nullable=False
    )
    code = Column(String, nullable=False, unique=True)
    email = Column(String)  # nullable (anyone with the link); stored lower-cased
    role = Column(String, nullable=False, default="member")
    created_by = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, nullable=False, default=False)
    accepted_at = Column(DateTime(timezone=True))
    # Revision 0004_invites_reusable. reusable: several people may join with
    # the code until it expires or is revoked (6b sets it); frozen Streamlit's
    # inserts get the server default false. accepted_by: who consumed a
    # single-use invite (1b's accept stamps it with accepted_at).
    reusable = Column(Boolean, nullable=False, default=False, server_default=sa.false())
    accepted_by = Column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL", name="fk_invites_accepted_by_users")
    )

    __table_args__ = (
        # Revision 0008_invites_integrity (slice 6b-1): an invite grants member
        # or admin, never owner; and one pending invite per church and email,
        # in any capitalization (a revoked, accepted or code-only one never
        # counts, so re-inviting after a revoke or an acceptance works).
        CheckConstraint("role IN ('member','admin')", name="ck_invites_role"),
        Index(
            "uq_invites_pending_email", "church_id", sa.func.lower(email), unique=True,
            postgresql_where=sa.text(PENDING_INVITE), sqlite_where=sa.text(PENDING_INVITE),
        ),
        Index("ix_invites_church_id", "church_id"),
    )


class HymnCatalog(Base):
    """Shared starter hymnal (template). Never church-scoped; never mutated by a church."""
    __tablename__ = "hymn_catalog"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    hymnal = Column(String, nullable=False, default="GG2013")  # which hymnal
    title = Column(String)
    number = Column(Integer)
    scripture_refs = Column(Text)
    theme = Column(Text)
    hymnary_link = Column(Text)
    audio_url = Column(Text)
    text_year = Column(Integer)      # year the words were written (Hymnary.org); None = unknown
    hymnal_count = Column(Integer)   # hymnals that include the text: familiarity; None = unknown


class Hymn(Base):
    """Per-church, editable hymnal. Seeded from HymnCatalog at church creation."""
    __tablename__ = "hymns"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    church_id = Column(
        Uuid, ForeignKey("churches.id", ondelete="CASCADE"), nullable=False
    )
    hymnal = Column(String, nullable=False, default="GG2013")  # which hymnal
    title = Column(String)
    number = Column(Integer)
    scripture_refs = Column(Text)
    theme = Column(Text)
    hymnary_link = Column(Text)
    audio_url = Column(Text)
    text_year = Column(Integer)      # year the words were written (Hymnary.org); None = unknown
    hymnal_count = Column(Integer)   # hymnals that include the text: familiarity; None = unknown

    __table_args__ = (
        Index("ix_hymns_church_id", "church_id"),
        Index("ix_hymns_church_hymnal", "church_id", "hymnal"),
        Index("ix_hymns_church_number", "church_id", "number"),
    )


class Service(Base):
    """Archived worship service. Date is stored as iso + display strings (no DATE)."""
    __tablename__ = "services"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    church_id = Column(
        Uuid, ForeignKey("churches.id", ondelete="CASCADE"), nullable=False
    )
    created_by = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    service_date_iso = Column(String)
    service_date_display = Column(String)
    occasion = Column(String)
    scriptures = Column(JSON)
    hymns = Column(JSON)  # denormalized title/number snapshot, no FK to hymns
    liturgy = Column(JSON)
    sermon_title = Column(String)
    selected_ot_ref = Column(String)
    selected_nt_ref = Column(String)
    include_communion = Column(Boolean, nullable=False, default=False)
    saved_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    # Revision 0005_services_extras (slice 5a-2). NULL means "not recorded": a
    # service saved before 5a-2 (by Streamlit) has neither, and the API reads
    # them as no custom elements ([]) and no hymnal (null).
    custom_elements = Column(JSON, nullable=True)   # [{label, text, insert_after}]
    hymnal = Column(String, nullable=True)          # the hymnal the hymns came from
    # Revision 0006_services_bulletin (printed bulletin PR 2b): the printed
    # bulletin's weekly fields (service_bulletin.py). NULL: never filled in
    # (every service saved before PR 2b), read as an empty bulletin. A Python
    # None is stored as SQL NULL, never as the JSON value null.
    bulletin = Column(JSON(none_as_null=True), nullable=True)

    __table_args__ = (
        Index("ix_services_church_saved_at", "church_id", "saved_at"),
        # One church's services, for the archive list and the hymn-use rebuild (5a-2):
        # its church_id prefix; the list sorts on an expression of the date.
        Index("ix_services_church_date", "church_id", "service_date_iso"),
    )


class BulletinImage(Base):
    """A cover picture for the printed bulletin (revision 0007_bulletin_images;
    printed bulletin PR 3a): the upload turned upright, scaled to at most
    1600 px on its long side and stored as JPEG (bulletin_image.py). A
    service's bulletin points at it by id (services.bulletin's
    "cover_image_id", no foreign key); one no saved service points at is
    removed 60 days after its upload (usecases.bulletin_images)."""
    __tablename__ = "bulletin_images"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    church_id = Column(
        Uuid, ForeignKey("churches.id", ondelete="CASCADE"), nullable=False
    )
    content_type = Column(String, nullable=False)    # always "image/jpeg" (what is stored)
    bytes = Column(LargeBinary, nullable=False)      # the picture itself
    width = Column(Integer, nullable=False)          # in pixels, as stored
    height = Column(Integer, nullable=False)
    created_by = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        # One church's pictures by age: the 60-day removal (usecases.bulletin_images).
        Index("ix_bulletin_images_church_created", "church_id", "created_at"),
    )


class HymnUsage(Base):
    """Drives 'exclude hymns used in the last 12 weeks'. Idempotent per dedupe key."""
    __tablename__ = "hymn_usage"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    church_id = Column(
        Uuid, ForeignKey("churches.id", ondelete="CASCADE"), nullable=False
    )
    date_iso = Column(String, nullable=True)
    hymn_number = Column(Integer)
    hymn_title = Column(String)  # denormalized, no FK to hymns
    recorded_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        UniqueConstraint(
            "church_id", "date_iso", "hymn_number", "hymn_title",
            name="uq_hymn_usage_dedupe",
        ),
        Index("ix_hymn_usage_church_date", "church_id", "date_iso"),
    )


class Contact(Base):
    """Configurable per-church email destinations."""
    __tablename__ = "contacts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    church_id = Column(
        Uuid, ForeignKey("churches.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String)
    email = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        Index("ix_contacts_church_id", "church_id"),
    )


class GmailToken(Base):
    """User-scoped (not church-scoped): connect Gmail once, send in any church."""
    __tablename__ = "gmail_tokens"

    user_id = Column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    refresh_token = Column(Text, nullable=False)
    google_email = Column(String)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)


class OAuthState(Base):
    """CSRF state for the gmail.send flow; survives the redirect, single-use."""
    __tablename__ = "oauth_states"

    state = Column(String, primary_key=True)
    user_id = Column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)

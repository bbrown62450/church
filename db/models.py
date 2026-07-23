"""ORM models — one relational schema serving SQLite (dev) and Postgres (prod).

Portability rules (both backends): generic types only (Uuid, JSON), Python-side
defaults only (uuid4, utcnow) — never server defaults. Church content cascades
to the CHURCH; authorship FKs (created_by) SET NULL so history survives a
departing author.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
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
    )


class Invite(Base):
    __tablename__ = "invites"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    church_id = Column(
        Uuid, ForeignKey("churches.id", ondelete="CASCADE"), nullable=False
    )
    code = Column(String, nullable=False, unique=True)
    email = Column(String)  # nullable; when set, one pending per (church, email)
    role = Column(String, nullable=False, default="member")
    created_by = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, nullable=False, default=False)
    accepted_at = Column(DateTime(timezone=True))

    __table_args__ = (
        # NULL emails are distinct on both SQLite and Postgres, so many
        # code-only invites coexist while an email-bound one is single-pending.
        UniqueConstraint("church_id", "email", name="uq_invites_church_email"),
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

    __table_args__ = (
        Index("ix_services_church_saved_at", "church_id", "saved_at"),
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

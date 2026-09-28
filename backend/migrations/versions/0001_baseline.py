"""Baseline: the 11 tables of db/models.py as of slice 1a.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-26

Runs only on fresh databases (CI, new local dev). Production is stamped at
this revision, not migrated (backend/migrations/README.md, step 4).

Written out by hand, never imported from db.models, so later model changes
cannot change what this revision creates. It reproduces the models exactly:
- unique, primary-key and foreign-key constraints stay unnamed, as
  create_all made them in production (users_email_key, invites_code_key,
  *_pkey, *_fkey on Postgres); no naming convention;
- the named constraints and indexes keep their model names;
- ON DELETE CASCADE for church content and memberships, SET NULL for the
  created_by authorship columns;
- the nullable INTEGER text_year and hymnal_count columns on hymns and
  hymn_catalog, and ix_hymns_church_hymnal (0002_reconcile adds these to an
  older database that lacks them);
- no server defaults (the models use Python-side defaults). Production's
  DEFAULT 'GG2013' on hymnal (from the deleted migrate_add_hymnal.py) stays
  where it is; env.py compares no server defaults.
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("google_sub", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("picture", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("google_sub"),
    )
    op.create_table(
        "churches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("timezone", sa.String(), nullable=False),
        sa.Column("settings", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "memberships",
        sa.Column("church_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('owner','admin','member')", name="ck_memberships_role"),
        sa.ForeignKeyConstraint(["church_id"], ["churches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("church_id", "user_id"),
    )
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"])
    op.create_table(
        "invites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("church_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("church_id", "email", name="uq_invites_church_email"),
        sa.ForeignKeyConstraint(["church_id"], ["churches.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("code"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_invites_church_id", "invites", ["church_id"])
    op.create_table(
        "hymn_catalog",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("hymnal", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("number", sa.Integer(), nullable=True),
        sa.Column("scripture_refs", sa.Text(), nullable=True),
        sa.Column("theme", sa.Text(), nullable=True),
        sa.Column("hymnary_link", sa.Text(), nullable=True),
        sa.Column("audio_url", sa.Text(), nullable=True),
        sa.Column("text_year", sa.Integer(), nullable=True),
        sa.Column("hymnal_count", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "hymns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("church_id", sa.Uuid(), nullable=False),
        sa.Column("hymnal", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("number", sa.Integer(), nullable=True),
        sa.Column("scripture_refs", sa.Text(), nullable=True),
        sa.Column("theme", sa.Text(), nullable=True),
        sa.Column("hymnary_link", sa.Text(), nullable=True),
        sa.Column("audio_url", sa.Text(), nullable=True),
        sa.Column("text_year", sa.Integer(), nullable=True),
        sa.Column("hymnal_count", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["church_id"], ["churches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hymns_church_id", "hymns", ["church_id"])
    op.create_index("ix_hymns_church_hymnal", "hymns", ["church_id", "hymnal"])
    op.create_index("ix_hymns_church_number", "hymns", ["church_id", "number"])
    op.create_table(
        "services",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("church_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("service_date_iso", sa.String(), nullable=True),
        sa.Column("service_date_display", sa.String(), nullable=True),
        sa.Column("occasion", sa.String(), nullable=True),
        sa.Column("scriptures", sa.JSON(), nullable=True),
        sa.Column("hymns", sa.JSON(), nullable=True),
        sa.Column("liturgy", sa.JSON(), nullable=True),
        sa.Column("sermon_title", sa.String(), nullable=True),
        sa.Column("selected_ot_ref", sa.String(), nullable=True),
        sa.Column("selected_nt_ref", sa.String(), nullable=True),
        sa.Column("include_communion", sa.Boolean(), nullable=False),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["church_id"], ["churches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_services_church_saved_at", "services", ["church_id", "saved_at"])
    op.create_table(
        "hymn_usage",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("church_id", sa.Uuid(), nullable=False),
        sa.Column("date_iso", sa.String(), nullable=True),
        sa.Column("hymn_number", sa.Integer(), nullable=True),
        sa.Column("hymn_title", sa.String(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "church_id", "date_iso", "hymn_number", "hymn_title", name="uq_hymn_usage_dedupe"
        ),
        sa.ForeignKeyConstraint(["church_id"], ["churches.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_hymn_usage_church_date", "hymn_usage", ["church_id", "date_iso"])
    op.create_table(
        "contacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("church_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["church_id"], ["churches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contacts_church_id", "contacts", ["church_id"])
    op.create_table(
        "gmail_tokens",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=False),
        sa.Column("google_email", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "oauth_states",
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("state"),
    )


def downgrade() -> None:
    # Reverse creation order; dropping a table drops its indexes with it.
    for table in ("oauth_states", "gmail_tokens", "contacts", "hymn_usage", "services",
                  "hymns", "hymn_catalog", "invites", "memberships", "churches", "users"):
        op.drop_table(table)

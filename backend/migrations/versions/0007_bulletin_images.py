"""Bulletin images: the printed bulletin's cover pictures (printed bulletin spec, "Data model"; PR 3a)

Expand-only (F §3.4): one new table, no change to any other, no backfill.
- bulletin_images: one uploaded cover picture, turned upright, scaled to at
  most 1600 px on its long side and stored as JPEG (bulletin_image.py):
  id, church_id (the church's content cascades with it), content_type,
  bytes (the picture), width and height in pixels, created_by (SET NULL
  when the member's account goes), created_at. A service's bulletin points
  at a picture by id (services.bulletin's "cover_image_id": a JSON key, no
  foreign key); a picture no saved service points at is removed 60 days
  after its upload (usecases.bulletin_images).
- ix_bulletin_images_church_created (church_id, created_at): one church's
  pictures by age, for that removal.
- Row-level security on, as 0003_lockdown left every other public table:
  with no policy, Supabase's anon and authenticated roles see no row, so a
  picture is only ever served through the API, church-scoped. Postgres only
  (SQLite has no row-level security).
- REVOKE ALL on the table from anon and authenticated when both roles exist
  (Supabase; CI's Postgres has neither), as 0003_lockdown does: 0003's
  ALTER DEFAULT PRIVILEGES already leaves them no grant on a new table, but
  only for the role that ran 0003, so this does not depend on it (plan
  review M10).

On Postgres env.py runs SET LOCAL lock_timeout = '5s' (and statement_timeout
'60s') first. Creating a table takes no lock on any existing table except a
short one on churches and users for the two foreign keys.

Revision ID: 0007_bulletin_images
Revises: 0006_services_bulletin
Create Date: 2026-10-03
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_bulletin_images"
down_revision = "0006_services_bulletin"
branch_labels = None
depends_on = None

# 0003_lockdown's REVOKE, for this table only, under the same guard (both Supabase roles exist).
REVOKE_SQL = """\
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon')
     AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    REVOKE ALL ON bulletin_images FROM anon, authenticated;
  END IF;
END $$"""


def upgrade() -> None:
    op.create_table(
        "bulletin_images",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("church_id", sa.Uuid(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("bytes", sa.LargeBinary(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["church_id"], ["churches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bulletin_images_church_created", "bulletin_images", ["church_id", "created_at"])
    if op.get_context().dialect.name == "postgresql":
        op.execute("ALTER TABLE bulletin_images ENABLE ROW LEVEL SECURITY")
        op.execute(REVOKE_SQL)


def downgrade() -> None:
    op.drop_index("ix_bulletin_images_church_created", table_name="bulletin_images")
    op.drop_table("bulletin_images")

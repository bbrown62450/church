# Printed Bulletin PR 3: the Cover Picture

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status: work in progress (planning, 2026-10-03).** The tasks are being built and replayed; this file is committed early so nothing is lost.

Baselines measured at `fbc9598` (2026-10-03): backend `1432 passed, 17 skipped`; Postgres-marked `17 passed, 1432 deselected` (local Postgres 16); frontend `704 passed` in 87 files; typecheck and lint clean; Alembic head `0006_services_bulletin` (6 revision files); 4 runbook owner markers.

## Working notes (replaced by the finished plan)

- Build worktree: `<scratch>/p3/build` (detached at `fbc9598`), commits per task "T<n> tests" then "T<n> code"; edit scripts in `<scratch>/p3/tools`. Local Postgres 16 on port 5433, databases `p3build` and `p3replay`.
- T1 (3a): `0007_bulletin_images` (table, index `ix_bulletin_images_church_created`, RLS on for Postgres), `BulletinImage` model, README "Before 0007_bulletin_images (printed bulletin PR 3a)" with counts (incl. database size), the SQL preview (trailing spaces stripped) and an after-deploy check (version, row_security, open_grants, pictures).
- T2 (3a): `bulletin_image.py` (prepare: 10 MB, JPEG/PNG, 50 MP, EXIF upright, sRGB, alpha on white, 1600 px, JPEG q85 without EXIF; cover: centered crop 1550x1250 px at 300 dpi, black band 55 %, white Times Bold from reportlab's `_eb_____.pfb`); `service_bulletin` `cover_image_id` + `cover_given` (False: a page from before 3b said nothing); `printed_bulletin.cover_kind` placeholder/picture/none; PDF and Word place the same composite JPEG (`printed_pdf.cover_picture`); no picture: reading and date centered, no box; the PDF box is now centered (PR 1's was at the left margin).
- T3 (3a, next): the API (raw body upload, not multipart: python-multipart is only installed through Streamlit, not in backend/requirements.txt), `CARRY_KEYS` gains "cover", archive keeps/validates the id, printing loads the picture, cleanup on upload (church-scoped, 60 days, never one a saved service points at), rate limit bucket, OpenAPI.
- T3 built: `repos/bulletin_images.py`, `usecases/bulletin_images.py` (upload with the 60-day removal on each upload; picture), `api/routes/bulletin_images.py` (raw body, `picture` bucket 20/h a member and 60/day a church, GET `private, max-age=86400`), `UploadSizeMiddleware` (Content-Length over 10 MB or missing: 422 `image`), `ServiceBulletin.cover_image_id` (optional; left out keeps the saved picture), `CARRY_KEYS` gains "cover" first, archive saves an id the church does not have as none, printing reads the picture. OpenAPI: no Input/Output split. T4 docs: items 28-31, the spec's data model.
- 3a counts as built: backend 1432 → 1464 passed, 17 → 19 skipped; Postgres 19 passed; frontend 704 in 87 unchanged; typecheck and lint clean.

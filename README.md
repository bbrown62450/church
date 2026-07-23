# Worship Service Builder — Multi-Church

Plan worship services (lectionary lookup, scripture-matched hymn suggestions,
AI-written PC(USA)-friendly liturgy, Word export, service archive, and
"exclude hymns used in the last 12 weeks"). Multiple churches share one
deployment; each church's hymnal, archive, contacts, and members are fully
isolated. People sign in with Google, then create a church (becoming owner) or
join one by invite.

## Architecture at a glance

- **Auth:** Streamlit native OIDC (`st.login` / `st.user`) with Google. Login
  uses only `openid` + `email` scopes. Sending a bulletin uses a **separate,
  opt-in** `gmail.send` grant (`google_oauth.py`).
- **Storage:** one relational database via SQLAlchemy 2.x, selected by
  `DATABASE_URL`. SQLite for local dev, Supabase Postgres in production.
- **Tenancy:** every request re-derives the caller's membership + role
  server-side (`tenancy.require_active_church`); all church data is filtered by
  the validated `church_id`.

## Local setup

```bash
pip install -r requirements.txt
cp .env.example .env          # fill in values (never commit .env)
```

`.env` holds the environment variables (`DATABASE_URL`, `OPENAI_API_KEY`,
the `GOOGLE_*` gmail.send client, and the migration-only `NOTION_*`). The
**Streamlit login** config is separate — see the `[auth]` block below.

### Streamlit login: `.streamlit/secrets.toml`

```toml
[auth]
redirect_uri = "http://localhost:8501/oauth2callback"
cookie_secret = "<strong random string>"
client_id = "<google client id>"
client_secret = "<google client secret>"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

The `redirect_uri` **must** end in `/oauth2callback` and be registered on the
Google OAuth client. It differs between dev (`localhost:8501`) and prod (the
Streamlit Cloud URL), so each environment needs its own value.

### Run

```bash
streamlit run app.py
```

## Google OAuth client — two redirect URIs

A single Google "Web application" OAuth client backs both flows and needs
**two** registered redirect URIs (each must match exactly — scheme, host, path,
trailing slash):

1. `https://<app>/oauth2callback` — for `st.login` (handled internally by
   Streamlit; never reaches app code). This is the `[auth]` `redirect_uri`.
2. `https://<app>/` (the bare app root, trailing slash included) — for the
   manual `gmail.send` flow. Set `GOOGLE_OAUTH_REDIRECT_URI` to this exact
   app-root value. The return trip is identified by its single-use `?state=`;
   Streamlit's login callback lives on `/oauth2callback` and never delivers a
   code to the app root, so the flows cannot collide.

Enable the **Gmail API**, and while the app is unverified add each sender under
**Test users** (up to 100). A dedicated OAuth client for `gmail.send` is an
allowed, slightly safer alternative to reusing the login client.

## Database

- **Local dev:** `DATABASE_URL=sqlite:///data/app.db`.
- **Production (Supabase):** use the **session pooler** host, e.g.
  `postgresql+psycopg2://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres`.
  Do **not** use the direct `db.<ref>.supabase.co` host — it is IPv6-only on the
  free tier and unreachable from Streamlit Community Cloud's IPv4-only egress.

Store `DATABASE_URL` in Streamlit secrets (App → Settings → Secrets).

## One-time migration (Notion + legacy contacts → database)

Import the founder church's existing Notion data (hymns, archive, usage) and
saved contacts. Set `NOTION_API_KEY`, `NOTION_DATABASE_ID`,
`NOTION_ARCHIVE_DATABASE_ID`, `NOTION_USAGE_DATABASE_ID`, and `DATABASE_URL`,
then:

```bash
python migrate_to_db.py \
  --founder-email beau@example.com \
  --church-name "Conner Presbyterian" \
  --timezone America/New_York
```

It creates the founder user + church (owner), imports the enriched Notion hymns
into `hymn_catalog`, seeds the founder church's hymns, imports the archive and
hymn usage, and copies contacts into the **founder church only**. It is
**re-runnable to convergence** (idempotent) and prints a report of counts plus
any liturgy rows flagged as truncated. Enrichment is validated at the end; an
empty scripture lookup aborts the run non-zero.

## Operations

### Keep-alive (required)

The free Supabase project pauses after ~7 days idle. `.github/workflows/keepalive.yml`
runs `keepalive.py` (a `SELECT 1` against `DATABASE_URL`) daily so the first
visitor each week never hits a paused/cold database. Add `DATABASE_URL` as an
Actions secret.

### Backups (required)

Supabase Free retains no backups. `.github/workflows/backup.yml` runs a daily
`pg_dump` and uploads the compressed dump as a build artifact. Artifacts are
short-lived — for durable retention, extend the job to push the dump to object
storage.

### Limits & upgrade path

Free tier: 500 MB DB, ample connections for a handful of churches. Each church
owns an independent copy of the ~700-hymn hymnal, so catalog-wide corrections
do not propagate automatically. Scaling to many churches may require the paid
tier (which also enables direct IPv4 connections).

## Removed since single-tenant

`APP_PASSWORD`, the shared SMTP fallback (`GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD`),
the `?gmail=<email>` sender mechanism, and Notion as a **runtime** dependency
(Notion is now used only by `migrate_to_db.py`).

## Deployment verification

Before relying on production, run through `docs/manual-verification.md` on the
deployed URL (the two OAuth flows, login round-trip, and invite-link survival
cannot be fully covered by unit tests).

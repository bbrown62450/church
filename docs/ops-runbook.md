# Operations runbook

The single place for the Supabase lockdown record, backup key custody and the
restore drill, the Streamlit freeze record, platform limits and incident
response. Design: `docs/superpowers/specs/2026-09-25-slice-ops-cleanup-design.md`
("the ops spec").

- An entry marked `[owner: …]` is a value only the owner can see (a dashboard,
  a SQL result, a message sent). Replace the whole marker with the value and
  the date.
- Never paste a secret here: no database URL with its password, no API key,
  no access token, no `age` private key.
- ops-3 adds "Environments and variables" at the top and "Keep-alive" after
  "Backups", and adds the freeze record, the policy and the recorded versions
  to "Streamlit freeze".

## Supabase lockdown record

Project `worship-staging`, ref `tbecmwtitsoxzkrvxxxu`. Procedure: the ops spec →
Data and migrations → Step 0. Done on 2026-09-25; the results are below. To
check again, connect with the session-pooler URL the apps use, but never put
the URL on a command line: shell history keeps it, and libpq quotes parts of a
malformed URL, password included, in its errors. From the repo root, in bash
or zsh, `.github/backup/pg_env.py` turns it into `PG*` variables:

```
IFS= read -rs BACKUP_URL        # paste the URL and press Return; nothing is shown
eval "$(python3 .github/backup/pg_env.py --exports <<<"$BACKUP_URL")"; unset BACKUP_URL
docker run --rm -it -e PGHOST -e PGPORT -e PGUSER -e PGPASSWORD -e PGDATABASE \
    -e PGSSLMODE=require postgres:17 psql
unset PGHOST PGPORT PGUSER PGPASSWORD PGDATABASE    # when finished
```

If `psql` is installed, plain `PGSSLMODE=require psql` can replace the
`docker run` line.

**1. Exposure before the lockdown.** For each of `users`, `gmail_tokens`,
`invites` and `memberships`:

```
curl -s "https://tbecmwtitsoxzkrvxxxu.supabase.co/rest/v1/<table>?select=*&limit=1" \
  -H "apikey: <anon key>" -H "Authorization: Bearer <anon key>"
```

Then again with `Authorization: Bearer <your own access token>` (the
`authenticated` role, which any Google user can get by signing in).

| Role | Result | Date |
|---|---|---|
| anon | Not run as an exposure test: the Data API was already off. REST and GraphQL requests with the anon key return HTTP 503 `PGRST002` and no rows. | 2026-09-25 |
| authenticated | Not run: with the Data API off, `/rest/v1` serves no table to any role. | 2026-09-25 |

Any rows returned mean an incident: complete "Incident response" below. None
were returned, so there was no incident.

**2. Can RLS be enabled safely?** Through the pooler URL:

```sql
select tablename, tableowner from pg_tables where schemaname = 'public' order by 1;
select current_user, rolbypassrls from pg_roles where rolname = current_user;
show server_version;
```

| Check | Result (2026-09-25) |
|---|---|
| Owner of every `public` table | `postgres` |
| `current_user`, `rolbypassrls` | `postgres`, `true` |
| `server_version` (its major also goes in "Platform limits") | `17.6` |
| RLS safe: `current_user` owns every table or has BYPASSRLS | Yes (both) |

**3. Lockdown applied.**

| Action | Result | Date |
|---|---|---|
| (a) Dashboard → Project Settings → Data API: off | Already off before Step 0; left off. REST and GraphQL requests with the anon key return HTTP 503 `PGRST002` and no data. | 2026-09-25 |
| (b) Enable RLS on every `public` table (the `DO` block below) | Applied | 2026-09-25 |
| (b) The two REVOKEs from `anon` and `authenticated`, and the two `ALTER DEFAULT PRIVILEGES` (below) | Applied | 2026-09-25 |

```sql
-- Defense in depth; slice 1's 0003_lockdown repeats this idempotently.
DO $$
DECLARE t text;
BEGIN
  FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
  END LOOP;
END $$;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated;
```

If step 2 said "no", skip the `DO` block: RLS with no policies would hide every
row from both apps. Apply (a) and the REVOKEs only; slice 1 decides between
transferring table ownership and adding policies (ops spec, Risks item 1).

**4. Confirmation.**

| Check | Result | Date |
|---|---|---|
| Step-1 curls with the anon key: no rows | HTTP 503 `PGRST002`, no rows | 2026-09-25 |
| Step-1 curls with your access token: no rows | Not run: the Data API is off for every role | 2026-09-25 |
| GraphQL introspection lists no app tables (no `usersCollection`) | HTTP 503 `PGRST002`, no data | 2026-09-25 |
| `/me` works on https://worship-service-builder.vercel.app | Yes: the Vercel app loads the owner's church | 2026-09-25 |
| https://liturgy-stg.streamlit.app loads the owner's church | Yes | 2026-09-25 |
| Incident response needed (step 1 returned rows)? | No: the Data API was already off | 2026-09-25 |

GraphQL check:

```
curl -s -X POST https://tbecmwtitsoxzkrvxxxu.supabase.co/graphql/v1 \
  -H "apikey: <anon key>" -H "Content-Type: application/json" \
  -d '{"query":"{ __schema { queryType { fields { name } } } }"}'
```

**Rollback:** `ALTER TABLE public.<t> DISABLE ROW LEVEL SECURITY` for each
table, and turn the Data API back on. The REVOKEs need no rollback, because no
app uses those roles.

## Backups

- **Workflow:** `.github/workflows/backup.yml` (`db-backup`). Daily at 08:37 UTC,
  and by hand from `main`: Actions → db-backup → Run workflow (branch `main`),
  or `gh workflow run db-backup --ref main`.
- **What it does:** checks the server's Postgres major against `PG_MAJOR`,
  dumps the `public` schema with `pg_dump --format=custom --no-owner
  --no-privileges`, pipes it through `age` to every key in
  `.github/backup/age-recipients.txt`, and uploads
  `backup-<UTC timestamp>.dump.age` as the artifact `db-backup`, kept 30 days.
  No plaintext dump touches the runner's disk. Supabase-managed schemas
  (`auth`, `storage`) are not included; users sign in again with Google and are
  matched by email.
- **Secret:** `BACKUP_DATABASE_URL`, an **environment secret** of the GitHub
  Environment `backup` (repo Settings → Environments → `backup`), whose
  deployment-branch rule admits only `main`, so a workflow on any other branch
  cannot read it. There is no repository secret of that name. The value is
  the Supabase **session pooler** URL the apps use. The direct host is
  IPv6-only on Free and GitHub runners are IPv4. The SQLAlchemy form
  (`postgresql+psycopg2://…`) is fine: `.github/backup/pg_env.py` reads the
  URL as the app does, masks each part in the log (password, user, host,
  whole URL), and hands the parts to `psql` and `pg_dump` as `PG*` variables,
  so the URL never reaches a command line. The secret is added only after the
  encrypted workflow is on `main`; until then every run fails at "Check
  prerequisites", which is intended. Scheduled runs use `main`; a manual run
  from any other branch is refused by the environment.
- **Artifacts** are encrypted, so it is acceptable that anyone signed in to
  GitHub can download them from this public repo.

### Key custody

1. Created once with `brew install age`, then `age-keygen -o ~/wsb-backup-key.txt`.
2. The whole key file is stored in the owner's password manager, plus one
   offline copy; then the file is deleted from disk.
3. The private key never goes to GitHub, Railway, the repo or chat. Only the
   `age1…` public line is committed, in `.github/backup/age-recipients.txt`.
4. Every public key in that file can decrypt every new backup. An optional
   second recovery key, stored apart from the first, protects against losing
   the first.

| Key | Where the private key is kept | Created |
|---|---|---|
| `age1zl8f90cg` | [owner: password-manager entry name; offline copy: yes/no] | 2026-09-26 |

### Rotating the key

1. Generate and store the new key as in "Key custody".
2. PR: add its `age1…` line to `.github/backup/age-recipients.txt` next to the
   old one. After merging, run db-backup by hand and decrypt that artifact
   with the new key (the download and `age --decrypt` lines of the restore
   drill).
3. PR: remove the old line. Keep the old private key for 30 more days, until
   the last artifact encrypted to it has expired, then destroy every copy.
4. If a private key is exposed: remove its line at once, delete the existing
   `db-backup` artifacts (Actions → db-backup → each run → Artifacts), and run
   db-backup by hand so a fresh backup exists under the remaining keys.

### Restore drill (once in the ops slice, then quarterly)

```
cd "$(mktemp -d)"                                            # a fresh, empty folder
gh run download <run-id> -R bbrown62450/church -n db-backup  # or download from the Actions UI
ls backup-*.dump.age                                         # exactly one file: use its full name below
# Save the whole key file from the password manager as ~/wsb-backup-key.txt, then:
age --decrypt -i ~/wsb-backup-key.txt -o backup.dump backup-<timestamp>.dump.age
docker run --rm -d --name wsb-restore -e POSTGRES_PASSWORD=restore postgres:17
until docker exec wsb-restore pg_isready -h 127.0.0.1 -U postgres; do sleep 1; done
docker exec -i wsb-restore pg_restore -h 127.0.0.1 -U postgres -d postgres --no-owner --no-privileges < backup.dump
docker exec wsb-restore psql -h 127.0.0.1 -U postgres -Atc "select 'users', count(*) from users union all select 'churches', count(*) from churches union all select 'services', count(*) from services union all select 'hymns', count(*) from hymns"
docker stop wsb-restore
rm -f backup.dump ~/wsb-backup-key.txt backup-*.dump.age     # the plaintext dump holds Gmail refresh tokens; the key never stays on disk
```

If you stop early (for example Ctrl-C during the `pg_isready` wait), still run
the cleanup `rm …` line and `docker stop wsb-restore`, so no plaintext dump or
key file is left on disk.

- Use an image tag at least as new as the server major (`PG_MAJOR`).
- The wait uses TCP (`-h 127.0.0.1`) because the image first runs a temporary,
  socket-only server for initdb and then restarts; a socket connection can hit
  that temporary server and be cut off in the middle of the restore.
- Expected: at most the harmless `schema "public" already exists` error, and
  every table restored.
- Run the same count query on production (Supabase SQL editor) and compare.
  Rows written between the dump and the check are the only allowed difference.

| Date | Run | Artifact | Counts: restored / production (users, churches, services, hymns) | Result |
|---|---|---|---|---|
| [owner] | [owner: run URL] | [owner: backup-….dump.age] | [owner] | [owner] |

### Backup run record

| Date | Run | Result |
|---|---|---|
| 2026-09-26 (first manual run after ops-1) | https://github.com/bbrown62450/church/actions/runs/36261197972 | Green. Artifact `db-backup` (225,686 bytes, encrypted), expires 2026-10-26. A scan of the public log found no database host, user, URL, `PGPASSWORD` or private-key text; 4 values were masked as `***`. |

## Streamlit freeze

### Streamlit apps

The ops spec names `liturgy` as production and deletes `liturgy-stg`. The
owner corrected this on 2026-09-25: it is the other way round.

| App | URL | Status |
|---|---|---|
| `liturgy-next` | https://liturgy-next.streamlit.app/ | **Production.** The owner and the tester use it. On 2026-09-26 it deploys from repo `bbrown62450/church`, branch `main`, main file `app.py`. `liturgy-stg`, which ran from the old branch `claude/multi-user-app-support-edd5eb`, was deleted that day during Task 9a. Streamlit Community Cloud allows only one app per repository + branch + main file, and `liturgy-next` (created earlier as a side-by-side test) already held `main`/`app.py`. So the owner kept `liturgy-next` as the production address instead of recreating `liturgy-stg`. Its Secrets carry `[auth] redirect_uri = https://liturgy-next.streamlit.app/oauth2callback` and `GOOGLE_OAUTH_REDIRECT_URI = https://liturgy-next.streamlit.app/`, and both are registered on the Google OAuth client. The owner checked sign-in, church and hymnal, saved services and a Gmail test send. `keep-awake` keeps it awake. ops-3's Freeze still has to move production onto `streamlit-frozen`, at this address. |
| `liturgy` | https://liturgy.streamlit.app/ | **Deleted 2026-09-26** (it was unused; its Google sign-in failed with `StreamlitAuthError` from its secrets config). The URL now returns 404. Its two Google redirect URIs (`https://liturgy.streamlit.app/oauth2callback` and the bare root `https://liturgy.streamlit.app/`) can be removed from the OAuth client; they are harmless meanwhile. |

### Streamlit bug triage

Every Streamlit bug in the inventory, checked against the freeze policy's
definition of a data-safety fix: data loss, corruption, leakage or security.
"Stored data" means rows in the database; losing text typed but not yet saved
is a usability bug, not a data-safety one.

| Inventory | Bug | Meets the definition? | Disposition |
|---|---|---|---|
| D5, and F6 "drops a loaded service's own hymns" | With "Exclude hymns used in the last 12 weeks" ticked, Prepare records the picks and reruns; the picks are now "recent", `safe_hymn_selectbox` resets them to '', and the next Prepare or Save stores no hymns. Loading a recent archived service with the box ticked drops its hymns, and "Save changes" then overwrites the archived hymns. | **Yes: silent loss of stored data in the normal Prepare → Save flow** | **Fixed in ops-1** (below). Until the fix is live, the tester relies on the D5 workaround message; the date it was sent is in the D5 record below. |
| A7 | A Word file prepared for church A can be downloaded or emailed while church B is active, to church B's contacts. | Leakage, in principle | **Accepted.** The tester belongs to one church, and Streamlit offers no way to join or create a second one (onboarding runs only at zero churches, inv A5), so the switcher never renders (the pre-freeze smoke check confirms there is no "Church" selectbox in the sidebar). React keys the draft and documents by church (slice 2, 5a). |
| E6 | Raw provider error text, or the "[Configure OPENAI_API_KEY…]" placeholder, becomes the liturgy text and can be saved or printed. | Corruption, in principle | **Accepted.** The Preview shows the text before Prepare or Save, so it is never saved silently, and Streamlit blocks Generate entirely when no key is set (inv E6). The new app shows such stored text as ordinary text and never writes error text itself (F §6.2). |
| E4 | Generate replaces the liturgy wholesale, so an unticked section of a loaded service disappears, and "Save changes" then overwrites it. | Loss, but visible | **Accepted.** The section is visibly missing from the Preview before Save, and the loaded text is still in its "Your text" box, so ticking the section and generating again restores it verbatim (inv E2). |
| D6 | With no Opening hymn, the Response hymn is stored first and reloads into the Opening slot. | Corruption of the slot order, visible | **Accepted.** It happens only when Opening is left empty, and the shifted slot is visible in the pickers before the next Save. The new app always writes three positional entries (F §6.2). |
| F6 | A hymn renamed or deleted in Settings is silently dropped when a service that used it is loaded; the next Save stores it without that hymn. | Loss, rare and visible | **Accepted.** It needs a hymn rename or delete, and the empty slot is visible before Save. |
| F7 | Last write wins; any member can overwrite any service. | Loss under concurrent edits | **Accepted.** One person uses the app. `If-Match` arrives in 5a. |
| F10 | All recipients go in one visible To header. | Contacts see each other's addresses | **Accepted.** This is the behavior the tester already relies on, and the recipients are the church's own contacts. 5b moves them to BCC (owner decision 9). |
| D3, D7, E6, F9 | Member-editable hymn titles and links rendered as unescaped markdown; configuration details and raw exception text shown to members. | Security, low | **Accepted.** Only signed-in members of the tester's own church can write hymns or see these messages. The React UI escapes and uses fixed messages (F §1.5, §4.8). |
| G7, G8, B1 | Admins can grant owner; the role is not validated on invites; code-only invites can be reused. | Security | **Accepted** by F §6.2, because the owner is the tester. 6b fixes them. |
| F4 | Usage is recorded on Prepare and never removed; the check-then-insert can race. | Stale data, not loss | **Accepted** by F §6.2. 5a replaces usage per date on save. |
| B2, G2 | Timezones are free text. | No | Not data-safety. Slices 1, 2 and 6a validate them. |
| C1, C4 | No readings, or a reading-set switch, overwrites the occasion and scriptures typed but not yet saved. | No (nothing stored is touched) | Not data-safety. |
| G5 | On Postgres, hymns with no number beyond the first 50 can't be seen or deleted in Settings. | No (nothing is lost) | Not data-safety. 6a replaces the page. |
| inv §4 | The Data API exposed the tables; backups were unencrypted. | Security | **Fixed in ops** (Step 0, S2), outside the Streamlit code. Step 0 (2026-09-25) found the Data API already off, and added RLS and the REVOKEs. |
| inv §4 | Gmail refresh tokens are stored in plaintext. | Security | **Deferred to slice 7** (F §6.4), because the frozen app reads them. The lockdown and the encrypted backups remove the exposure paths. |

### D5 fix and recovery record

ops-1 adds `ui_helpers.hymn_options_excluding_recent`, which `app.py` uses when
"Exclude hymns used in the last 12 weeks" is ticked: hymns already picked in the
three slots stay selectable, so Prepare, Save and loading a recent service no
longer clear them. Recent hymns that are not picked stay hidden.

| Event | Date |
|---|---|
| D5 workaround message sent to the tester | Not sent (owner decision, 2026-09-26): the fix goes live right after the ops-1 merge, when production Streamlit moves to `main` (Task 9a; production became `liturgy-next` instead), so the window is short. |
| ops-1 build live on https://liturgy-next.streamlit.app/ | 2026-09-26 (liturgy-next deploys from `main`, which includes the D5 fix; the owner verified sign-in, church and hymnal, saved services and a Gmail test send) |
| D5 manual check passed on https://liturgy-next.streamlit.app/ | [owner] |
| "Fixed" message sent to the tester | [owner] |

**Recovery queries** (Supabase SQL editor, after the fix is live).

1. Archived services saved without hymns:

```sql
select church_id, service_date_iso, occasion, saved_at from services
where case when hymns is null or jsonb_typeof(hymns::jsonb) <> 'array' then true
           else jsonb_array_length(hymns::jsonb) = 0 end
order by service_date_iso desc;
```

2. Services that lost some of their hymns. Loading an older archived service
   with the box ticked clears only the slots whose hymn is recent, so "Save
   changes" can store one or two hymns. `hymn_usage` keeps what was recorded
   when the service was prepared, so a service that stores fewer hymns than
   its usage rows (at most 3) is a candidate. It also lists query 1's rows
   that have usage, and a service whose picks were changed between two
   Prepares can show up without having lost anything, so ask before re-saving.

```sql
select s.church_id, s.service_date_iso, s.occasion, s.saved_at,
       case when jsonb_typeof(s.hymns::jsonb) = 'array' then jsonb_array_length(s.hymns::jsonb) else 0 end as stored,
       count(u.id) as used
from services s
left join hymn_usage u on u.church_id = s.church_id and u.date_iso = s.service_date_iso
group by s.id
having least(count(u.id), 3) >
       case when jsonb_typeof(s.hymns::jsonb) = 'array' then jsonb_array_length(s.hymns::jsonb) else 0 end
order by s.service_date_iso desc;
```

For each row of either query, this lists the hymns picked when the service was prepared:

```sql
select hymn_number, hymn_title from hymn_usage
where church_id = '<church_id>' and date_iso = '<service_date_iso>';
```

Ask the tester whether the service really had no hymns, or only the ones it
stores. If hymns are missing, the tester loads it, picks them again and clicks
"Save changes".

Result: [owner: "no rows" for both queries, or per row: the query, the date, the hymns `hymn_usage` lists, the tester's answer, and whether the service was re-saved]

## Platform limits

- Railway public networking: a request is closed after 5 minutes with no data
  transferred, and can run up to 15 minutes while data keeps flowing
  (https://docs.railway.com/networking/public-networking/specs-and-limits,
  checked 2026-09-25). F §1.8 needs at least 120 s: OK. Never add a test
  endpoint that sleeps.
- Postgres server major: 17
- Postgres `server_version`: 17.6 (2026-09-25)
- The `Postgres server major` line is read by
  `backend/tests/test_ops_workflows.py`, which fails unless it equals
  `PG_MAJOR` in `.github/workflows/backup.yml`. Change both together; the
  backup job also refuses to run when the server major differs.
- Supabase session pooler (Supavisor) Pool Size: 15 (Nano compute; max client
  connections 200), 2026-09-25 (Dashboard → Database → Connection pooling).
- Budget (ops spec, Risks item 2): 2 × (`DB_POOL_SIZE` + `DB_MAX_OVERFLOW`) + 2
  must not exceed the Pool Size; the 2 is the backup job's one session plus
  the owner's SQL editor. The spec's 5 + 5 needs 22 > 15, so the trigger
  fired. The values are `DB_POOL_SIZE=3` and `DB_MAX_OVERFLOW=3`:
  2 × (3 + 3) + 2 = 14 ≤ 15. `backend/.env.example` says the same.
- Hand-off to ops-2: the engine's code defaults must be 3 and 3, not the
  spec's 5 and 5.
- Until ops-2 merges, no code reads these variables: `backend/db/engine.py`
  sets no pool size, so each process can hold SQLAlchemy's default 5 + 10 = 15
  sessions. The API, `liturgy-stg` and (until it is deleted) `liturgy` can
  together ask for 45 against 15. Real use by one tester is 2–4. Deleting
  the unused `liturgy` app frees its share.
- Values set: `DB_POOL_SIZE=3` and `DB_MAX_OVERFLOW=3` as Railway service
  variables (API), and as top-level keys `DB_POOL_SIZE = "3"` and
  `DB_MAX_OVERFLOW = "3"` in the `liturgy-stg` app's Streamlit Secrets (not
  `liturgy`, which is being deleted): 2026-09-26 (Railway API service and `liturgy-stg` Secrets)
- GitHub Actions artifacts: `db-backup` keeps 30 days (GitHub's maximum is 90).

## Incident response

Only if Step 0, step 1 returned rows. Do it the same day (Supabase Free keeps
logs for a short time). Steps 1–3 come before any repair.

1. **Preserve evidence.** Take an encrypted dump before changing any row; it
   never exists in plaintext. First load the pooler URL into `PG*` variables
   (the `read` and `eval` lines in "Supabase lockdown record"), then:
   ```
   docker run --rm -e PGHOST -e PGPORT -e PGUSER -e PGPASSWORD -e PGDATABASE \
       -e PGSSLMODE=require postgres:17 pg_dump --schema=public --format=custom \
     | age --encrypt -r <your age1… public key> > incident-$(date -u +%Y%m%dT%H%M%SZ).dump.age
   unset PGHOST PGPORT PGUSER PGPASSWORD PGDATABASE
   ```
   Use an image tag at least as new as the server major. Keep the file
   offline next to the key, not in the repo or in GitHub.
2. **Review the API logs.** Dashboard → Logs → API: list the `/rest/v1` and
   `/graphql/v1` requests you didn't make, especially `POST`, `PATCH` and
   `DELETE`, with dates, methods, paths and IPs.
3. **Check for tampering** in every table the default grants let a caller
   write:
   - `users`, every row: compare `email`, `google_sub`, `name` and
     `created_at` with the known users. Identity is matched by email, so a
     changed `users.email` on the owner's row hands the owner's memberships to
     whoever signs in with that address. Look for rows created for people you
     don't know.
   - `memberships` (unexpected rows or roles) and `invites` (unexpected rows,
     especially with the admin or owner role).
   - `contacts`: unexpected recipients (bulletins are emailed to them).
   - `churches`: `name`, `settings` and `deleted_at`.
   - `services`, `hymns`, `hymn_usage`, `hymn_catalog`: rows or edits you
     don't recognize (`services.saved_at` shows recent writes).
   - `gmail_tokens`: recently changed rows.
   - Purge `oauth_states`: `DELETE FROM oauth_states;` (a state is valid for
     10 minutes, so the only cost is restarting a Gmail connect in progress).
4. **Repair** from the forensic dump or the known values: a changed
   `users.email` first, before anyone signs in again; then memberships,
   contacts and settings.
5. Revoke every active invite in Streamlit Settings → Invites and reissue
   those still needed (invite codes are bearer secrets).
6. Send the tester the Gmail message (ops spec, User experience): remove the
   app's access at https://myaccount.google.com/permissions, then "Connect
   your Gmail" again.
7. Record everything below.

### Incident record

None: the Data API was already off (2026-09-25). REST and GraphQL requests
with the anon key returned HTTP 503 `PGRST002` and no rows, so the owner
recorded no incident and no incident steps were needed.

### Accepted risk: database password shared in a chat session

On 2026-09-25 the Supabase database password (the `postgres.<ref>` pooler user) was pasted into an AI coding-assistant chat while configuring Railway. On 2026-09-26 the owner decided not to rotate it. If it is rotated later, update it in: Supabase (Project Settings → Database → Reset database password; avoid `@ # / ?` to skip URL-encoding), Railway `DATABASE_URL`, the `liturgy-next` Streamlit Secrets `DATABASE_URL`, and the `backup` environment secret `BACKUP_DATABASE_URL`; then run the backup by hand and check `/me` and liturgy-next.

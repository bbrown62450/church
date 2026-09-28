# Manual Verification Checklist (deployed URL)

Run these on the **deployed** Streamlit Cloud URL after configuring `[auth]`,
`DATABASE_URL`, and the `GOOGLE_*` gmail.send client. These flows depend on real
redirects/cookies and cannot be fully covered by unit tests.

## 1. Gmail callback with `[auth]` CORS/XSRF enabled
- [ ] Enabling `[auth]` auto-enables Streamlit's CORS/XSRF protection. Confirm
      the manual gmail.send return to the **app root** with `?code=...&state=...`
      is delivered to app code (a top-level GET) and is **not** swallowed by
      Streamlit's internal `/oauth2callback` login handler.
- [ ] Click **Connect your Gmail**, complete Google consent, and confirm the
      refresh token is saved and a test bulletin sends from your own address.
- [ ] Confirm the sender is always the logged-in `st.user.email` (a spoofed
      `?gmail=` param has no effect) and that a missing/invalid OAuth `state`
      is rejected on callback.

## 2. Login round-trip
- [ ] Sign in with Google (`st.login`), reload, and confirm the 30-day cookie
      keeps you signed in.
- [ ] Sign out (`st.logout`) and confirm the app returns to the signed-out state.
- [ ] First-ever sign-in creates the user record; a user with no church sees the
      create-or-join empty state.

## 3. Invite link survives login
- [ ] Open an invite link (`?invite=CODE`) while signed out. After the Google
      login round-trip (and any gmail-connect round-trip), confirm the `?invite`
      param is preserved and the church is joined as `member`.
- [ ] Confirm an expired/revoked code fails cleanly, and accepting when already
      a member is a no-op.

## Slice 0 — React + FastAPI foundation

On the deployed Vercel URL, on a phone and on a desktop:

- [ ] `/` redirects to `/login` when signed out.
- [ ] Sign in with Google returns to `/` and shows your church in the switcher.
- [ ] Account menu shows name, email, and your role.
- [ ] Switching churches (if you have more than one) updates the role shown.
- [ ] Log out returns to `/login`.
- [ ] `https://<railway-domain>/health` returns `{"ok":true}`.
- [ ] `https://<railway-domain>/me` without a token returns 401 with the error shape.
- [ ] The Streamlit app still signs in and loads your church.
- [ ] Supabase → Authentication → Sign In / Providers: only Google enabled.
- [ ] Supabase email changes require confirmation: `curl -s -H "apikey: <publishable key>" https://<ref>.supabase.co/auth/v1/settings` shows `"mailer_autoconfirm": false` (users are matched by email, so auto-confirmed email changes would allow account takeover).

## Ops slice

Run on the production URLs: https://worship-service-builder.vercel.app (at
375 px in Chrome device mode, iPhone SE, and on desktop),
https://church-production-74ca.up.railway.app, and
https://liturgy-frozen.streamlit.app, the production Streamlit app since the
Freeze on 2026-09-26 (the only one: `liturgy` and `liturgy-stg` were deleted
that day, and `liturgy-next`, production until the Freeze, was deleted in it).
Record each result, with its date, in `docs/ops-runbook.md`.

- [ ] Step 0 recorded in `docs/ops-runbook.md` (done on 2026-09-25; confirm the records are there, do not redo the checks): the exposure checks (the Data API was already off: REST and GraphQL with the anon key return 503 `PGRST002` and no rows, so no incident), GraphQL introspection, table owners and BYPASSRLS, `server_version` 17.6 and the `- Postgres server major: 17` line, the pooler Pool Size 15 with 2 × (3 + 3) + 2 = 14 ≤ 15, and Railway's request limit with its source. If a later exposure check ever returns rows: the incident record, including the users/contacts audit and where the forensic dump is kept.
- [ ] D5 workaround message: sent to the tester on day one, or the owner's decision not to send it recorded (as on 2026-09-26).
- [ ] D5 fix, live in production since the ops-1 merge (on `liturgy-next` until the Freeze, on `liturgy-frozen` since), in a throwaway church, on https://liturgy-frozen.streamlit.app: sign in with a second Google account that has no church and create "Ops test". Tick "Exclude hymns used in the last 12 weeks", pick three hymns, generate the liturgy, click "Prepare bulletin copy": the three picks are still selected. Click "Prepare pastor's copy": both Word files list the three hymns. Save, then load the service again with the box still ticked: its three hymns are in the slots. Delete "Ops test" in Settings → Danger zone. Then run the recovery queries, record the result, and send the tester the "fixed" message.
- [ ] https://worship-service-builder.vercel.app, after the lockdown and after each ops merge: sign in, the church shows in the switcher, switch church if you have two, log out.
- [ ] `db-backup` run by hand: green, with an artifact `backup-*.dump.age`; the log shows no URL or password. The restore drill's counts match production.
- [ ] `https://church-production-74ca.up.railway.app/health/ready` → `{"ok":true,"db":"ok"}`. The `keepalive` run by hand is green.
- [ ] Railway deploy log after ops-3: `Database: dialect=postgresql driver=psycopg2 host=…pooler.supabase.com database=postgres`, with no username or password, and no `CORS_ORIGINS allows only localhost` ERROR line.
- [ ] Browser devtools on the Vercel app: the `/me` response has an `x-request-id` header, and it is readable from JS: in the console, `fetch("https://church-production-74ca.up.railway.app/health").then(r => r.headers.get("x-request-id"))` resolves to an id, not `null`.
- [ ] `curl -i https://church-production-74ca.up.railway.app/me/` → 404 JSON with `request_id`, and no `location` header (not a 307).
- [ ] `liturgy-next` after the ops-3 merge (rebooted), and `liturgy-frozen`, the pre-flight app from `streamlit-frozen` that has served production since the Freeze (the owner kept it instead of moving it onto `liturgy-next`): sign in, the church and hymnal load, load a saved service, open Settings; on `liturgy-frozen` also connect Gmail and send a test email to yourself. Its settings show branch `streamlit-frozen`, main file `app.py`, Python 3.14 and Sharing public. After the next merge to `main`, its logs show no code pull (`Pulling code changes from Github`, `Updated app!`) and its settings still show `streamlit-frozen`.
- [ ] `keep-awake` is green with one URL, https://liturgy-frozen.streamlit.app/. The Google OAuth client "Liturgy" lists only the two `liturgy-frozen` redirect URIs among `streamlit.app` addresses: the deleted `liturgy` and `liturgy-stg` apps' four were removed before the Freeze, and the deleted `liturgy-next` app's two after it.

## Slice 1

Run on the production URLs: https://worship-service-builder.vercel.app (at
375 px in Chrome device mode, iPhone SE, and on desktop),
https://church-production-74ca.up.railway.app, and
https://liturgy-frozen.streamlit.app, the production Streamlit app. Record
each result, with its date, in `docs/ops-runbook.md` → Supabase lockdown
record → "Alembic stamping record (slice 1a)". The items marked "(after 1a)"
come from `backend/migrations/README.md` → Production runbook; slice 1b
appends its own items here.

- [ ] (after 1a) Runbook step 0 (RLS precondition) rerun and recorded; Railway → the API service → Settings → Deploy shows the Pre-deploy Command `alembic upgrade head` and the Healthcheck Path `/health/ready` (set in the UI; Railway does not read `/backend/railway.toml`); the merge deploy's log shows the **pre-deploy** `alembic upgrade head` (`0001_baseline -> 0002_reconcile`, `-> 0003_lockdown`, `-> 0004_invites_reusable`) and a passing `/health/ready` health check; `alembic current` shows `0004_invites_reusable (head)` and `alembic check` prints `No new upgrade operations detected.` (outputs pasted in the 1a PR).
- [ ] (after 1a) A new Google account signing in right after the 1a merge lands on the stub `/welcome` ("No church yet"), not a 404, and **Log out** returns it to `/login`; at 375 px and on desktop.
- [ ] (after 1a) Streamlit smoke check on https://liturgy-frozen.streamlit.app (F §6.3): sign in, the church and hymnal load, a saved service loads, Settings opens; Settings → Invites → **Create invite** works (the frozen app's insert gets `reusable = false`), then revoke that invite.

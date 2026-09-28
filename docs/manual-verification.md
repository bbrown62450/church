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
each result, with its date, in `docs/ops-runbook.md`: the items marked
"(after 1a)" under Supabase lockdown record → "Alembic stamping record (slice
1a)", and the items marked "(after 1b)" under "Slice 1b record", the section
after it, which the docs-only `claude/slice-1b-records` PR fills. The items
marked "(after 1a)" come from `backend/migrations/README.md` → Production
runbook. The items marked "(after 1b)" are the slice 1 spec's manual checks
2–11 in the order they run: check 4 comes after checks 5 and 6, so that C
already has churches when it joins (owner decision 9), and check 7 after check
4, so that C can switch between Member and Owner. Never record an invite
code, an invite link or an email address.

- [ ] (after 1a) Runbook step 0 (RLS precondition) rerun and recorded; Railway → the API service → Settings → Deploy shows the Pre-deploy Command `alembic upgrade head` and the Healthcheck Path `/health/ready` (set in the UI; Railway does not read `/backend/railway.toml`); the merge deploy's log shows the **pre-deploy** `alembic upgrade head` (`0001_baseline -> 0002_reconcile`, `-> 0003_lockdown`, `-> 0004_invites_reusable`) and a passing `/health/ready` health check; `alembic current` shows `0004_invites_reusable (head)` and `alembic check` prints `No new upgrade operations detected.` (outputs pasted in the 1a PR).
- [ ] (after 1a) A new Google account signing in right after the 1a merge lands on the stub `/welcome` ("No church yet"), not a 404, and **Log out** returns it to `/login`; at 375 px and on desktop.
- [ ] (after 1a) Streamlit smoke check on https://liturgy-frozen.streamlit.app (F §6.3): sign in, the church and hymnal load, a saved service loads, Settings opens; Settings → Invites → **Create invite** works (the frozen app's insert gets `reusable = false`), then revoke that invite.

Slice 1b setup. Accounts: **A** is the owner's own Google account; **B** and
**C** are two other Google accounts that belong to no church before these
checks (check 8 needs "1b Invite Test" to be B's only church).
Every invite is made in liturgy-frozen: Settings → Invites → **Create
invite**, with its Role (member or admin) and "Bind to email (optional)"; the
app shows the code once. Streamlit invites are single-use in the new app
(`reusable = false`). Build the link by hand as
`https://worship-service-builder.vercel.app/join?code=<code>`, and never put a
code into a record or a chat. Use throwaway churches only, never the tester's,
each with a name no church has yet (frozen Streamlit's switcher keys churches
by name; add a suffix if a name is taken). Each account may create at most 5
churches in 24 hours, soft-deleted churches and churches created in Streamlit
included; these checks create 1 as A and 3 as C. Start as A in the new app:
church switcher → "Join or create a church…" → **Create a church** → Church
name "1b Invite Test" → **Create church** (frozen Streamlit offers
onboarding only to an account with no church). Then in liturgy-frozen as A:
sidebar Church → "1b Invite Test" → Settings → Invites → **Create invite**
(Role member, no email) → build the link.

- [ ] (after 1b) **2.** In a private window, signed out, open the link: the address bar shows `/join` and the "You're invited" card appears. **Sign in with Google** as B → back on `/join`; the preview shows "1b Invite Test", "You're invited to join as a member." and "Invite expires …". **Join 1b Invite Test** → home with "1b Invite Test" active and the toast "Joined 1b Invite Test.". In liturgy-frozen as A, the invite is gone from Settings → Invites (the list hides accepted invites).
- [ ] (after 1b) **3.** In a second browser profile, open the same link and sign in with Google as C → "This invite has already been used." and "Ask for a new invite link."; **Go to home** → `/welcome` (C has no church). In B's window, open the link again → "You're already a member of 1b Invite Test." with no role line; **Open 1b Invite Test** → home with it active and the toast "You're already a member of 1b Invite Test.".
- [ ] (after 1b) **5.** As C on `/welcome`, with DevTools → Network open: **Create a church** → Church name "1b Test C", Time zone left at its default (the browser's zone, preselected) → **Create church** → the toast "Created 1b Test C. You're the owner." and home with "1b Test C" active and "Role: Owner" in the account menu. Record the `churches` request's Timing → "Waiting for server response" (S Risk 3; above 5 s, seeding moves to `INSERT … SELECT` in a follow-up). In the Supabase SQL Editor (read-only): `select (select count(*) from hymn_catalog) as catalog, (select count(*) from hymns h join churches c on c.id = h.church_id where c.name = '1b Test C') as seeded;` → the two numbers are equal.
- [ ] (after 1b) **6.** As C: church switcher → "Join or create a church…" → **Create a church**, with DevTools → Network throttling "Slow 4G". Leave the name blank and tap **Create church** → "Church name is required." under the field and no `churches` request in the Network panel. Enter "1b Test C2" and double-tap **Create church** → exactly one "1b Test C2" in the church menu. Set throttling back to "No throttling".
- [ ] (after 1b) **4.** In liturgy-frozen as A: sidebar Church → "1b Invite Test" → Settings → Invites → **Create invite** with Role member and "Bind to email (optional)" set to C's email → build its link. Open it in B's window (signed in as B) → "This invite was issued for a different email address." and "You're signed in as" with B's email. **Use a different Google account** → Google's account chooser appears (the app asks for it with `prompt=select_account`, S Risk 8; record whether it appeared, since the card has a fallback line if it does not) → choose C → back on `/join` → the preview with "This invite is for" and C's email → **Join 1b Invite Test** → the toast "Joined 1b Invite Test.". C already had churches (owner decision 9).
- [ ] (after 1b) **7.** As C (in "1b Test C", "1b Test C2" and "1b Invite Test"): church switcher → "Join or create a church…" → `/welcome` shows "← Back to" the active church → **Create a church** → "1b Test C3" → the church menu lists all four; switching between "1b Invite Test" and "1b Test C3" changes the role shown (Member, Owner). C has now created 3 churches in 24 hours.
- [ ] (after 1b) **8.** In a new private window, sign in as B and make "1b Invite Test" active. In liturgy-frozen as A: sidebar Church → "1b Invite Test" → Settings → Members → **Remove** next to B. B refocuses the tab → the toast "You no longer have access to 1b Invite Test." and B falls back to another church, or to `/welcome` if B has none.
- [ ] (after 1b) **9.** As B on `/welcome` (church switcher → "Join or create a church…" if B still has a church) → account menu → **Log out** → `/login`. B's session on a second device (a phone), signed in beforehand, stays signed in (`scope: "local"`).
- [ ] (after 1b) **10.** At 375 px: no horizontal scroll on `/welcome` (both tabs), `/join` (the "You're invited", preview and rejected cards, and https://worship-service-builder.vercel.app/join with no code for "This invite link is incomplete.") and home; inputs do not zoom on iOS (font size ≥ 16 px); tap targets ≥ 44 px.
- [ ] (after 1b) **11.** Streamlit smoke on https://liturgy-frozen.streamlit.app (F §6.3): sign in, the church and hymnal load, a saved service loads, Settings opens. As C there: "1b Test C" is in the sidebar Church list and its hymnal loads. As A: sidebar Church → "1b Invite Test" → Settings → Invites → **Create invite** (Role member, no email), then Settings → Danger zone → type "1b Invite Test" → **Delete church** (a soft delete that also revokes its invites); open that invite's link in the new app as C → "This invite has been revoked." (revoked is checked before church_unavailable).

Slice 1b regression pass (F §5.5), after the items above: sign in, switch
church, open home (1b ships no nav items). Optional clean-up: as C in
liturgy-frozen, Settings → Danger zone deletes "1b Test C", "1b Test C2" and
"1b Test C3" (soft deletes; they still count toward C's cap for 24 hours).

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

## Slice 2

Run on the production URLs: https://worship-service-builder.vercel.app (at
375 px in Chrome device mode, iPhone SE, and on desktop) and
https://liturgy-frozen.streamlit.app, the production Streamlit app. These are
the slice 2 spec's manual checks 1-13 (slice 2 spec → Manual checks), with a
Saturday added to check 2 (owner answer Q1, 2026-09-29: no one-tap Sunday
readings) and check 14 for "New service" (owner answer Q2). After the 2c merge
the owner's guided check (owner answer Q3: about six steps on the phone, given
one at a time, then a quick look on a computer) covers the
items marked "(owner, after 2c)", some of them in part; its result goes into
`docs/ops-runbook.md` → "Slice 2c record", which says what ran. The rest can
be run at any time and recorded the same way. Reading texts and dates come from the live
lectionary and Bible sites, so record what the page shows, never an email
address or a church id.

- [ ] (owner, after 2c) **1.** A church with no draft on this device opens `/` → `/builder/readings`, dated next Sunday in the church's time zone, with the occasion and readings filled and the step bar showing Date & readings as Complete.
- [ ] (owner, after 2c) **2.** Change the date to a plain Tuesday: "No lectionary readings for …" with **Enter readings**, plus the note "These readings are from … not …" with **Clear readings**; focus stays on the date. A Saturday (for example 2026-10-10) also falls back to manual entry. Ash Wednesday 2027 (2027-02-10) shows "Ash Wednesday"; Good Friday 2027 (2027-03-26) finds readings; Thanksgiving (2026-11-26) shows four lines.
- [ ] (owner, after 2c) **3.** Palm Sunday 2027 (2027-03-21): two set cards under "This date has more than one set of readings", with the Passion set selected; tapping the Palms card changes the readings.
- [ ] (owner, after 2c) **4.** Type an occasion or a reading of your own: the caption reads "Entered by you" or "Edited from the lectionary (…)". Change the date: "Readings for … are available." appears; **Use them** asks "Replace your readings?" first; **Keep mine** there hides the banner and the "Use the lectionary's readings" link for that date until the tab closes (Escape only closes the question). On another date, after typing over its readings, "Use the lectionary's readings" puts them back, asking first. On a date whose readings filled themselves, delete the Psalm line: no banner.
- [ ] **5.** Easter Day 2026 (2026-04-05): choose the Easter Vigil set: 11 lines, no heading lines, no "too long" message; **Show text** on "Romans 6:3-11 and Psalm 114" loads both passages.
- [ ] **6.** On desktop, type a date digit by digit: one lookup in DevTools → Network, and focus never jumps to Occasion.
- [ ] **7.** Refresh on every step: the draft is kept. A second tab edits: the first tab shows "Updated from another tab." Switch church and back: the drafts are separate.
- [ ] (owner, after 2c) **8.** **Show text** on "Isaiah 50:4-9a": the text loads. Switch **Bible translation**: the text changes. ESV is offered (production has the key).
- [ ] (owner, after 2c) **9.** Bulletin readings: the automatic New Testament reading is the epistle, never the Psalm. With Easter-season lines, the automatic Old Testament reading is the first line (Acts) and the New Testament one the epistle; pick the Psalm as the Old Testament reading and the New Testament one becomes Acts; **Use automatic** undoes it. Edit a picked line and leave the field: the pick goes back to automatic. Edit a picked line and refresh without leaving the field: after the reload the pick is automatic.
- [ ] **10.** Go to Hymns, then open `/builder`: it lands on Hymns. With a second tab open, moving between steps in one tab shows no "Updated from another tab." in the other.
- [ ] **11.** With the network off (DevTools offline) on a new date: "The lectionary couldn't be reached. …" with **Try again**; back online, **Try again** recovers.
- [ ] (owner, after 2c) **12.** At 375 px: no sideways scroll, even with a long reference typed without spaces; the footer stays at the bottom above the home indicator; inputs do not zoom on iOS. On desktop: the summary sits in the right column with the readings and their OT and NT marks.
- [ ] **13.** Regression: sign in, switch church, open the Builder nav item; the Streamlit smoke check on https://liturgy-frozen.streamlit.app (F §6.3).
- [ ] (owner, after 2c) **14.** After picking a date or choosing a reading set, **New service** asks "Start a new service?". On an untouched draft it starts over at once, and so it does when only the Bible translation was changed, keeping that translation (2c build).

## Slice 3

Run on the production URLs: https://worship-service-builder.vercel.app (at
375 px in Chrome device mode, iPhone SE, and on desktop) and
https://liturgy-frozen.streamlit.app, the production Streamlit app. These are
the slice 3 spec's manual checks 1-10 (slice 3 spec → Manual checks), with
check 11 for the church season in the AI prompt (owner answer 3, 2026-09-29)
and check 12 for "New service" (owner answer 1). After the 3b merge the
owner's guided check (owner answer 5: about six steps on the phone, given one
at a time, then a quick look on a computer) covers the items marked "(owner,
after 3b)", some of them in part; its result goes into `docs/ops-runbook.md` →
"Slice 3b record", which says what ran. The rest can be run at any time and
recorded the same way. Hymn titles, numbers and suggestions come from the
church's own hymnal and the live AI, so record what the page shows, never an
email address or a church id.

- [ ] (owner, after 3b) **1.** Open Hymns with readings for a real Sunday. "Hymns for the readings" shows matches in "Matches the readings" and "Same chapter". **Add** → **Opening hymn** fills the Opening card.
- [ ] (owner, after 3b) **2.** Search a picker by number and by part of a title. Two hymns with the same title are both listed, with different numbers, and either can be chosen. Typing a number then Enter chooses the top match (owner answer, 2026-09-30).
- [ ] (owner, after 3b) **3.** Turn **Exclude hymns used within 12 weeks** off and on. A recently used pick stays, with its "Used on …" notice. The "… hymns are hidden." count changes with the switch. Run this in the church whose services the old app holds: recent use is kept per church. On 2026-09-30 (slice 3b Task 1) no recent use showed because a test church with no services was selected; with the real church selected, 29 hymns showed as used within 12 weeks of 2026-10-04.
- [ ] (owner, after 3b) **4.** **Suggest hymns**: empty slots fill and every slot shows at least 2 ideas. Tap an idea, then tap the hymn it replaced: they swap back. Choose a slot yourself, suggest again: your pick stays.
- [ ] **5.** Tap **Cancel** during a suggestion: the button is back to "Suggest hymns". Suggest 41 times quickly (or lower the limit in a local run): "Too many requests — try again in … s.", then "Try again now." once the wait has passed.
- [ ] **6.** In a church with two hymnals: switch hymnals with **Hymnal**; the picks keep their hymnal badges. With PH1990 the "no scripture references" notes show.
- [ ] (owner, after 3b) **7.** Refresh the page mid-step: picks, ideas and the switch survive. Switch church and back: each church keeps its own draft. The step bar shows "n of 3", then "Complete", for Hymns, and the summary (bottom sheet at 375 px, right column on desktop) lists the three hymns or "No {Slot} hymn", with no "Available soon" in its Hymns block. Review lists each empty slot under "Still needed".
- [ ] (owner, after 3b) **8.** At 375 px: no sideways scroll, the ideas wrap, a picker's list is usable with the keyboard open, and the sticky footer does not cover the last card. A row with every badge (a long title with its hymnal, "Used …" and "Written …", in a picker list, on a card and in Hymns for the readings) moves its badges to a second line instead of widening the page; an idea stays one line, its title shortened. Tap a hymn's ✕: focus stays on the card (its heading) and the keyboard does not open (owner answer, 2026-09-30).
- [ ] **9.** Regression: sign in, switch church, open every shipped nav item; the Streamlit smoke check on https://liturgy-frozen.streamlit.app: load the church, load an archived service, open Settings (F §6.3).
- [ ] (owner, after 3b) **10.** In GG2013, **Suggest hymns** for a real Sunday: the ideas lean older and familiar, and any hymn written in 1970 or later shows "Written {year}". A picker search for a known modern hymn shows the badge; a nineteenth-century hymn does not.
- [ ] (owner, after 3b) **11.** On a Sunday in the Season after Pentecost (for example 2026-10-04), **Suggest hymns** offers no Palm Sunday, Holy Week, Easter, Advent or Christmas hymns unless the readings call for one.
- [ ] (owner, after 3b) **12.** After choosing a hymn or a hymnal, **New service** asks "Start a new service?". Turning Exclude on or off does not make it ask; Suggest fills empty slots, which does.

## Slice 4

Run on the production URL https://worship-service-builder.vercel.app, at 375 px
(Chrome device mode, iPhone SE) and on desktop, and the Streamlit smoke on
https://liturgy-frozen.streamlit.app. These are the slice 4 spec's manual
checks (slice 4 spec → Manual checklist), with check 10 for "New service"
(owner answer 1, 2026-09-30) and check 11 for a long section (owner answer 2).
After the 4b merge the owner's guided check (owner answer 4: six short steps
on the phone, given one at a time, then a quick look on a computer) covers the
items marked "(owner, after 4b)", some of them in part; its result goes into
`docs/ops-runbook.md` → "Slice 4b record", which says what ran. The rest can
be run at any time and recorded the same way. The AI's words differ every
time, so record what the page shows, never an email address or a church id.

- [ ] (owner, after 4b) **1.** Open Liturgy on a fresh draft: the 8 cards in the order of worship, Prayers of the People off; Benediction with the full Halverson text ("You go nowhere by accident. ..." in quotation marks, ending "- Richard Halverson"; owner decision 2026-10-02) and "Church default"; the landmark rows show the chosen hymns and readings.
- [ ] (owner, after 4b) **2.** Type a Call to Worship. Tap **Generate empty sections (5)**: the 5 empty switched-on sections fill within about a minute and one message says "Wrote 5 sections."; the Call to Worship is unchanged, character for character; the Benediction is untouched.
- [ ] (owner, after 4b) **3.** Regenerate the typed card: "Replace your text?" appears; **Replace text**, then **Undo** brings the typed text back.
- [ ] **4.** Start a bulk run, go to Hymns and back: the results are there. Cancel a run: the card is unchanged.
- [ ] **5.** Refresh mid-edit: the text is kept. Switch church and back: each church keeps its own liturgy.
- [ ] **6.** Communion is on for a first-Sunday date, off after changing the date, and stays as set after a toggle; **Use default** follows the date again. Its text shows under **Show communion text**.
- [ ] (owner, after 4b) **7.** Add, edit, move and remove (then **Undo**) a custom element. It shows right after its place.
- [ ] (owner, after 4b) **8.** At 375 px: no sideways scroll; the keyboard does not cover the focused text; the footer (Back, Next) hides while typing and comes back after; touch targets are at least 44 px. The Prayers of the People card's header fits: its switch, title and ⋯ on one line, and "Pastor's copy only" with the status chip (for example "Empty") on the line below. Switching a section off shows "Off — not in the service. Any text is kept." and switching it on shows the text again.
- [ ] **9.** Regression: sign in, switch church, open every shipped nav item; the Streamlit smoke check on https://liturgy-frozen.streamlit.app: load the church, load an archived service, open Settings (F §6.3).
- [ ] (owner, after 4b) **10.** **New service** asks "Start a new service?" after a card's text, a section switched on or off, a sermon title, a communion toggle or a custom element; on a fresh draft whose Benediction still shows the church default it does not ask.
- [ ] **11.** Switch on Prayers of the People and tap **Generate**: it fills (about 5 s in the 4a check; the page waits up to 100 s).

## Service reviewer

Run on the production URL https://worship-service-builder.vercel.app, at 375 px
(Chrome device mode, iPhone SE) and on desktop. These are the reviewer spec's
manual check (Testing) and the owner's guided check (owner answer 4,
2026-10-01): after the merge the owner runs the items marked "(owner, after
the reviewer)" on a phone, one step at a time, and takes a quick look on a
computer; the result goes into `docs/ops-runbook.md` → "Service reviewer
record". The AI's words differ every time, so record what the page shows,
never an email address or a church id. Items marked "(owner, after
follow-up 1)" are the owner's phone check after reviewer follow-up 1
(`docs/superpowers/plans/2026-10-01-reviewer-followup-1.md`); that result
goes into "Reviewer follow-up 1 record". Items marked "(owner, after
follow-up 2)" are the owner's phone check after reviewer follow-up 2
(`docs/superpowers/plans/2026-10-01-reviewer-followup-2.md`); that result
goes into "Reviewer follow-up 2 record".

- [ ] (owner, after the reviewer) **1.** On a liturgy with a typed Call to Worship and a few AI sections, tap **Review service**: a spinner and "Reviewing…", then notes under the cards (a tag such as "Rules" or "Read aloud", one sentence, an ×), "Looks good." on a card with none, and, when prayers repeat each other, an "Across the service" box at the top. A Benediction that still shows the church default gets no notes and no "Looks good." (owner, 2026-10-02); once you edit it, the next review covers it.
- [ ] (owner, after the reviewer) **2.** Dismiss one note with its ×: only that note goes.
- [ ] (owner, after the reviewer) **3.** On an AI card with a note, tap **Revise with these notes**: the text is replaced, "Revised with these notes. Undo" shows, and **Undo** brings the draft back.
- [ ] (owner, after follow-up 1) **4.** On the typed card with a note, tap **Revise with these notes**: "Replace your text?" asks first; **Keep my text** changes nothing; **Revise text** revises it, shows "Revised with these notes. Undo", and **Undo** brings your text back. A Benediction that follows the church default is not reviewed, so it has no notes and no Revise. (Before reviewer follow-up 1: typed cards had no Revise.)
- [ ] (owner, after follow-up 1) **5.** Type in a card that has notes: its notes stay, dimmed, under "From before your last edit.", and the other cards keep theirs; a card that said "Looks good." shows nothing after an edit; a new **Review service** replaces the dimmed notes. (Before reviewer follow-up 1: the notes went at once.)
- [ ] **6.** With the AI unavailable (or after a review that says so), the quick checks still show with "Only quick checks ran. The full review isn't available right now."
- [ ] (owner, after the reviewer) **7.** At 375 px: no sideways scroll; the Review service button sits beside or under "Liturgy"; note chips and sentences wrap; every × and button is at least 44 px.
- [ ] **8.** Start a review and tap **Cancel**: the spinner goes and nothing changes. Start one and choose **New service**: no notes remain.
- [ ] (owner, after follow-up 1) **9.** On a real review: no note only praises a prayer ("… fits well", "good focus on …"); a card with a "Cites …" note has no second note about naming the reading; a prayer named in "Several prayers open with …" has no note of its own about its opening, and "Across the service" has no second, AI-worded version of that note.
- [ ] (owner, after follow-up 2) **10.** With two or three prayers opening with the same words, **Review service**: under "Several prayers open with "…"." in "Across the service" there is **Revise the other prayers** (an AI note there has none). Tap it: the first of those prayers keeps its text; each of the others shows "Revising…" with its own Cancel from the start, and they are revised one at a time (about 10 s each), each with a new opening, different from the first and from each other, and "Revised with these notes. Undo"; the note goes once all were revised with new openings (if the AI kept the opening, the note and its button stay). When one of them is your own or saved text, "Replace your text?" asks first, once, naming them; **Keep my text** changes nothing. **Undo** on one card brings back only that card's text.

## Slice 5a

Run on the production URL https://worship-service-builder.vercel.app, on an
iPhone with Safari at 375 px and on desktop Chrome. These are the slice 5a
spec's manual checks (Testing → Manual checks) for the Word downloads, as
amended on 2026-10-01 (three PRs; no Streamlit check). After the 5a-1 merge
the owner's guided check (owner answer 8, one step at a time on the phone)
covers the items marked "(owner, after 5a-1)"; its result goes into
`docs/ops-runbook.md` → "Slice 5a-1 record". 5a-2 and 5a-3 add their own
items here. Record what the page and the file show, never an email address
or a church id.

- [ ] (owner, after 5a-1) **1.** Build a service and open **4 Review & send**. Tap **Download bulletin copy**: the button says "Preparing…", then the share or preview sheet opens with `worship_October_04_2026.docx` (for that date). The file opens; it has the title, the date as "October 04, 2026", "First Reading", the sermon title, the Benediction as the full Halverson text in quotation marks ending "- Richard Halverson" (unless the church saved its own), and no Prayers of the People.
- [ ] (owner, after 5a-1) **2.** Switch on Prayers of the People with text: the **pastor's copy** includes it and the bulletin copy does not. With it off, the pastor's copy says "Same as the bulletin copy for this service. Prayers of the People is empty or turned off."
- [ ] (owner, after 5a-1) **3.** Leave the Opening hymn empty and choose a Response hymn: the file has "Second Hymn" and no "First Hymn"; no hymn line ends in "#None".
- [ ] **4.** With RCL readings and no NT pick, the NT reading is the epistle, not the Psalm. Pick the Gospel as the NT reading, then edit that line: the Bulletin readings select shows "Automatic: {epistle}", and a new download prints that epistle.
- [ ] **5.** On desktop Chrome the download has the server's filename, and the file looks like the Streamlit one: Times New Roman 11 pt, Word's Heading 2 headings, People lines and the Prayer of Confession in bold, communion after the Second Hymn.
- [ ] **6.** Clear the service date: both download buttons are off with "Choose a service date on step 1 to download."
- [ ] (owner, after 5a-1) **7.** At 375 px: no sideways scroll on **Review & send**; the download buttons are full width and at least 44 px tall.
- [ ] **8.** Switch church: a download uses that church's draft.

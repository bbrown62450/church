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

Slice 5a-2 (saving on the server and `0005_services_extras`) changes nothing
on screen; saving from the app comes with 5a-3. Its items are the owner's
production steps around the merge (`backend/migrations/README.md` →
"Before 0005_services_extras") and a short phone check that the builder works
as before; the results go into `docs/ops-runbook.md` → "Slice 5a-2 record".

- [ ] (owner, before the 5a-2 merge) **9.** A green `db-backup` run; the read-only counts (version `0004_invites_reusable`, saved services, undated, old-style hymn lists); the SQL preview read: two `ADD COLUMN` lines and one `CREATE INDEX` between `BEGIN;` and `COMMIT;`, under the 5 s lock timeout.
- [ ] (owner, after 5a-2) **10.** The after-deploy query shows `0005_services_extras`, `2`, `1`, and the counts are unchanged.
- [ ] (owner, after 5a-2) **11.** On the phone the builder works as before: **2 Hymns** lists the hymnal, and **4 Review & send** still downloads the bulletin copy. Nothing new shows; "Saving services to the archive is coming soon." is still there.

Slice 5a-3 adds the Save card on **4 Review & send** and the **Services**
page. The owner's guided check after the merge (five steps on the phone)
covers the items marked "(owner, after 5a-3)"; its result goes into
`docs/ops-runbook.md` → "Slice 5a-3 record".

- [ ] (owner, after 5a-3) **12.** On **4 Review & send**, tap **Save to archive**: "Service saved", and the card says "Saved to the archive · {date and time}". **Services** in the menu lists the service at its date, with "Editing". After an edit the card says "Unsaved changes · last saved …" and the button "Save changes"; saving again says "Saved to the archive" with the new time.
- [ ] (owner, after 5a-3) **13.** **Start a new service**, date it a week after the saved service (a service's own date is never marked), then on **2 Hymns**: the saved service's hymns are marked as recently used.
- [ ] (owner, after 5a-3) **14.** On **Services**, open the saved service (after "Replace your unsaved draft?" if the draft has changes): Review shows "You're editing the saved service for {date}. …"; step 1 shows the saved occasion and readings, with no "Readings for … are available". Change the date: the button reads "Save as new service" and says why.
- [ ] (owner, after 5a-3) **15.** Save that copy, then delete it from **Services** ("Delete this service?", "Delete service"): it leaves the list, and if it was the one being edited the draft starts fresh.
- [ ] (owner, after 5a-3) **16.** At 375 px: no sideways scroll on **Review & send** or **Services**; the buttons and rows are easy to tap.
- [ ] **17.** In a second browser with the same service open, save it in one, then "Save changes" in the other: "Someone else changed this service"; "Reload their version" and "Save mine as a new service" both work.

## Printed bulletin

Run on the production URL https://worship-service-builder.vercel.app, on an
iPhone with Safari at 375 px and on desktop Chrome. These are the printed
bulletin spec's manual checks for PR 1 (the booklet from what the app knows,
with [placeholders] for the rest). After the PR 1 merge the owner's guided
check (one step at a time on the phone) covers the items marked "(owner,
after PR 1)", and the print test at the church covers "(owner, print
test)"; the results go into `docs/ops-runbook.md` → "Printed bulletin PR 1
record". PR 2 and PR 3 add their own items here. Record what the page, the
file and the paper show, never an email address or a church id.

- [ ] (owner, after PR 1) **1.** Build a service with readings, hymns and liturgy and open **4 Review & send**. Under **Printed bulletin**, tap **Download printed bulletin**: "Preparing…", then the share or preview sheet with `printed_bulletin_October_04_2026.pdf` (for that date). The PDF's pages are wide (legal, landscape), two booklet pages each, in reading order: the first has the cover (church name, the picture's box with the reading and the date) on the left and page 1, "THE SERVICE FOR THE LORD'S DAY", on the right; the announcements are the last page.
- [ ] (owner, after PR 1) **2.** In that PDF the readings are printed in full in the translation chosen on step 1, followed by "Scripture readings are from the …"; hymns read like `*HYMN: #409 "God Is Here!"`; the people lines are bold (after PR 2a the church's details and the names come from **Bulletin settings**, and after PR 2b-2 the music and the announcements from the **Bulletin** step; a blank one prints nothing; before PR 2b-2 they print as [placeholders]).
- [ ] (owner, after PR 1) **3.** Tap **Download Word version**: `printed_bulletin_October_04_2026.docx` opens in reading order (cover, the service, the announcements), on small pages.
- [ ] **4.** On step 1 choose another translation (for example KJV), then download again: the readings and the credit line change to it.
- [ ] (owner, after PR 1) **5.** At 375 px: no sideways scroll on **Review & send**; the two new buttons are full width and at least 44 px tall. Clear the service date: both are off with "Choose a service date on step 1 to download."
- [ ] (owner, print test) **6.** At the church, print the PDF on legal paper (one side or both, as the church usually does). Each sheet holds two pages side by side, not folded: the cover and page 1, then pages 2 and 3, and so on, with the announcements last. Check that the pages read 1, 2, 3 … in order, nothing is upside down, the page numbers are there, and no text is cut off at the edges or between the two pages.

### Printed bulletin PR 2a: bulletin settings

After the PR 2a merge the owner's guided check (one step at a time on the
phone) covers the items marked "(owner, after PR 2a)"; the results go into
`docs/ops-runbook.md` → "Printed bulletin PR 2a record". Record what the page
and the file show, never an email address, a phone number, a street address
or a church id.

- [ ] (owner, after PR 2a) **7.** As an owner or admin, open **4 Review & send**. The **Printed bulletin** card says "The church's details, the people who lead and the service time come from the bulletin settings." and, above the download buttons, lists "Not filled in: …" (before anything is saved: address, phone, email, website, Facebook name, service time, worship leader, liturgist, organist); under the downloads is a **Bulletin settings** button. Tap it: the **Bulletin settings** page opens.
- [ ] (owner, after PR 2a) **8.** Fill in the address (two lines), the phone, email, website and Facebook name, the service time and the three people, and tap **Save settings**: "Bulletin settings saved". Reload the page: everything is still there. Back on **Review & send** the "Not filled in" line is gone.
- [ ] (owner, after PR 2a) **9.** Tap **Download printed bulletin**: the cover shows the address lines, the phone, the email, the website and "FB: …"; page 1's header names the three people ("…, Worship Leader", "…, Liturgist", "…, Organist"), the date line ends with the service time, and each part shows its leader's name on the right, as in the sample. The prelude, the postlude and the announcements still show [placeholders] (the Bulletin step comes in PR 2b). Tap **Download Word version**: its cover and page 1 show the same details and names.
- [ ] (owner, after PR 2a) **10.** On **Bulletin settings**, under **Each part**, change who leads one part (for example the Sermon) and switch **Stands** for one part; change the stand note or the Gloria Patri words; save and download again: the bulletin follows each change.
- [ ] **11.** Clear the phone and save: the cover leaves the phone out (no empty line and no [placeholder]), and the card lists "Not filled in: phone."
- [ ] **12.** Signed in as a plain member of the same church: **Bulletin settings** shows "Only admins can edit the bulletin settings. You can read them below." and the settings as plain text (no fields, switches or **Save settings**), each part with who leads it and whether the congregation stands; the member's printed bulletin shows the same details.
- [ ] (owner, after PR 2a) **13.** At 375 px: no sideways scroll on **Bulletin settings**; every field, each part's leader and **Stands**, **Save settings** and **Back to Review & send** are easy to tap (44 px).
- [ ] **14.** After saving the settings, step 1's default translation and the Hymns step's hymnal are unchanged (saving keeps the church's other settings).
- [ ] **15.** On **Bulletin settings**, change a field without saving and tap **Back to Review & send**: "Discard unsaved changes?" asks first; **Keep editing** stays with the change, **Discard changes** goes back. Reloading the tab with a change unsaved shows the browser's own warning.

### Printed bulletin PR 2b: the Bulletin step

PR 2b ships as two PRs, backend first: **PR 2b-1** (migration
`0006_services_bulletin`; the server saves, opens, carries and prints the
week's fields; the builder itself does not change) and, once 2b-1 is live
and checked, **PR 2b-2** (the Bulletin step). From PR 2b-2 the builder has
five steps: **4 Bulletin** comes before **5 Review & send** (earlier items
say "4 Review & send"). Before the PR 2b-1 merge the owner runs the steps of
`backend/migrations/README.md` → "Before 0006_services_bulletin" (items 16
and 17); after each merge, the owner's guided check (one step at a time on
the phone) covers the items marked "(owner, after PR 2b-1)" or "(owner,
after PR 2b-2)". The results go into `docs/ops-runbook.md` → "Printed
bulletin PR 2b-1 record" and "Printed bulletin PR 2b-2 record". Use
invented announcements for the checks, or the church's real ones only on
the owner's own phone; record what the page and the files show, never a
name from the prayers and concerns, an email address, a phone number, a
street address or a church id.

- [ ] (owner, before the PR 2b-1 merge) **16.** A green `db-backup` run; the read-only counts (version `0005_services_extras`, saved services, churches); the SQL preview read: one `ADD COLUMN bulletin JSON` between `BEGIN;` and `COMMIT;`, under the 5 s lock timeout.
- [ ] (owner, after PR 2b-1) **17.** The after-deploy query shows `0006_services_bulletin`, `1` and `with_bulletin` `0`, and the counts are unchanged (or grew by the services saved since).
- [ ] (owner, after PR 2b-1) **18.** The builder works as before (four steps): open a saved service from **Services**, tap **Save changes**, and download the printed bulletin from **4 Review & send**: the save works, and the PDF still prints the music and the announcements as [placeholders], as the Printed bulletin card says.
- [ ] (owner, after PR 2b-2) **19.** The step bar shows five steps and fits at 375 px with no sideways scroll; **4 Bulletin** says "Optional". On **Bulletin**: **Music**, **Who leads**, **Announcements** and **Reading text**, every field and button easy to tap (44 px).
- [ ] (owner, after PR 2b-2) **20.** Fill in the prelude and postlude (title and composer), the ushers and counters, the coffee hour and one line of activities, leave the rest blank, and download the printed bulletin from **5 Review & send**: the prelude and postlude print with their composers and the organist's name; the announcements page shows only what was filled in (no heading or line for a blank one); the Printed bulletin card no longer says anything prints as [placeholders] and lists the blank ones ("Not filled in: …"). The Word version shows the same.
- [ ] (owner, after PR 2b-2) **21.** Under **Who leads**, change one person for this week ("Changed for this week.") and, behind **Change who leads a part**, the Sermon's leader (each part says "Usually" and the settings' name); download again: page 1's header and the Sermon follow the change; **Bulletin settings** still has the usual names.
- [ ] (owner, after PR 2b-2) **22.** Save the service. Start a **New service**, choose the Sunday one week after the saved service's date on step 1, and open **4 Bulletin**: the saved service's music and announcements are there, each with "From last week. Check before printing."; **Who leads** shows the usual names and the reading boxes are empty. On **5 Review & send** the card says "From last week, not checked yet: …". Change one box and tap **Keep as is** on another: their notes go, and the card's list shortens. Save it and open it again from **Services**: the boxes not yet checked still say "From last week".
- [ ] **23.** Paste one reading's text under **Reading text** and download: the PDF prints the pasted text under that reading, the credit line names only the other reading ("The First Reading is from the …", or the New Testament Reading), and the download fetches only the other reading. Paste both: no credit line. (A reading whose text could not be loaded prints "[Reading text unavailable]" and is not named in the credit line.)
- [ ] **24.** Clear every announcement and download: there is no announcements page in the PDF or the Word version (the card lists "announcements" as not filled in).
- [ ] **25.** Open a saved service from **Services**: its bulletin fields are as saved, only the boxes it was saved with unchecked say "From last week", nothing from another week comes in, and Review says "Saved".
- [ ] **26.** Open a saved service, change its date on step 1 to another Sunday and open **4 Bulletin** ("Save as new service"): its music and announcements each say "From last week. Check before printing.", **Who leads** shows the usual names, no part has a leader of its own and the reading boxes are empty. Change the date back: the names, part leaders and texts come back.
- [ ] **27.** A draft started before PR 2b-2 opens with everything it had, and its Bulletin step fills with last week's music and announcements once last week's service has them (a service saved before PR 2b-2 has none).

### Printed bulletin PR 3: the cover picture

PR 3 ships as two PRs, backend first, as PR 2b did: **PR 3a** (migration
`0007_bulletin_images`; the server takes, shows and prints a cover picture;
the builder itself does not change) and, once 3a is live and checked,
**PR 3b** (the picture on the Bulletin step). Before the PR 3a merge the
owner runs the steps of `backend/migrations/README.md` → "Before
0007_bulletin_images" (items 28 and 29); after each merge, the owner's
guided check (one step at a time on the phone) covers the items marked
"(owner, after PR 3a)" or "(owner, after PR 3b)", and the print test item
36. The results go into `docs/ops-runbook.md` → "Printed bulletin PR 3a
record" and "Printed bulletin PR 3b record". Use a picture with no one in
it for the checks (a building, flowers); record what the page and the files
show, never a picture, a name, an email address, a phone number, a street
address or a church id.

- [ ] (owner, before the PR 3a merge) **28.** A green `db-backup` run; the read-only counts (version `0006_services_bulletin`, saved services, those with bulletin fields, the database's size); the SQL preview read: one new table `bulletin_images`, its index, row-level security and no grant to Supabase's `anon` and `authenticated` roles, between `BEGIN;` and `COMMIT;`, under the 5 s lock timeout.
- [ ] (owner, after PR 3a) **29.** The after-deploy query shows `0007_bulletin_images`, `true`, `0` and `0` (`0006_services_bulletin` with two empty values: the deploy has not applied 0007 yet, run it again in a minute), and the counts are unchanged (or grew by the services saved since), the database about the same size.
- [ ] (owner, after PR 3a) **30.** The builder works as before: open a saved service from **Services**, tap **Save changes**, and download the printed bulletin from **5 Review & send**: the save works, and the PDF's cover still shows the "[Cover picture]" box (now centered under the church's name, as the Word version's already was) with the reading and the date in it.
- [ ] (agent, after PR 3a) **31.** `/openapi.json` in production lists `/bulletin-images` and `/bulletin-images/{image_id}`; signed out, `POST /bulletin-images` answers 401 for a 1-byte body and for a 9.5 MB one (Railway's proxy passes a phone-sized picture with its size), and 422 naming `image` for an 11 MB one (refused before it is read).
- [ ] (owner, after PR 3b) **32.** On **4 Bulletin**, **Cover picture** comes first. Tap **Choose a picture**: the phone offers its photos (and the camera). Choose a photo taken on the phone: it uploads ("Uploading…"), and the preview shows it upright, trimmed to the cover's shape, with a dark band across its bottom holding the reading and the date as they print (an iPhone photo shows that Safari sent it as a JPEG, PR 3 planning answer 5). Choose another picture and, while it says "Uploading…", go to **5 Review & send** and back: the new picture is there. Download the printed bulletin from **5 Review & send**: the picture fills the cover's box under the church's name, in color, with the reading and the date in white on a dark see-through band across its bottom. The Word version shows the same picture.
- [ ] (owner, after PR 3b) **33.** Tap **Remove** and download again: the cover has no box, and the reading and the date sit centered where the picture was; the Printed bulletin card lists "cover picture" under "Not filled in".
- [ ] (owner, after PR 3b) **34.** Choose a picture, save the service, start a **New service** for the Sunday after and open **4 Bulletin**: last week's picture is there with "From last week. Check before printing."; **Keep as is** keeps it and the note goes. Open a saved service and change its date ("Save as new service"): its picture is marked the same way.
- [ ] **35.** A file that is not a JPEG or PNG (a PDF, a HEIC picture from a computer) or is over 10 MB says so under the buttons ("Choose a JPEG or PNG picture." or "The picture is larger than 10 MB. Choose a smaller one.") and uploads nothing; the picture already chosen stays.
- [ ] (owner, after PR 3b) **36.** Print test (PR 3 planning answer 10): print side 1 of a bulletin with a picture on the church's color printer, on legal paper: the picture is in color, sharp, inside the margins, and the reading and the date on the band are easy to read.
- [ ] (agent, after PR 3b) **37.** In a test church: another church's picture id answers 404; the picture's preview is fetched once in a visit, and after a reload the browser asks again and gets 304 (`Cache-Control: private, no-cache` with the ETag); a draft from before PR 3b opens with everything it had and no picture.

## Slice 6a

Run on the production URL https://worship-service-builder.vercel.app, on an
iPhone with Safari at 375 px and on desktop Chrome. These are the 6a spec's
manual checks for 6a-1 (the Settings area and the Church page), as the
owner's planning answers of 2026-10-05 split 6a into three PRs; 6a-2
(Hymns) and 6a-3 (Liturgy prompts, Prayers, Rubric, Bulletin settings
moved in) add their own items here. After the 6a-1 merge the owner's guided
check (one step at a time on the phone) covers the items marked "(owner,
after 6a-1)"; the results go into `docs/ops-runbook.md` → "Slice 6a-1
record". Record what the page shows, never an email address or a church id.

- [ ] (owner, after 6a-1) **1.** The menu at the top has **Settings** after **Services**. Tap it: **Settings** opens on **Church** ("You're the owner of {church}."), with the sections **Church** and **Bulletin**; **Bulletin** opens the Bulletin settings page.
- [ ] (owner, after 6a-1) **2.** On **Church**, the church's name, time zone, default Bible translation, default hymnal (with one hymnal: "{code} (your only hymnal)") and default Benediction show as saved. Change the default Bible translation and tap **Save profile**: "Profile saved.". Open **Builder** step 1 of a service that has not chosen its own translation: the passages are in the new translation with no reload. Expected, not a bug (6a-1 owner question 11): a service whose translation was picked by hand as the one that was then the default follows the new default too, and so does a saved service when it is reopened. Change it back.
- [ ] (owner, after 6a-1) **3.** Change the default Benediction and save. Start a **New service** (if it asks to clear the current draft, tap **Cancel** and open the liturgy step of the current service instead, when you have not typed its Benediction yourself) and open the liturgy step: the Benediction card shows the new text, and its hint's **Settings.** opens **Settings** → **Church**. A Benediction card you typed yourself is unchanged. Put the Benediction back as it was (if it was the standard Halverson text, type **Halverson**: the word stands for the full text).
- [ ] (owner, after 6a-1) **4.** On **Church**, change the name without saving and tap **Builder** at the top: "Discard unsaved changes?" asks first; **Keep editing** stays with the change, **Discard changes** goes to the builder. At 375 px: no sideways scroll on **Settings**; the fields, the section links and **Save profile** are easy to tap.
- [ ] **5.** Rename the church and save: the church switcher shows the new name with no reload. Rename it back.
- [ ] **6.** The time zone list offers "Use this device's time zone (…)" when the device's zone differs from the church's; tapping it and saving stores it (`GET /church` answers it with `timezone_valid` true).
- [ ] **7.** Signed in as a plain member of the same church: **Settings** → **Church** shows "Only admins can edit the church profile." and the profile as plain text, with no fields and no **Save profile**; the Benediction hint's **Settings.** opens the same page.
- [ ] **8.** Saving the profile keeps the church's other settings: the Bulletin settings, the rubric and the liturgy prompts are as they were.

**6a-2 (Hymns).** After the 6a-2 merge the owner's guided check covers the
items marked "(owner, after 6a-2)", one step at a time on the phone; the
results go into `docs/ops-runbook.md` → "Slice 6a-2 record". Any test hymn is
deleted in the same step that adds it; a hymnal is added (and then removed)
only when the church does not have it already, and a hymnal the church uses
is never removed. Record counts and what the page shows, never a church id.

- [ ] (owner, after 6a-2) **9.** **Settings** lists **Church**, **Hymns**, **Bulletin**, **Contacts** and **Account**. Tap **Hymns**: **Hymnals** lists each of the church's hymnals with its hymn count and **Default** on the default one; **Hymn library** says how many hymns there are. Search for **23**: hymn 23 and titles containing "23" are listed. Clear the search; at the end of the list **Show more** loads more hymns.
- [ ] (owner, after 6a-2) **10.** **Add hymn**: title **Test hymn**, no number, **Add hymn**: "Hymn added.". Search for it, tap it, change the title to **Test hymn 2**, **Save changes**: "Hymn updated." and the dialog says "Changes also appear in saved services that use this hymn.". Open **Builder** → **Hymns**, tap the Opening hymn's picker and type **Test hymn**: "Test hymn 2" is offered with no reload (do not choose it). Back in **Settings** → **Hymns**, **Add hymn** with the title **test hymn 2** and no number: "{hymnal} already has test hymn 2." (the default hymnal's code) shows in the dialog and nothing is added; **Cancel**. Then open "Test hymn 2", **Delete hymn**, **Delete hymn** again in "Delete “Test hymn 2”?": "Hymn deleted." and it is gone.
- [ ] (owner, after 6a-2) **11.** Only when **Add a hymnal** shows **Add** beside PH1990 (the church does not have it): **Add**: "Added PH1990 (605 hymns).", the row turns to **Added**; **Done**; PH1990 is listed with 605 hymns, and the library has the chips **All**, **GG2013** and **PH1990**. Then **Remove…** on PH1990, **Remove PH1990**: "Removed PH1990." and only the church's own hymnals are left. If PH1990 shows **Added**, the church has it already: skip this item and remove nothing.
- [ ] (owner, after 6a-2) **12.** At 375 px: no sideways scroll on **Hymns**; the five section links, the hymn rows, **Add hymn** and the search box are easy to tap. In **Edit hymn** with the iPhone keyboard open, **Save changes** can be reached and the box being typed in is not covered.
- [ ] **13.** Signed in as a plain member of the same church: **Hymns** shows "Admins can add bundled hymnals." with no **Add a hymnal** or **Remove…**; **Edit hymn** has no **Delete hymn**, and the year and familiarity are read-only ("Only admins can change this."); adding and editing a test hymn works (an admin deletes it).
- [ ] **14.** In a test church: pick a test hymn in the builder, then delete it in **Settings** → **Hymns**: the builder's slot shows "Not in your hymnal. Choose a replacement." with no reload.
- [ ] **15.** As an admin, set a hymn's "Year the words were written" to a year after the rubric's preferred year: the builder's picker labels it as newer with no reload.

**6a-3a (Liturgy prompts, Rubric, Bulletin).** After the 6a-3a merge the
owner's guided check covers the items marked "(owner, after 6a-3a)", one step
at a time on the phone; the results go into `docs/ops-runbook.md` → "Slice
6a-3a record". A test change to a prompt or to the rubric is made only on a
card that does not say **Customized**, and is put back with **Reset to
default** and a save in the same step, so the church's prompts end as
generation reads them (a prompts save sends every customized card again,
cleaned as generation reads it) and its rubric as it began; **Reset all to
defaults** is never tapped on the church's own page. Record what the page shows, never a church id or a prompt's wording.

- [ ] (owner, after 6a-3a) **16.** **Settings** lists **Church**, **Hymns**, **Liturgy**, **Rubric**, **Bulletin**, **Contacts** and **Account**. **Liturgy** shows "Liturgy prompts" with nine cards, "Overall voice (system prompt)" first and "Section prompts" with the placeholder help above the other eight; note which cards say **Customized**. **Rubric** shows "Service rubric" with **Hymn preferences**, three **Hymns** cards and eight **Prayers** cards; note which say **Customized** and the year in "Prefer hymns written before".
- [ ] (owner, after 6a-3a) **17.** On **Liturgy**, open a card that does not say **Customized** and type **{** at the end of its text; **Save prompts**: the card shows "{Card} prompt: It has a { or } without a partner. Use {{ or }} to print a brace." and nothing is saved (if the message names a different card instead, delete the **{**, note that card's name and stop this item there: that card's saved wording fails today's check and is left as it is for the owner to decide). Replace the **{** with the word **Amen.**; **Save prompts**: "Prompts saved." and the card says **Customized**. Then **Reset to default** on that card and **Save prompts**: "Prompts saved." and **Customized** is gone.
- [ ] (owner, after 6a-3a) **18.** On **Rubric**, open a **Prayers** card that does not say **Customized**, tap at the end of its last point and press return: a new empty point appears below; type **Test point**; **Save rubric**: "Rubric saved." and the card says **Customized**. Then **Reset to default** on that card and **Save rubric**: "Rubric saved." and **Customized** is gone. In "Prefer hymns written before" type **1400**: "The preferred year must be between 1500 and {this year}." shows and **Save rubric** cannot be tapped; type the year it showed before, and the message goes.
- [ ] (owner, after 6a-3a) **19.** **Settings** → **Bulletin** shows the bulletin settings as before, with **Back to the builder**. In **Builder** → **Bulletin**, **Bulletin settings** opens **Settings** → **Bulletin**; **Back to the builder** returns to the Bulletin step. On **Review & send** the Printed bulletin card's **Bulletin settings** opens the same page.
- [ ] (owner, after 6a-3a) **20.** At 375 px: no sideways scroll on **Liturgy**, **Rubric** or **Bulletin**; the seven section links, the cards and the buttons are easy to tap. On **Liturgy** with a card open and the iPhone keyboard up, the box being typed in is not covered and **Save prompts** can be reached by scrolling down.
- [ ] **21.** Signed in as a plain member of the same church: **Liturgy** shows "Only admins can edit the prompts. You can read them below." with read-only cards and no buttons; **Rubric** shows "Only admins can edit the rubric. You can read it below." with the points as text and no buttons; **Bulletin** shows its summary.
- [ ] **22.** In a test church, as an admin: save a Benediction prompt and generate the Benediction in the builder: the text follows it; set "Prefer hymns written before" to 1900: the builder's picker labels hymns written in or after 1900 as newer with no reload; then **Reset all to defaults** on both pages.
- [ ] **23.** Signed in, open the old address `/bulletin-settings` on the production URL: it opens **Settings** → **Bulletin**.

**6a-3b (Prayers).** After the 6a-3b merge the owner's guided check covers
the items marked "(owner, after 6a-3b)", one step at a time on the phone; the
results go into `docs/ops-runbook.md` → "Slice 6a-3b record". The prayers are
the pastor's own words: a prayer is added to keep only when the owner says
so; a test prayer ("Test prayer. Amen.", type Other) is removed, and the
library saved again, in the same step that adds it; a draft voice profile
replaces the church's profile only when the owner taps **Use this draft** and
**Save** because they want to keep it. Record counts and what the page shows,
never a prayer's or the profile's wording, a church id or an email address.

- [ ] (owner, after 6a-3b) **24.** **Settings** lists **Church**, **Hymns**, **Liturgy**, **Prayers**, **Rubric**, **Bulletin**, **Contacts** and **Account**. **Prayers** shows "Prayer library", the **Voice profile** box with **Update from my prayers**, and under **Prayers** either the church's prayers (each with its type, its first line, **Edit** and **Remove**) or "No prayers yet. Paste in a few of your own prayers so the writer can learn your voice."; note how many prayers there are and whether the profile box has text.
- [ ] (owner, after 6a-3b) **25.** **Add a prayer**, choose a type and paste a prayer (one of the owner's own to keep, or the test prayer **Test prayer. Amen.** as **Other**); **Save**: "Prayer library saved.", and the new row shows its first line. A test prayer: **Remove**, "Remove this prayer?", **Remove prayer**, **Save**: "Prayer library saved." and the list is as it was.
- [ ] (owner, after 6a-3b) **26.** With at least one prayer saved: **Add a prayer** (unsaved): **Update from my prayers** greys out with "Save your prayers first."; remove that empty row (it asks first) and the button comes back. **Update from my prayers**: "Drafting…" (and "Still working. This can take up to a minute." after 8 s), then "Draft from your prayers" beside the profile (below it on a phone) with **Use this draft** and **Keep mine**. **Keep mine** leaves the profile as it was; only if the owner wants the draft: **Use this draft**, edit it if wished, **Save**.
- [ ] (owner, after 6a-3b) **27.** At 375 px: no sideways scroll on **Prayers**; the eight section links, a row's type, **Edit** and **Remove**, and the buttons are easy to tap. With a prayer open and the iPhone keyboard up, the box being typed in is not covered and **Save** can be reached by scrolling down.
- [ ] **28.** Signed in as a plain member of the same church: **Prayers** shows "Only admins can edit the prayer library. You can read it below.", the profile and every prayer in full as text, and no buttons.
- [ ] **29.** In a test church, as an admin: save three prayers of mixed types (one a Prayer of Confession) and a voice profile, then generate the Prayer of Confession in the builder with no reload: it follows the profile and does not repeat the saved prayer's lines (6a spec, manual check 12).
- [ ] **30.** In the same test church: with prayers unsaved, tap **Builder**: "Discard unsaved changes?" asks first. Then empty the library (remove every prayer, clear the profile, **Save**).

## Slice 5b

Run on the production URL https://worship-service-builder.vercel.app, on an
iPhone with Safari at 375 px and on desktop Chrome. These are the checks for
5b-1 (the Contacts page in Settings), as the owner's 5b planning answers of
2026-10-06 split 5b into two PRs; 5b-2 (the Gmail connection and emailing the
bulletin) adds its own items here. After the 5b-1 merge the owner's guided
check (one step at a time on the phone) covers the items marked "(owner,
after 5b-1)"; the results go into `docs/ops-runbook.md` → "Slice 5b-1
record". Record what the page shows (how many contacts, how many flagged),
never an email address, a person's name or a church id.

- [ ] (owner, after 5b-1) **1.** **Settings** lists **Church**, **Bulletin** and **Contacts**. Tap **Contacts**: the church's saved contacts are listed (a name in bold with its address under it, an address alone when there is no name). Under any address the app could not email, "This address doesn't look valid. Edit it." shows. Note how many contacts there are, how many are flagged, and whether any address is listed twice (even with different capital letters or spaces).
- [ ] (owner, after 5b-1) **2.** Fix each flagged contact with its pencil button (**Edit contact**, **Save changes**): the note goes away. If the box holds more than one address, keep one here, then add each other one with **Add a contact**. Delete one of any address listed twice. Then, every time: add a contact named "Test" with the address test@example.com, rename it "Test 2", try adding TEST@example.com again ("That email is already in your contacts."), then delete it with its bin button ("Delete Test 2?", **Delete contact**).
- [ ] (owner, after 5b-1) **3.** Type a name in the add form without adding it and tap **Church** in the Settings sections: "Discard unsaved changes?" asks first. At 375 px: no sideways scroll; the section links, the pencil and bin buttons and **Add contact** are easy to tap. In **Edit contact** with the iPhone keyboard open, **Save changes** can be reached and the box being typed in is not covered.
- [ ] **4.** Signed in as a plain member of the same church: **Settings** → **Contacts** shows "Only admins can add or change contacts." and the list with no buttons and no add form.
- [ ] **5.** Two tabs as an admin: delete a contact in one, then edit it in the other: "Contact not found." and the row goes away.
- [ ] **6.** Add a contact as `Someone@Example.ORG`: it is saved and listed as `Someone@example.org` (the domain lower-cased, the rest as typed).

**5b-2 (the Gmail connection and emailing the bulletin).** The owner's Google
and Railway setup comes before the merge (item 7). After the merge the
owner's guided check covers the items marked "(owner, after 5b-2)", one step
at a time on the phone; the results go into `docs/ops-runbook.md` → "Slice
5b-2 record". Every test email goes only to the owner's own addresses. Record
what the page shows, never an email address, a token, a code from the
address bar or a church id.

- [ ] (owner, before the 5b-2 merge) **7.** Google Cloud Console → the OAuth client "Liturgy" lists `https://worship-service-builder.vercel.app/gmail/callback` and `http://localhost:3000/gmail/callback` under Authorized redirect URIs, and the consent screen's publishing status is noted (Testing or In production). Railway → the API service → Variables has `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` (Streamlit's) and `GOOGLE_OAUTH_REDIRECT_URI` = `https://worship-service-builder.vercel.app/gmail/callback`; after the deploy the log has the line `Gmail: configured` and no other line starting `Gmail:`.
- [ ] (owner, after 5b-2) **8.** **Settings** lists **Church**, **Bulletin**, **Contacts** and **Account**. **Account** shows your name, your email, "Signed in with Google.", **Log out** and the **Gmail** card. If it says "Connected as …", tap **Disconnect** first ("Connect Gmail" shows). Tap **Connect Gmail**: Google opens in the same tab with your account chosen; allow sending; you are back on **Account** with "Gmail connected" and "Connected as" your address. At 375 px the four section links are easy to tap and nothing scrolls sideways.
- [ ] **9.** On **Account**, **Connect Gmail** and then Cancel at Google: "Gmail connection was cancelled." and back on **Account**.
- [ ] **10.** After a successful connect, reload `/gmail/callback`: "Gmail connection didn't finish. Try connecting again."; **Account** still says "Connected as …".
- [ ] (owner, after 5b-2) **11.** **Review & send** → **Email the bulletin** says "Sends from" your address. Tap **Email bulletin…**: the subject reads "Worship service for" the service date with no leading zero, and **Bulletin copy (Word)** is ticked; tick **Printed bulletin (PDF)** too. Type your own address under **Other addresses** (only yours) and tap **Send to 1 person**: "Email sent to 1 person." The email has you in To, the message and both files, and both open on the phone. If you have a second address of your own, send again to both: each copy shows only the sender in To, and Gmail's Sent copy shows both in Bcc.
- [ ] (owner, after 5b-2) **12.** Open **Email bulletin…** again: **Printed bulletin (PDF)** is still ticked (remembered on this phone). With the keyboard open in **Message**, **Send** can still be reached and the box is not covered. At 375 px nothing in the dialog scrolls sideways. Close it with **Cancel**.
- [ ] (owner, after 5b-2) **13.** **Settings** → **Account** → **Disconnect**. On **Review & send** the card says "Connect your Gmail to email the bulletin from your own account."; tap its **Connect Gmail**: after Google you come back to **Review & send** and the email dialog opens by itself. **Cancel**; **Account** says "Connected as" your address.
- [ ] **14.** Double-tap **Send to 1 person**: one email arrives.
- [ ] **15.** A contact flagged on the Contacts page shows in the dialog with "This address doesn't look valid. An admin can fix it in Settings → Contacts." and cannot be ticked.
- [ ] **16.** Switch church with the dialog open: it closes; opening it again lists the other church's contacts.

## Slice 6b

Slice 6b moves People (members and invites) and the Danger zone (transfer
ownership, leave, delete the church) into Settings, in two PRs (owner's 6b
planning answers of 2026-10-09). **6b-1** is the server side only:
`GET /members`, `PATCH` and `DELETE /members/{user_id}`, `GET`, `POST` and
`DELETE /invites`, `POST /church/transfer-ownership`, `POST /church/leave`
and `DELETE /church`, and migration `0008_invites_integrity`. No page uses
them until 6b-2, so the app looks and works as before. The owner's steps
around the 6b-1 merge follow `backend/migrations/README.md` → "Before
0008_invites_integrity", one step at a time; the results go into
`docs/ops-runbook.md` → "Slice 6b-1 record". Record counts and what the
screens show, never an email address, an invite code or link, a church id
or a database URL. 6b-2 (the People and Danger zone pages) adds its items
here.

- [ ] (owner, before the 6b-1 merge) **1.** A fresh backup: the db-backup workflow on `main` finishes green with an artifact `db-backup`.
- [ ] (owner, before the 6b-1 merge) **2.** "Before 0008_invites_integrity" step 2's read-only query in Supabase's SQL Editor shows `version` `0007_bulletin_images`, `duplicate_pending_pairs` `0` and `old_constraint` `1`; the other counts are recorded (`churches_without_one_owner` and `churches_without_admin` are normally `0`).
- [ ] (owner, before the 6b-1 merge) **3.** The SQL preview the agent renders from the PR's code matches step 3 of that section, and the owner has read it.
- [ ] (owner, after 6b-1) **4.** Step 4's read-only query shows `0008_invites_integrity`, `1`, `1`, `0`; step 2's query again shows the same counts (or more invites), with `other_role_invites` `0` and `old_constraint` `0`.
- [ ] (owner, after 6b-1) **5.** On the phone, the app loads as before (pull down to reload): the builder opens and **Settings** lists the same sections as before 6b-1 (no People or Danger zone yet). If you still have an invite link (`…/join?code=…`) to your church that nobody has used yet, open it on the phone while signed in: it says "You're already a member of {church}." with **Open {church}**, which opens the church and changes nothing (the link stays unused); without such a link, that half is skipped.
- [ ] (agent, after 6b-1) **6.** `/health/ready` answers `{"ok":true,"db":"ok"}`; `/openapi.json` lists `/members`, `/members/{user_id}`, `/invites`, `/invites/{invite_id}`, `/church/transfer-ownership` and `/church/leave`, and `/church` with `delete`; each of the new routes answers 401 when called signed out.

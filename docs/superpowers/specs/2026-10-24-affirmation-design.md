# Affirmation of Faith: design

Status: design for the owner's decisions 1, 2 and 6 of 2026-10-24 (`2026-10-24-affirmation-and-formatting-decisions.md`, binding), with the owner's answers A to D of the same day ("Owner answers" below). Plan: `docs/superpowers/plans/2026-10-24-affirmation.md`. It ships as two PRs (answer A): Affirmation PR A, the server side and migration `0010_services_affirmation`, merged and confirmed live first; then Affirmation PR B, the pages. Formatting (decisions 3 to 5) is the next PR; nothing here builds it, and every text stays plain text that the formatting PR can later read as markdown.

## What changes

Today the Affirmation of Faith is a fixed landmark in `OUTLINE` (`backend/liturgy_config.py`, `fixed_text` "Apostles' Creed"). It cannot be left out or changed:

- The Word files (`worship_service.build_docx`, both copies) print the heading "Affirmation of Faith" and the line "Apostles' Creed" (the name only, no creed text).
- The printed bulletin (`printed_bulletin.order_of_worship`, rendered by `printed_pdf` and `printed_docx`) prints `*AFFIRMATION OF FAITH:  “The Apostles’ Creed”` (starred by default) and the full creed in bold, one paragraph (`APOSTLES_CREED`, the traditional wording, "Holy Ghost ... quick and the dead").
- The emailed bulletin (`bulletin_email`) is a plain message with the Word file and/or the printed PDF attached; it prints whatever those files print. The message itself never names the creed.

After this change the Affirmation is a card in the Liturgy step, like the communion card, with a switch, a choice and an own-text box; the church's default lives on Settings → Liturgy.

## UX

### The Affirmation card (Liturgy step)

It takes the Affirmation landmark's place in the order of worship (after the Sermon Title, before the Second Hymn). From the top:

1. A switch, **Include Affirmation of Faith** (on by default). Off: the card's other controls go and the helper says "Not printed or emailed." Nothing of it prints (see "What prints"); custom elements placed "After Affirmation of Faith" still print in their place, as every custom element does when its item is absent.
2. A choice of three (a radio group, one per line at 375 px, 44 px rows): **Apostles' Creed**, **Nicene Creed**, **Your own text**.
3. For a creed: "Show creed text", a collapsible with the creed exactly as the printed bulletin prints it (the Nicene Creed line by line, a line too long for the screen continuing indented under itself; and its credit line under it), as the communion card shows its text.
4. For Your own text: a text box like a prayer card's (autosizing, the section limit of 20 000 characters, the label "Your own text" for screen readers), with the hint "Printed in bold for everyone to read together." While it is blank the hint adds "Nothing prints until you type it." No AI, no Undo, no Clear button: it is typed or pasted.
5. A helper line like the communion card's: "Your church's default." while it follows the default; "You changed this." or "Set from the saved service." otherwise, each with **Use church default**, which puts the church's default back (focus moves to the switch, as communion's "Use default").

Any change to the switch, the choice or the text makes the card the member's own (it no longer follows the default). The text typed for Your own text is kept in the draft while another choice is picked, so switching back finds it; it is saved only when Your own text is the choice.

### Settings → Liturgy: the church default

A card **Affirmation of Faith** above "Liturgy prompts" on `/settings/liturgy`, saved on its own:

- The same three choices and, for Your own text, a text box ("Paste your church's own text, for example A Brief Statement of Faith." as its hint). The creeds show their text behind "Show creed text".
- Owners and admins change it and press **Save default** (disabled until something changed; the leave guard asks before leaving unsaved; newer server data rebases the form as on the other settings pages). Your own text with a blank box cannot be saved: "Type your church's own text, or choose a creed."
- Members see it read-only, with "Only admins can change the default. You can read it below.", and no Save button. The server refuses a member's change (403, `PATCH /church` is admins only) and writes nothing.
- A church that never set it has the Apostles' Creed as its default (today's behavior). The default is always "included": a church that never says a creed switches it off per service (owner answer D: no "leave it out" default now).

### Review step and summary

The builder's summary (the Liturgy block) gains one line: "Affirmation of Faith: Apostles' Creed", "... Nicene Creed", "... Your own text", "... Your own text (nothing typed yet)" or "Affirmation of Faith: Off". "Review service" and "Hear it from the pews" are unchanged (see "AI interplay").

## What prints

"Prints" means the Word files (bulletin and pastor's copies, `POST /documents`), the printed bulletin as PDF and as Word (`POST /documents/printed`) and therefore the email's attachments (`POST /bulletin-emails`). The email's message text never mentions the Affirmation.

| The card | Word files | Printed bulletin (PDF and Word) |
|---|---|---|
| Off (any choice) | nothing (no heading, no line, no blank paragraph) | nothing; it no longer counts as a starred element for the stand note |
| Apostles' Creed | exactly as today: "Affirmation of Faith" (Heading 2), "Apostles' Creed", a blank paragraph | exactly as today: `*AFFIRMATION OF FAITH:  “The Apostles’ Creed”` and the traditional text in bold, one paragraph |
| Nicene Creed | "Affirmation of Faith", "Nicene Creed", a blank paragraph | `*AFFIRMATION OF FAITH:  “The Nicene Creed”`, the ELLC text in bold in its sense lines (one paragraph per ELLC line, as ELLC asks, each with the hanging indent the People and Leader lines use, so a line that wraps continues indented under itself), then its credit line in the italic credit style the scripture credit uses |
| Your own text, typed | "Affirmation of Faith", the text as typed (line breaks kept), a blank paragraph | `*AFFIRMATION OF FAITH:` and the text as typed, in bold (line breaks kept) |
| Your own text, blank | nothing, as Off | nothing, as Off |

The star and the leader's name on the right follow the bulletin settings as today (`affirmation_of_faith` stays an element key). Own text goes through the same Word-safe cleaning as every text (`archive._xml_safe`, then trimmed).

## Data shape

One shape everywhere, `{"include": bool, "choice": "apostles" | "nicene" | "own", "text": str}`; `text` is "" unless the choice is "own". A pure module `backend/affirmation.py` holds the two creeds, the credit line, the labels, `Affirmation` (default: included, Apostles' Creed, no text), `read` (tolerant: anything not understood reads as the default, so nothing ever fails for a stored value) and `resolve_default`.

- **Draft (frontend, localStorage):** version 5 adds `liturgy.affirmation = {include, choice, text, origin}`, `origin` "default" (follows the church default), "user" or "archive". The 4 → 5 migration gives the Apostles' Creed, included: origin "archive" for a draft that is a saved service (it prints as saved) and "default" for an unsaved one (it follows the church default, which is the Apostles' Creed until an admin changes it). A fresh draft takes the church's default.
- **The request body** (`ServiceDraft`, used by `POST /documents`, `/documents/printed`, `/bulletin-emails` and `POST`/`PUT /services`): an optional `affirmation`. PR B's pages always send it; today's pages never do. Left out (a page from before PR B): the documents print the Apostles' Creed (today), a `POST /services` stores none, and a `PUT /services/{id}` keeps what is saved (the bulletin's rule). `ServiceDraft` refuses unknown fields, so the API from before PR A would refuse PR B's bodies (422): PR B is merged only after PR A is live.
- **The fingerprint payload** ("Unsaved changes"): `affirmation` is left out when it is included Apostles' Creed, so a draft saved before this change keeps its fingerprint and stays "Saved".
- **Saved services:** a new nullable JSON column `services.affirmation`. NULL (every service saved before this change, and a POST without it) reads as included Apostles' Creed, so old services open and print exactly as today. `GET /services/{id}` (and the POST and PUT answers) always carry `affirmation`. Opening a saved service puts it on the card with origin "archive"; a save makes a "default" card "archive" (as the Benediction and communion).
- **The church default:** `churches.settings["default_affirmation"] = {"choice", "text"}` (no column). `GET /church` returns `default_affirmation: {choice, text}` (Apostles' Creed and "" when unset or not understood); `PATCH /church` takes `default_affirmation` from owners and admins (422 for an unknown choice or for "own" with a blank text; the text is cleaned like the Benediction's).

### Why a migration

Preferred was none, but a saved service needs somewhere to keep its choice, and every place without a migration is worse: `services.liturgy` holds only the eight sections and every reader filters to them (0006's docstring chose a new column for the same reason), and the frozen Streamlit app reads `services.liturgy` and expects only text in it; `services.bulletin` and `services.custom_elements` mean other things and have their own NULL rules. So **`0010_services_affirmation`**: one nullable JSON column, no default, no backfill, expand-only (the frozen app never reads it), the same shape and pre-merge routine as `0006_services_bulletin` (backup, counts, read the SQL, after-deploy check: `backend/migrations/README.md`). The church default needs no migration.

## API changes

- `GET /liturgy/config`: a new `affirmation` object: `title` "Affirmation of Faith", `toggle_label` "Include Affirmation of Faith", and `choices` (key, label, text, credit; the own choice's text and credit are ""). The outline does not change: its Affirmation item stays `kind: "landmark"`, `value_source` "fixed", `fixed_text` "Apostles' Creed", because today's Liturgy step renders nothing for a kind it does not know, so a new kind would drop the row from today's pages. PR B's Liturgy step shows the card in that item's place when the config carries `affirmation`, and today's row when it does not (an API from before PR A); Settings → Liturgy likewise leaves the default card out.
- `ServiceDraft.affirmation` (optional), `ServiceOut.affirmation` (always), schema `ServiceAffirmation`.
- `GET /church` → `default_affirmation`; `PATCH /church` ← `default_affirmation`, schema `ChurchAffirmation`.
- `frontend/src/lib/api/openapi.json` and `schema.d.ts` regenerated the repo's way (`.venv/bin/python backend/scripts/export_openapi.py`, then `npm run gen:api`), both in PR A (CI fails on drift); the frontend test fixtures gain the new required fields there too. No page changes in PR A, and today's frontend tests pass unchanged against its types.
- Telling the new API from the old after a deploy: the public `/openapi.json` names `ServiceAffirmation` only on the new one (`/health/ready` answers the same for both).

## AI interplay

Neither the creed nor the church's own text goes into "Review service" or "Hear it from the pews", and neither goes into liturgy generation. They are fixed texts the church chose (the creeds) or pasted (a confession of faith), not prayers to improve; the reviewer's and the pews' prompts stay as they are, and nothing here changes what the AI is sent. Own text is never logged (it is service text, F §2.5): the log lines stay ids, sizes and durations.

## Copyright findings

- **ELLC texts (Apostles' and Nicene Creeds, from *Praying Together*).** ELLC's permissions page and its "Guidelines for Reproducing ELLC Texts" (July 2017) say: "The liturgical texts in Praying Together may be used freely and without the need for prior permission. The liturgical text(s) should be properly acknowledged." The notice to use: "English translations of (text), © 1998, English Language Liturgical Consultation (ELLC), and used by permission. www.englishtexts.org"; a modified text adds "(adapted)". ELLC also asks that the texts be printed in their sense lines, and that denominations and publishers using them in service books tell the Secretary (helpful, not required). The notes on each text need permission; this change uses none of them. Sources: https://www.englishtexts.org/permissions, https://irp-cdn.multiscreensite.com/a42fbdb2/files/uploaded/Guidelines.pdf (linked from that page), https://www.englishtexts.org/the-nicene-creed, https://www.englishtexts.org/the-apostles-creed (all read 2026-10-24).
  - The notice says © 1998, while *Praying Together* is usually dated 1988 (for example https://en.wikipedia.org/wiki/English_Language_Liturgical_Consultation). The app prints ELLC's own wording, © 1998, as ELLC gives it.
  - The Nicene Creed's "[and the Son]": ELLC's note on line 26 says the brackets are not to be printed and each church decides whether to include the words. The PC(USA) tradition says them; the app prints "who proceeds from the Father and the Son," without brackets, which is one of ELLC's two intended forms, not an adaptation (owner answer C).
  - **Unverified:** that the PC(USA) *Book of Common Worship* (2018) prints exactly the ELLC wording; the search did not reach its text. Nothing here depends on it.
- **The Apostles' Creed the app prints today** is the traditional wording ("Holy Ghost", "quick and the dead"), the 1662 *Book of Common Prayer* text with modern punctuation. That text is public domain in the United States; in the United Kingdom the Book of Common Prayer is still under Crown rights (letters patent). Source: https://librivox.org/the-book-of-common-prayer-1662-selections (summary level; not a legal opinion). It prints with no credit line, as today.
- **Choice made here:** the Apostles' Creed keeps today's traditional wording (so old services print exactly as today and no credit is needed; owner answer B); the Nicene Creed uses the ELLC text with ELLC's credit line on the printed bulletin and in the app wherever its text shows. The Word files print only the creed's name, so they carry no credit. The ELLC Apostles' Creed is not offered (answer B). The texts in `backend/affirmation.py` were copied from ELLC's own page on 2026-10-24 and a test pins them.

## Backward compatibility

- A saved service (NULL `affirmation`) opens with the Apostles' Creed, included, and prints byte for byte as today in every format (tests compare against today's output).
- A draft in a browser upgrades to version 5 with the Apostles' Creed, included; a saved one stays "Saved".
- A body without `affirmation` prints as today; a PUT without it keeps the saved choice.
- Between the two PRs (PR A live, PR B not yet): today's pages work exactly as now. They never send `affirmation`, they read only the fields they know, and the outline they draw is unchanged.
- `test_build_docx_characterization.py` keeps pinning today's Word file for the default.

## Out of scope

Formatting (the next PR; the own text is stored as typed, so the formatting PR can read it as markdown later); more built-in texts (A Brief Statement of Faith and others are pasted as own text, decision 2); a "We believe" variant or a contemporary Apostles' Creed; per-church editing of a creed's wording; AI for the Affirmation; printing the creed's text in the Word files (they print names, as today); telling ELLC (optional, the owner's call).

## Risks

- **A migration** (small, expand-only, the 0006 pattern), in PR A: the owner runs the README routine before the merge; a failed `alembic upgrade head` leaves the previous release serving.
- **A stale page** (open from before PR B) sends no `affirmation`: its downloads print the Apostles' Creed and its PUT keeps the saved choice, so it never erases a Nicene choice; its outline keeps today's row until reloaded.
- **PR B ahead of PR A** would fail every download and save (the old API refuses the unknown field): the PRs merge in order, and PR B's pre-merge check reads the live `/openapi.json`.
- **Wording errors in a creed** print in every bulletin: a test pins both texts against the copies taken from ELLC and the current file.
- **The printed bulletin grows** by the Nicene Creed's 32 lines when chosen; the booklet already flows over pages.

## Owner answers (2026-10-24)

The owner answered "all recommended" (binding; recorded in the decisions doc):

- **A. Two PRs.** Affirmation PR A is the server side and migration `0010_services_affirmation`, merged and confirmed live first; Affirmation PR B is the pages. Each has its own verification, pre-merge note, PR body, CI counts, merge, after-deploy check, phone check and runbook record; PR A's phone check is minimal (the app still saves and downloads as before), PR B's covers the card. PR A is safe with today's frontend (see "API changes" and "Backward compatibility"); PR B is guarded if it ever runs ahead.
- **B. The Apostles' Creed** keeps today's traditional (1662 Book of Common Prayer) wording.
- **C. The Nicene Creed** says "and the Son", without brackets.
- **D. No "leave it out" church default** now.

The questions as asked, for the record: which wording of the Apostles' Creed (traditional, recommended; or ELLC's contemporary text); the Nicene Creed's "and the Son" (include, recommended; or leave out); the migration (yes, recommended, `0010_services_affirmation` with the 0006 routine; the no-migration alternative hid the choice in `services.liturgy`, which the frozen Streamlit app reads); and a "leave it out" church default (not now, recommended). Answer A answers the plan review's first finding, which recommended two PRs.

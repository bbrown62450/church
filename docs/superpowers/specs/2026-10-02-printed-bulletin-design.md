# Printed Bulletin: Design

Date: 2026-10-02
Status: owner answers of 2026-10-02 ("all recommended") are binding; PR 1 has its plan
(`docs/superpowers/plans/2026-10-02-printed-bulletin-1.md`); PR 2 and PR 3 get their own plans.
Builds on:
- `2026-10-02-printed-bulletin-idea.md` (the idea note)
- `2026-09-25-slice-5a-documents-archive-design.md` (5a: `POST /documents`, `ServiceDraft`, the archive)
- `2026-09-25-migration-foundations-design.md` (F)
- `2026-09-25-slice-6a-settings-church-design.md` (6a, where the bulletin settings fold in later)

## Why

The app makes the pastor's Word working files, but the church still builds the real Sunday
bulletin by hand. The owner's sample (First Presbyterian Church's bulletin for September 27, 2026,
shared in the session and not committed) shows what it holds: a folded booklet on legal paper with a
cover, the order of worship with the leaders' names, the readings in full, the sung responses, and an
announcements page. Most of the order of worship is already in the draft. This design makes the
app print the booklet, first from what it knows (PR 1), then with the weekly and standing details
(PR 2) and the cover picture (PR 3).

## Owner answers (Beau, 2026-10-02, "all recommended"; binding)

| # | Answer |
|---|---|
| 1 | **Output:** a print-ready PDF in the folded legal-landscape booklet layout, plus an editable Word version. |
| 2 | **Standing church settings:** church name, address, phone, email, website, Facebook name; the standing worship leader, liturgist and organist; the "*Congregation stands if able" note and which elements get the star; the Gloria Patri words. **Weekly:** prelude and postlude (title, composer), a per-element leader when different, announcements. |
| 3 | **Announcements:** a simple form for ushers, deacon of the week and coffee hour, plus free-text boxes for activities, prayer concerns and collection items; each carries forward from last week. |
| 4 | **Cover picture:** uploaded each week, with the option to keep last week's; printed under the church name with the scripture reference and date over it. |
| 5 | **Scripture:** full text in the translation chosen on step 1, with a credit line; a way to paste your own text for a licensed translation the app can't fetch. |
| 6 | **One version** (no separate mailing version) for now. |
| 7 | **Keep the pastor's and bulletin Word copies;** add a third download, "Download printed bulletin". |
| 8 | **Weekly fields on a new "Bulletin" step** between Liturgy and Review; standing church details in a small **Bulletin settings** panel now, folded into 6a later. |
| 9 | **Three PRs:** (1) the booklet PDF (and Word) from what the app already knows, placeholders for the rest; (2) the weekly fields and announcements (and the standing settings panel); (3) the cover picture upload. |
| 10 | **Checks:** a guided phone check after each PR, and a print test on legal paper at the church after PR 1 (folds and margins). |

## The sample, read closely

The sample PDF is three legal-landscape pages (1008 x 612 pt), each holding two 7 x 8.5 in pages
side by side in **reading order**: cover | 1, 2 | 3, 4 | 5. That is a viewing layout (it was the
mailing copy); it does not fold into a booklet. Six booklet pages are a sheet and a half; a folded
booklet needs a multiple of 4. So the app's PDF is **imposed** for printing (below), and the print
test (answer 10) confirms the fold, the page order and the margins on the church's printer.

What the sample prints, in order: the cover (church name; picture with the sermon reference and the
date over it; address, phone, email, website, "FB: ..."); "THE SERVICE FOR THE LORD'S DAY" with the
church, the worship leader, liturgist and organist, and the date (left) and time (right); four
italic centered section headings (GATHERING FOR WORSHIP, RECEIVING THE WORD, RESPONDING TO THE
WORD, SENDING OUT TO SERVE); each element in bold capitals with its leader right-aligned; Leader
and People lines (People bold); "*HYMN: #409 "God Is Here!""; the Gloria Patri with its words; the
readings in full; the Apostles' Creed in full; Prayers of the People as a heading only; the
Offering and the Doxology; the Benediction in quotes with "- Richard Halverson"; the postlude with
its composer; "*Congregation stands if able"; page numbers from the first inside page; and an
announcements page last.

## Decisions

### Layout and page order
- **Page:** a booklet page is half a legal sheet, 7 x 8.5 in (504 x 612 pt), margins 0.5 in, the
  page number centered 20 pt from the bottom. Body Times 11 pt on 13 pt leading; the church name on
  the cover 28 pt bold; contact lines Helvetica 12 pt (the sample uses a sans face there).
- **Pages in reading order:** the cover (unnumbered), the inside pages numbered from 1, the
  announcements page last (the back cover).
- **Imposition:** the page count rounds up to a multiple of 4 with blank pages placed just before
  the announcements page, so announcements stay on the back. Sheet k (0-based) of a booklet of N
  pages prints (N-1-2k | 2k) on its front and (2k+1 | N-2-2k) on its back. Print on both sides,
  flipped on the short edge, and fold. With the sample's content that is 8 pages on 2 sheets.
- **One version** (answer 6): the PDF is the imposed booklet. Read on a phone it is in sheet order;
  the Word version is in reading order.
- **Word version:** the same pages in reading order on 7 x 8.5 in pages (Times New Roman 11 pt,
  0.5 in margins, leaders at a right tab stop, page numbers from the first inside page). It does not
  set Word's Book fold (its effect on page size differs between Word and other editors); to print it
  as a booklet, use Word's Book fold or the printer's booklet setting. The PDF is the print copy.

### PDF library
| Option | License | Install on Railway | Fit |
|---|---|---|---|
| **reportlab 5** + **pypdf 6** (chosen) | BSD; BSD-3-Clause | pure-Python wheels (`py3-none-any`); reportlab pulls Pillow and charset-normalizer wheels, no system library | platypus flows text across pages (keep-with-next, tables for the right-aligned leader); pypdf places two pages on each legal sheet (`merge_transformed_page`) and reads text back in tests |
| fpdf2 | LGPL-3.0 | pure Python | simpler flow model; LGPL is not the permissive license asked for |
| WeasyPrint | BSD | needs Pango and other system libraries | ruled out (system deps) |
| PyMuPDF | AGPL | wheels | ruled out (license) |

Both were installed from PyPI into `.venv` while planning (reportlab 5.0.1, pypdf 6.19.0) and go in
`backend/requirements.txt` as `reportlab>=5.0,<6` and `pypdf>=6.0,<7`.

### Fonts
The PDF uses the standard Times family (and Helvetica for the contact lines), which every PDF viewer
and printer has, so nothing is embedded and no font file enters the repo. These fonts cover
Windows-1252 (curly quotes, dashes, accented Latin letters); any other character prints as "?"
after NFKC normalization (a "fi" ligature becomes "fi"). If the print test or a translation shows a
problem, the fix is to embed Liberation Serif (SIL OFL, metric-compatible with Times New Roman), a
follow-up.

### What prints where (all three PRs)
The order of worship follows `liturgy_config.OUTLINE` (the Word copies' order), with the sample's
additions and its four section headings:

| Element | Leader (standing default) | Star | From |
|---|---|---|---|
| THE SERVICE FOR THE LORD'S DAY header | | | church name; worship leader, liturgist, organist (settings); date; service time (settings) |
| GATHERING FOR WORSHIP | | | |
| PRELUDE: 'title' / - composer | organist | | weekly (PR 2) |
| WELCOME AND ANNOUNCEMENTS | liturgist | | fixed |
| CALL TO WORSHIP (Leader/People) | liturgist | | draft |
| OPENING PRAYER | liturgist | | draft |
| HYMN: #n "title" | | * | draft (opening slot) |
| PRAYER OF CONFESSION (bold) | liturgist | | draft |
| ASSURANCE OF PARDON | liturgist | | draft, then `ASSURANCE_RESPONSE` |
| SUNG RESPONSE: "Gloria Patri" + words | | * | words: settings (PR 2; the traditional words until then) |
| PRAYER FOR ILLUMINATION | liturgist | | draft |
| RECEIVING THE WORD | | | |
| FIRST READING: ref + text | liturgist | | draft + fetched text (or pasted, PR 2) |
| NEW TESTAMENT READING: ref + text | worship leader | | same; then the credit line |
| SERMON: "title" | worship leader | | draft |
| AFFIRMATION OF FAITH: "The Apostles' Creed" + text | | * | fixed (traditional text) |
| HYMN (response slot), communion when on | | * | draft |
| PRAYERS OF THE PEOPLE/THE LORD'S PRAYER (heading only) | worship leader | | fixed |
| RESPONDING TO THE WORD; OFFERING OUR GIFTS; SUNG RESPONSE: "Doxology" | | * (Doxology) | fixed |
| OFFERTORY PRAYER | worship leader | | draft |
| SENDING OUT TO SERVE; HYMN (closing slot) | | * | draft |
| BENEDICTION | | * | draft (the church default prints as saved, quotes and "- Richard Halverson" included) |
| POSTLUDE: 'title' / - composer | organist | | weekly (PR 2) |
| *Congregation stands if able | | | settings (PR 2) |

Custom elements print after their anchor, as in the Word copies. An empty hymn slot, a switched-off
or blank section and a missing reading print nothing (as the Word copies); a blank sermon title
prints "[Sermon title]". The communion liturgy prints after the second hymn when it is on.

### Scripture text (answer 5)
- Fetched on the server when the file is built, for the two readings the Word copies print
  (`service_output.resolve_doc_readings`), through `usecases.passages` (the part cache, the 20 s
  deadline). The first alternative that comes back prints ("Psalm 23 or Psalm 100" prints Psalm 23).
  Verse line breaks become spaces; a blank line starts a paragraph.
- Translation: the draft's (`readings.translation`) when this deployment offers it, else the
  church's stored default when offered, else WEB: the same rule as step 1's `effectiveTranslation`.
- Credit line after the readings: "Scripture readings are from the {translation label}." (for
  example "the World English Bible (WEB)"). The public-domain translations need no notice; ESV text
  carries its own "(ESV)" from the ESV API, as Crossway's bulletin terms ask.
- A reading whose text does not come back prints "[Reading text unavailable]" (PR 1), never an
  error. PR 2 adds a "Paste the text" box per reading for a licensed translation the app cannot
  fetch; pasted text wins over fetched text.
- Rate limit: one `scripture` token per upstream part, charged before any fetch (a 429 fetches
  nothing), as `POST /scripture/passages`.

### API
- **`POST /documents/printed`** (PR 1), church-scoped (any member), plain `def`, body
  `PrintedDocumentIn = {format: "pdf" | "docx", translation: string <= 20 | null, service: ServiceDraft}`
  (`extra="forbid"`), answer 200 with the bytes, `Content-Type` `application/pdf` or the Word type,
  `Content-Disposition` `printed_bulletin_October_04_2026.pdf` (or `.docx`), `Cache-Control: no-store`.
  A new route rather than a third `variant` on `POST /documents`: its body (format, translation)
  and its answer (two media types, a rate-limit bucket) differ, and `DocumentIn` and its tests stay
  as they are. Nothing is stored or cached; no idempotency key (a pure render).
- PR 2 adds `bulletin` (below) to `ServiceDraft` (optional, so PR 1's clients keep working) and
  `GET`/`PUT /church/bulletin-settings`.
- PR 3 adds `POST /bulletin-images` (upload) and `GET /bulletin-images/{id}` (the member's preview).

### Data model (PR 2 and PR 3; PR 1 has none)
- **Standing settings** live in `churches.settings` (JSON, already there) under one key,
  `"bulletin"`: `{address_lines: [str], phone, email, website, facebook, service_time,
  worship_leader, liturgist, organist, stand_note, starred: [element key], gloria_patri_words,
  leaders: {element key: "worship_leader" | "liturgist" | "organist"}}`. No migration; read
  tolerantly (a missing or malformed value is the placeholder). Admins edit them in the Bulletin
  settings panel (`PUT /church/bulletin-settings`, admin only, as 6a will be); 6a later moves the
  panel into Settings without changing the storage.
- **Weekly fields** live in the draft and in the saved service: `bulletin: {prelude: {title,
  composer}, postlude: {title, composer}, leaders: {element key: name}, announcements: {ushers,
  deacon, coffee_hour, activities, prayer_concerns, collection}, reading_text: {ot, nt},
  cover_image_id}`. The draft gains the field with a version bump (v2 to v3, migrating with an
  empty `bulletin`); `ServiceDraft.bulletin` is optional; `services` gains one nullable JSON column
  `bulletin` in migration `0006_services_bulletin` (PR 2; a backup, read-only counts and the `--sql`
  preview first, as 0005). A new column rather than a key inside `liturgy`: `liturgy` holds only the
  eight sections and every reader filters it to them.
- **Carry forward** (answer 3): a new draft's `bulletin` starts from the most recently saved
  service's (by service date, before the draft's date): the announcements, the music and the cover
  picture id; the per-element leaders and pasted reading texts start empty.
- **Cover picture** (PR 3): stored in Postgres, in a new table `bulletin_images (id, church_id,
  content_type, bytes, width, height, created_by, created_at)` (migration `0007_bulletin_images`).
  The upload is checked (JPEG, PNG or HEIC from a phone; at most 10 MB in), decoded with Pillow
  (already installed with reportlab), turned upright, scaled to at most 1600 px on the long side
  and stored as JPEG (about 150-400 KB). The service's `bulletin.cover_image_id` points at it;
  "Keep last week's" carries the id forward. Images no service points at are removed when they are
  more than 60 days old.

  | Option | For | Against |
  |---|---|---|
  | **Postgres `bytea` (chosen)** | one system: transactions, church isolation, backups and restores include it; no new secret or service; the size is small after scaling (about 20 MB a year a church) | grows the database (the free tier's 500 MB holds decades at this rate); backups grow a little |
  | Supabase Storage | built for files; the database stays small | a second system to secure (bucket policies), a service-role key on Railway, files outside the nightly backup, and an orphan problem across two systems |

### The Bulletin step and the settings panel (PR 2)
A new step "Bulletin" between Liturgy and Review & send (the step bar gains a fifth step): the
prelude and postlude (title, composer), a "Who leads" list (each element with its standing leader,
changeable for this week), the announcements form (ushers/counters, deacon of the week, coffee hour,
and free-text boxes for this week's activities, prayers and concerns, and collection items), and
per reading a "Paste the text" box. A link opens the Bulletin settings panel (admins), with the
church details, the standing people, the stand note and starred elements, the Gloria Patri words
and the service time. PR 3 adds the cover picture to the step: "Upload a picture", "Keep last
week's picture", and a preview.

### Review & send (PR 1)
A **Printed bulletin** card after the Word documents card: what it prints, a note that PR 1 prints
[placeholders] for what the app does not know yet, **Download printed bulletin** (the PDF, primary)
and **Download Word version** (outline), each with its own "Preparing…"/"Still working…", gated by
the service date and the readings like the Word copies, with the same error toasts and the same save
tip after a download. The Word documents card does not change.

## Scope by PR

- **PR 1 (plan written):** the booklet PDF and Word file from the draft (`printed_bulletin`,
  `printed_pdf`, `printed_docx`), `POST /documents/printed` with the readings' text, the Printed
  bulletin card; placeholders for the church details, the people, the service time, the music, the
  cover picture and the announcements; the traditional Gloria Patri words and the Apostles' Creed;
  the sample's stars and leader roles as defaults. No migration, no new variable. Then the guided
  phone check and the print test.
- **PR 2:** the standing settings (`churches.settings["bulletin"]`, the panel, the GET/PUT route),
  the Bulletin step, the weekly fields in the draft (v3) and in `services.bulletin` (migration
  `0006_services_bulletin`), carry forward, pasted reading text, the placeholders replaced. Then a
  guided phone check.
- **PR 3:** the cover picture (table `bulletin_images`, migration `0007_bulletin_images`, upload,
  preview, keep last week's, printed in the PDF and the Word file under the church name with the
  reference and date over it). Then a guided phone check and a second short print test (the picture).

## Testing

- Pure: the booklet's page order (`booklet_positions`, `booklet_sides`: every page once, blanks
  before the back page, 4/8/12 pages), the date and the filenames, reading paragraphs, the order of
  worship (element order, leaders, stars, Leader/People and the Assurance as the Word copies read
  them, custom elements, empty slots, communion, the credit line and the unavailable text), the
  cover and the back page.
- Render: the PDF's sheets are 1008 x 612 pt, the side count is half a multiple of 4, text read back
  with pypdf is in booklet order (side 1: the back page then the cover; side 2: page 1 ...), a long
  service takes another sheet, an unprintable character becomes "?"; the Word file is 7 x 8.5 in
  with the parts starting new pages and the leader at a tab.
- API: both formats with their headers, the readings fetched in the draft's translation (a fake
  `fetch_part`), the fallback to the church's translation, no readings fetch nothing, the
  `scripture` bucket charged per part with a 429 that fetches nothing, member access and church
  isolation, 422s naming the field, the log line without text.
- Frontend: the body (`printedRequest`), the fallback filename, the card (text, buttons, a PDF
  download with the translation, the Word fallback name, the date gate, an error toast).
- Manual: the guided phone check (download and open both files) and the print test at the church.

## Risks

- **The printer's duplex setting.** "Flip on short edge" is the usual booklet setting for landscape
  sheets; a printer that flips the other way prints the backs upside down. The print test finds out;
  the fix is a note on the card or rotated backs, a small change.
- **Blank pages.** A short service pads with up to three blank pages before the back. PR 2's
  announcements fill some of that; the print test shows whether the owner wants "Notes" pages instead.
- **The PDF on a phone** reads in sheet order (answer 6: one version). The Word version reads in
  order.
- **Upstream scripture text** can be slow or missing; the file still prints, with the placeholder.

## Notes from the PR 1 plan (2026-10-02)

- reportlab 5.0.1 and pypdf 6.19.0 installed from PyPI into `.venv` as pure-Python wheels; the
  plan's code was built and its directives replayed on a fresh worktree (backend 1335 → 1363 passed,
  frontend 655 → 660 in 83 files).
- A service shaped like the owner's sample (names replaced by placeholders) renders as five booklet
  pages (cover, three inside pages, announcements), padded to eight on two legal sheets; the
  imposed sides were rendered to images and compared with the sample's pages.
- The Word file was checked by reading it back with python-docx; LibreOffice in the planning
  container could not open any `.docx`, so the owner's phone check is its first visual check.

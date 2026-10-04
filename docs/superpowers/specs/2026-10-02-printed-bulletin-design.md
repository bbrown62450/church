# Printed Bulletin: Design

Date: 2026-10-02
Status: owner answers of 2026-10-02 ("all recommended") are binding, with the layout decided as
**layout B** (owner, 2026-10-02, binding; below); PR 1 has its plan
(`docs/superpowers/plans/2026-10-02-printed-bulletin-1.md`); PR 2 and PR 3 get their own plans.
Builds on:
- `2026-10-02-printed-bulletin-idea.md` (the idea note)
- `2026-09-25-slice-5a-documents-archive-design.md` (5a: `POST /documents`, `ServiceDraft`, the archive)
- `2026-09-25-migration-foundations-design.md` (F)
- `2026-09-25-slice-6a-settings-church-design.md` (6a, where the bulletin settings fold in later)

## Why

The app makes the pastor's Word working files, but the church still builds the real Sunday
bulletin by hand. The owner's sample (First Presbyterian Church's bulletin for September 27, 2026,
shared in the session and not committed) shows what it holds: booklet pages on legal paper, two to a side, with a
cover, the order of worship with the leaders' names, the readings in full, the sung responses, and an
announcements page. Most of the order of worship is already in the draft. This design makes the
app print it, first from what it knows (PR 1), then with the weekly and standing details
(PR 2) and the cover picture (PR 3).

## Owner answers (Beau, 2026-10-02, "all recommended"; binding)

| # | Answer |
|---|---|
| 1 | **Output:** a print-ready PDF in the folded legal-landscape booklet layout, plus an editable Word version. (The layout is now B, below: two pages to a side in reading order, not folded.) |
| 2 | **Standing church settings:** church name, address, phone, email, website, Facebook name; the standing worship leader, liturgist and organist; the "*Congregation stands if able" note and which elements get the star; the Gloria Patri words. **Weekly:** prelude and postlude (title, composer), a per-element leader when different, announcements. |
| 3 | **Announcements:** a simple form for ushers, deacon of the week and coffee hour, plus free-text boxes for activities, prayer concerns and collection items; each carries forward from last week. |
| 4 | **Cover picture:** uploaded each week, with the option to keep last week's; printed under the church name with the scripture reference and date over it. |
| 5 | **Scripture:** full text in the translation chosen on step 1, with a credit line; a way to paste your own text for a licensed translation the app can't fetch. |
| 6 | **One version** (no separate mailing version) for now. |
| 7 | **Keep the pastor's and bulletin Word copies;** add a third download, "Download printed bulletin". |
| 8 | **Weekly fields on a new "Bulletin" step** between Liturgy and Review; standing church details in a small **Bulletin settings** panel now, folded into 6a later. |
| 9 | **Three PRs:** (1) the booklet PDF (and Word) from what the app already knows, placeholders for the rest; (2) the weekly fields and announcements (and the standing settings panel); (3) the cover picture upload. |
| 10 | **Checks:** a guided phone check after each PR, and a print test on legal paper at the church after PR 1 (folds and margins; with layout B, the page order and the margins). |

### Owner decisions after the answers (Beau, 2026-10-02; binding)

- **Layout B.** The printed PDF matches the owner's sample: legal paper, landscape, two booklet
  pages side by side in **reading order** (side 1 is the cover and page 1, side 2 pages 2 and 3,
  and so on). No folding imposition and no padding to a multiple of 4: N pages take ceil(N/2)
  sides, and an odd N leaves the last side's right half blank. The announcements page is the last
  page, as in the sample. This replaces the folded layout of answer 1 and of this spec's first
  draft; the folded booklet is a later option ("Later options" below), not built in PR 1.
- **The PR 1 plan's Questions 1-12:** "all recommended", with question 3 (the PDF's layout)
  answered as layout B.

### PR 2 planning answers (Beau, 2026-10-02, "all recommended"; binding)

1. **PR 2 splits in two.** **PR 2a, Bulletin settings:** the panel and `GET`/`PUT
   /church/bulletin-settings` for the church details, the standing worship leader, liturgist and
   organist, the service time, the stand note, the starred elements and the Gloria Patri words,
   printed at once; no migration, no draft change. **PR 2b, the Bulletin step:** prelude and
   postlude, the announcements, pasted reading text, carry forward, the draft v3 and migration
   `0006_services_bulletin`. Order: 2a, 2b, then PR 3 (cover picture).
2. **Admins only** change the Bulletin settings; every member's printed bulletin uses them.
3. **A blank field prints nothing** (no line, no [placeholder]); the Printed bulletin card lists
   what is still empty ("Not filled in: ...") so it is caught before printing. In 2a this covers
   the standing settings; 2b adds the weekly fields.
4. **Announcements:** ushers and counters, deacon of the week, coffee hour, activities, prayers
   and concerns, collection items, plus one **"Other announcements"** box.
5. **Carry forward with a check:** every announcement carries forward (answer 3), and each
   carried-over box shows "From last week. Check before printing." until it is edited.
6. **The Bulletin step is optional:** it never blocks Review, the Word copies or the printed
   bulletin.
7. **Who leads:** the step shows the three people at the top (from settings, changeable for this
   week); changing one part's leader sits behind "Change who leads a part".
8. **Migration 0006** follows 0005's routine: a backup, read-only counts and the `--sql` preview
   before the merge, a check query after the deploy, one step at a time.

### PR 3 planning answers (Beau, 2026-10-03, "all recommended, the printer is color"; binding)

1. **Two PRs, server first** (as PR 2b): **PR 3a** brings the `bulletin_images` table (migration
   `0007_bulletin_images`), the upload and preview routes, `bulletin.cover_image_id`, and the
   picture printed in the PDF and the Word version; the deployed pages keep working. **PR 3b**
   brings the upload on the Bulletin step. 3b opens only after 3a is live and checked.
2. **Text over the picture:** the reading and the date in white on a dark see-through band across
   the bottom of the picture.
3. **Fit:** the picture fills the box, trimmed evenly at the edges (centered crop).
4. **Color:** the church's printer prints in color, so the picture stays in color.
5. **Formats:** JPEG and PNG only (no HEIC package); Safari is expected to turn an iPhone photo
   into JPEG on upload, to be verified on the owner's phone during the PR 3b check.
6. **No picture this week:** no box at all; the reading and the date sit centered where the
   picture would be.
7. **Keep last week's picture:** it carries forward like the music, marked "From last week. Check
   before printing.", with **Keep as is**.
8. **Who can upload:** any member who can edit the service.
9. **Old pictures:** a picture no saved service points at is removed after 60 days.
10. **Checks:** migration 0007 follows 0006's routine (a backup, read-only counts, the `--sql`
    preview; after the deploy, one read-only check), a phone check after each PR, and a short print
    test of a cover with a picture.

## The sample, read closely

The sample PDF is three legal-landscape pages (1008 x 612 pt), each holding two 7 x 8.5 in pages
side by side in **reading order**: cover | 1, 2 | 3, 4 | 5. It does not fold into a booklet, and
that is what the owner chose (layout B): the app's PDF has the same two-up reading order, and the
print test (answer 10) confirms the page order and the margins on the church's printer.

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
  announcements page last (numbered, as in the sample).
- **Two to a side (layout B):** each legal landscape side (1008 x 612 pt) holds two booklet pages
  side by side in reading order: side 1 is the cover | page 1, side 2 is page 2 | page 3, and so on.
  Any page count: N pages take ceil(N/2) sides; nothing is padded; an odd N leaves the last side's
  right half blank (no page number there). Nothing is folded, so the sheets can be printed on one
  side or both. With the sample's content (shorter readings) that is 5 pages on 3 sides; the
  owner's sample has 6 pages on 3 sides.
- **One version** (answer 6): the PDF reads in order on a phone too (the first page shows the
  cover and page 1 side by side); the Word version has the same pages one to a page.
- **Word version:** the same pages in reading order on 7 x 8.5 in pages (Times New Roman 11 pt,
  0.5 in margins, leaders at a right tab stop, page numbers from the first inside page). To print
  it two to a legal sheet as the PDF does, use the printer's "2 pages per sheet" setting. The PDF
  is the print copy.

### PDF library
| Option | License | Install on Railway | Fit |
|---|---|---|---|
| **reportlab 5** (chosen; runtime) | BSD | a pure-Python wheel (`py3-none-any`); it pulls Pillow (a binary wheel with its libraries inside) and charset-normalizer (already installed through requests), no system library | platypus flows text across pages (keep-with-next, tables for the right-aligned leader); one page template with two frames lays two booklet pages on each legal side in reading order, in one pass |
| **pypdf 6** (tests only) | BSD-3-Clause | pure-Python wheel, in `requirements-dev.txt` only | reads the PDF's text back in the tests; the first draft also used it at runtime to impose the folded booklet, which layout B does not need |
| fpdf2 | LGPL-3.0 | pure Python | simpler flow model; LGPL is not the permissive license asked for |
| WeasyPrint | BSD | needs Pango and other system libraries | ruled out (system deps) |
| PyMuPDF | AGPL | wheels | ruled out (license) |

Both were installed from PyPI into `.venv` while planning (reportlab 5.0.1, pypdf 6.19.0):
`reportlab>=5.0,<6` in `backend/requirements.txt` (the only new runtime package), `pypdf>=6.0,<7` in
`requirements-dev.txt` (CI only). Two pages per side need no imposition library: reportlab draws
them directly.

### Fonts
The PDF uses the standard Times family (and Helvetica for the contact lines), which every PDF viewer
and printer has, so nothing is embedded and no font file enters the repo. These fonts cover
Windows-1252 (curly quotes, dashes, "…", accented Latin letters), which print as they are; any other
character is NFKC-normalized (a "fi" ligature becomes "fi"), an invisible format character (a
zero-width space, a byte order mark) is dropped, and what is left prints as "?". If the print test or a translation shows a
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
  carries its own "(ESV)" from the ESV API, as Crossway's bulletin terms ask. From PR 2b it names
  only the fetched readings whose text came back: one of them, "The {First Reading | New Testament
  Reading} is from the {label}."; none (pasted, or "[Reading text unavailable]"), no line.
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
  tolerantly (a missing or malformed value reads as its default: the sample's stars, leaders'
  roles, stand note and Gloria Patri words, and blank for every detail and name; a blank value
  prints nothing, PR 2 planning answer 3). Admins edit them in the Bulletin
  settings panel (`PUT /church/bulletin-settings`, admin only, as 6a will be); 6a later moves the
  panel into Settings without changing the storage.
- **Weekly fields** live in the draft and in the saved service: `bulletin: {prelude: {title,
  composer}, postlude: {title, composer}, people: {worship_leader, liturgist, organist} (null:
  the settings' name; PR 2 planning answer 7), leaders: {element key: name}, announcements:
  {ushers, deacon, coffee_hour, activities, prayer_concerns, collection, other} (answer 4),
  reading_text: {ot, nt}, unchecked: [box]}` (`unchecked`: the boxes still holding last week's
  text, not checked yet, so the marks come back when the service is opened again), and PR 3 adds
  `cover_image_id` (PR 2b plan, `docs/superpowers/plans/2026-10-03-printed-bulletin-2b.md`). The draft gains the field with a version bump (v2 to v3, migrating with an
  empty `bulletin`); `ServiceDraft.bulletin` is optional (a save without it keeps the saved one,
  with the pasted text of a reading that changed emptied, since `reading_text` is stored by
  position); `services` gains one nullable JSON column
  `bulletin` in migration `0006_services_bulletin` (PR 2; a backup, read-only counts and the `--sql`
  preview first, as 0005). A new column rather than a key inside `liturgy`: `liturgy` holds only the
  eight sections and every reader filters it to them.
- **Carry forward** (answer 3): a new draft's `bulletin` starts from the most recently saved
  service's (by service date, before the draft's date): the announcements, the music and the cover
  picture id; the per-element leaders and pasted reading texts start empty. As planned for PR 2b:
  only a draft that is not a saved service, when the Bulletin step or Review & send shows it for
  its date, into each box not yet typed in, edited or kept (a box at a time); each carried box
  shows "From last week. Check before printing." until it is edited or kept (planning answer 5),
  and the marks are saved with the service. A saved service saved again as a new service on
  another date ("Save as new service") is treated the same way: its music and announcements are
  marked to check, and this week's people, the part leaders and the pasted texts start empty.
- **Cover picture** (PR 3): stored in Postgres, in a new table `bulletin_images (id, church_id,
  content_type, bytes, width, height, created_by, created_at)` (migration `0007_bulletin_images`).
  The upload is checked (JPEG, a phone's multi-picture JPEG included, or PNG; at most 10 MB in;
  PR 3 planning answer 5: no HEIC, an iPhone's Safari sends a JPEG), decoded with Pillow (already
  installed with reportlab), one at a time and within 20 s (a JPEG of more than 64 scans, or a
  progressive JPEG or a PNG of more than 24 million pixels, is refused before it is decoded), turned
  upright, its colors converted to sRGB, scaled to at most 1600 px on the long side and stored as
  JPEG with no camera data or other metadata (no EXIF, XMP or comment), at most 0.6 MB (a lower
  quality, then a smaller size, until it fits; a phone photo is usually 0.2-0.5 MB). The picture is the request body of
  `POST /bulletin-images` (no multipart form, so no new package). The service's
  `bulletin.cover_image_id` points at it (a JSON key, no foreign key; an id the church does not
  have is saved and printed as no picture); it carries forward with the music, marked to check
  (planning answer 7). A bulletin that does not say (a page from before PR 3b) keeps the saved
  picture on a save and prints PR 1's box. Images no saved service points at are removed when they
  are more than 60 days old, on any church's next upload (planning answer 9). Since any Google
  account can create a church, a church keeps at most 160 pictures (its oldest unused ones make
  room) and all churches' pictures together at most 150 MB; past either an upload is refused with
  a message (PR 3 plan review, `docs/superpowers/plans/2026-10-03-printed-bulletin-3.md`).

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
and the service time. PR 3 adds the cover picture to the step: "Choose a picture", a preview
with the band the reading and the date print on, **Remove**, and last week's picture carried forward with "From last week. Check before printing."
and **Keep as is** (PR 3 planning answer 7).

### Review & send (PR 1)
A **Printed bulletin** card after the Word documents card: what it prints, a note that PR 1 prints
[placeholders] for what the app does not know yet, **Download printed bulletin** (the PDF, primary;
"Ready to print on legal paper, two pages to a side.")
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
  guided phone check. PR 2b ships backend first as two PRs: 2b-1 (the migration, the API saving,
  opening, carrying and printing the weekly fields; a page from before 2b-2 keeps working and
  prints PR 1's placeholders) is merged and live before 2b-2 (the draft v3, the Bulletin step,
  carry forward and the card). PR 3 follows the same order (its API and migration first).
- **PR 3:** the cover picture (table `bulletin_images`, migration `0007_bulletin_images`, upload,
  preview, keep last week's, printed in the PDF and the Word file under the church name with the
  reference and date over it). Then a guided phone check and a second short print test (the picture).
  As PR 2b, two PRs, backend first (PR 3 planning answer 1): 3a (the migration, the upload and
  preview routes, `cover_image_id`, the printing; a page from before 3b keeps working and prints
  PR 1's box) is merged and live before 3b (the picture on the Bulletin step).

## Testing

- Pure: the date and the filenames, reading paragraphs, the order of
  worship (element order, leaders, stars, Leader/People and the Assurance as the Word copies read
  them, custom elements, empty slots, communion, the credit line and the unavailable text), the
  cover and the back page.
- Render: the PDF's sides are 1008 x 612 pt, text read back with pypdf and split into each side's
  halves is in reading order (side 1: the cover then page 1; side 2: pages 2 and 3 ...), N pages
  take ceil(N/2) sides with the announcements last (an even and an odd count; an odd count's last
  right half blank), an unprintable character becomes "?"; the Word file is 7 x 8.5 in
  with the parts starting new pages and the leader at a tab.
- API: both formats with their headers, the readings fetched in the draft's translation (a fake
  `fetch_part`), the fallback to the church's translation, no readings fetch nothing, the
  `scripture` bucket charged per part with a 429 that fetches nothing, member access and church
  isolation, 422s naming the field, the log line without text.
- Frontend: the body (`printedRequest`), the fallback filename, the card (text, buttons, a PDF
  download with the translation, the Word fallback name, the date gate, an error toast).
- Manual: the guided phone check (download and open both files) and the print test at the church.

## Risks

- **Printing on both sides.** Layout B prints fine on one side. On both sides, the printer's
  two-sided setting must keep the backs upright (for landscape sheets usually "flip on short edge");
  the print test records what the church uses.
- **A blank half.** An odd page count leaves the last side's right half blank. PR 2's announcements
  may fill it; the print test shows whether the owner wants a "Notes" page there.
- **Upstream scripture text** can be slow or missing; the file still prints, with the placeholder.

## Later options

- **Folded booklet.** The PDF imposed for folding: the page count rounded up to a multiple of 4
  with blank pages just before the announcements (which then sit on the back cover); sheet k
  (0-based) of N pages prints (N-1-2k | 2k) on its front and (2k+1 | N-2-2k) on its back; printed
  on both sides, flipped on the short edge, and folded in half. It was the first draft's layout and
  is not built (owner decision, layout B); it would come back as a choice beside layout B, with its
  own card wording and a print test of the fold.

## Notes from the PR 1 plan (2026-10-02)

- reportlab 5.0.1 and pypdf 6.19.0 installed from PyPI into `.venv` as pure-Python wheels; the
  plan's code was built and its directives replayed on a fresh worktree (backend 1335 → 1357 passed,
  frontend 655 → 660 in 83 files; layout B, 2026-10-02).
- A service shaped like the owner's sample (names replaced by placeholders, shorter readings)
  renders as five booklet pages (cover, three inside pages, announcements) on three legal sides,
  the last right half blank; the sides were rendered to images and compared with the sample's
  three pages: the same two-up reading order.
- The Word file was checked by reading it back with python-docx; LibreOffice in the planning
  container could not open any `.docx`, so the owner's phone check is its first visual check.

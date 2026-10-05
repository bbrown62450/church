# Voices of the Church: Design (V1 and V2)

Date: 2026-10-05
Status: design for review. V1 has its plan (`docs/superpowers/plans/2026-10-05-voices-v1.md`, whose
"Questions for the owner" 1-7 put this design's owner-visible choices, each with a recommendation);
V2 is designed here and gets its own plan after V1 is live.
Builds on:
- `2026-10-01-voices-of-the-church-decisions.md` (the owner's answers of 2026-10-01, the planning
  answers and the source decision of 2026-10-05; all binding)
- `2026-10-05-voices-rights-check.md` (the rights research and the source facts)
- `2026-09-25-slice-2-readings-design.md` (step 1, the lectionary, `scripture_refs`)
- `2026-09-25-migration-foundations-design.md` (F)

Legend: **[decided]** = an owner decision, cited. **[proposed]** = this design's choice; the
owner-visible ones are the V1 plan's "Questions for the owner", each with a recommendation.

## Why

A preacher preparing a sermon reads what the church has said about the passage. Thomas Aquinas
gathered the Greek and Latin fathers' comments on every verse of the four Gospels into the Catena
Aurea, and Newman's Oxford translation of 1841-45 is in the public domain. Voices of the Church
puts those comments next to the Sunday's Gospel on step 1, where the preacher already reads the
passage, and (V2) lets an image or a phrase of one of them be woven into a prayer of the service,
with a small "after {Name}" credit.

## Scope

**V1 (one PR): the text and the panel.**
- The Catena's text as data files the app ships with, from the archive.org scans of the 1841-45
  Oxford printing (John Henry Parker), all four Gospels **[decided: source decision 1]**: every
  section's place (its verses, volume, printed pages, scan pages), and the text of each section
  someone has checked against the page images.
- A developer's tool that turns archive.org's OCR into drafts (never run in production).
- `GET /voices?reference=...`: the sections overlapping a Gospel passage.
- The **Voices of the Church** panel on step 1 (Readings), under the Gospel reading, collapsed,
  with the count of quotations **[decided: planning answer 3]**.
- The checked text for Matthew 22:15-22 (the owner's test Sunday, October 18, 2026) and the
  Gospels of the two Sundays after it: Matthew 22:34-40 and 22:41-46 (October 25), 23:1-4 and
  23:5-12 (November 1, the default set); five sections, 92 quotations, checked word by word
  against the page images while planning (the plan's check record).
- No database change **[decided: planning answer 2]**. No AI. No new package, no new variable.

**V2 (its own PR, after V1 is live): designed in "V2" below, not built in V1.**
- "Bring this into the liturgy" on a quotation **[decided: answers 1(3), planning answer 5]**.
- The "after {Name}" credit on the card and in the printed bulletin and both Word copies
  **[decided: answer 8, planning answer 6]**.

**Out of scope** **[decided: answer 2]**: ancient collects, the homilies (Schaff), The Faith
Received. Quotations are for preparation only and never print **[decided: answer 3]**.

## The source

**[decided: source decision 1]** The text of record is the printed page of the 1841-45 Oxford
edition, from archive.org's scans; not CCEL's transcription (whose terms ask permission to
republish, and which has Matthew and Mark only).

| Volume | Gospel | archive.org item | Title page | Translator named in the volume | Copy scanned |
|---|---|---|---|---|---|
| I, Part I | Matthew 1-10 | `catenaaureacomme00thomuoft` | 1841 | Mark Pattison | University of Toronto |
| I, Part II | Matthew 11-21 | `a6788682p201thomuoft` | 1841 | Mark Pattison | Saint Mary's College of California |
| I, Part III | Matthew 22-28 | `catenaurecommpt301thomuoft` | 1842 | Mark Pattison | University of Toronto |
| II | Mark | `catenaaureacomme02thomuoft` | 1842 | John Dobree Dalgairns | University of Toronto |
| III, Part I | Luke 1-10 | `catenaaureacomme03thomuoft` | 1843 | Thomas Dudley Ryder | University of Toronto |
| III, Part II | Luke 11-24 | `p2catenaaureacom03thomuoft` | 1843 | Thomas Dudley Ryder | University of Toronto |
| IV, Part I | John 1-10 | `catenaaureacomme04thomuoft` | 1845 | not named | University of Toronto |
| IV, Part II | John 11-21 | `p2catenaaureacom04thomuoft` | 1845 | not named | University of Toronto |

Every title page reads "OXFORD, JOHN HENRY PARKER; J. G. F. AND J. RIVINGTON, LONDON."; the
prefaces are signed "J. H. N." (rights check §1). Matthew Part II is the one volume whose only
scan is not a Toronto copy (its archive.org record carries no copyright status; it is the same
1841 printing, title page "MDCCCXLI."). The rights check found the text public domain in the US
and the UK; the scans carry no usage terms that the session could read (archive.org's terms page
is rendered by JavaScript) **[rights check §3]**.

Each scan page has an address: the image
`https://archive.org/download/<item>/page/n<leaf>.jpg` and the viewer
`https://archive.org/details/<item>/page/n<leaf>/mode/1up`, where `<leaf>` is the scan's page
index (0-based; Matthew 22:15-22 is printed pages 748-752, leaves 19-23 of
`catenaurecommpt301thomuoft`).

### "Exactly as printed" **[decided: planning answer 4]**, made precise **[proposed]**

Kept as printed: every word and its spelling ("shew", "pourtrayed", "offence", "Saviour"), the
capitals ("Thou", "Him"), the punctuation (the printing's own em dashes inside a comment included:
"thoughts—with all thy soul"), the ligature "æ" (the printing sets "Cæsar", "Judæa", "Quæst."),
the italics (the printing sets the Gospel's words quoted inside a comment in italics), the
speaker's label ("Pseudo-Chrys.", "Jerome;", "Id."), the margin references ("Chrys. Hom. lxx.",
"Aug. de Doctr. Christ. i. 22.", "Gloss. non occ.") and the margin's Scripture references ("1 Tim.
4, 3."), the printing's marginal variants and their marks in the text ("good¹" with "¹ alia re
frui."), a printed paragraph break inside one father's comment. A stop right after italic words
is set inside the italics ("*Master,*"): the printing sets it in the italic font wherever the scan
shows the difference (the semicolons after "burdens" and "footstool"), and a scan cannot tell an
italic comma or full stop from a roman one; a stop the page shows roman stays outside ("*they will
not*;"). The volumes' printed errata are the printers' own corrections and part of the printing:
applied where they touch a checked section, a corrected speaker with a note on the panel
("Corrected by the volume's errata: printed as JEROME") **[proposed; question 8]**. None touches
the five sections V1 checks (Matthew Part III has no errata page).

Not kept (typesetting, not wording): the line and page breaks; a word the line end hyphenated is
joined ("popu-lace" is "populace"; a word the printing hyphenates anyway keeps its hyphen,
"first-fruits", "self-satisfied"); the space the printing puts before ";", ":", "?" and "!"
("Thou ?" is "Thou?"); curly quotation marks and apostrophes are typed straight; small capitals
are typed as capital and small letters; a margin reference's tight spacing ("Ps.11,5." is "Ps. 11,
5."); page signatures ("VOL. I. 3 D").

Not shown in V1: the editors' footnotes and their marks in the text (Matthew 23:9's note "a", the
1841 editors' remark on the soul's creation, is not a father's word; a later version may add them),
and the Gospel text the Catena prints before each section (the step already shows the reading).

Aquinas's own words linking the comments, where he prints them as a paragraph of their own ("It
follows, *On these two commandments hang all the Law and the Prophets.*", after Hilary on Matthew
22:39-40), are no father's: they stay in their place as an item of their own with no label and no
father, shown under "Aquinas, linking the comments" in muted text, not counted as a quotation, and
never offered to V2 or credited "after" anyone **[proposed; question 9]**. A connective inside a
father's comment ("whence it follows, *When they had heard ...*") is printed as part of that
comment and stays in it.

The panel shows the father's full name, then the margin reference as printed; the label as printed
is kept in the data (for checking, and for V2's prompt) (question 4).

## The data **[proposed]**

### Files

`backend/data/catena/matthew.json`, `mark.json`, `luke.json`, `john.json`: one per Gospel, so a
request reads only the Gospel it needs. The directory is inside `backend/` because Railway
deploys that directory (the root `.gitignore`'s `data/*.json` does not reach it). Each file holds
one section a line, and a checked section's comments one a line, so a check's diff shows what
changed; in the shape of:

```json
{
 "format": 1,
 "gospel": "Matthew",
 "sections": [
  {"id": "matthew-22-1-14", "start": [22, 1], "end": [22, 14], "volume": "mt3",
   "pages": [738, 748], "leaves": [9, 19], "status": "unchecked"},
  {"id": "matthew-22-15-22", "start": [22, 15], "end": [22, 22], "volume": "mt3",
   "pages": [748, 752], "leaves": [19, 23], "status": "checked",
   "checked": {"on": "2026-10-05", "by": "Claude (Voices V1 planning session), word by word against the page images"},
   "comments": [
    {"label": "Pseudo-Chrys.", "father": "Pseudo-Chrysostom", "work": null,
     "text": "As when one seeks to dam a stream of running water, ... *Then went the Pharisees; went* to the Herodians. ...",
     "notes": []},
    {"label": "Chrys.", "father": "Chrysostom", "work": "Chrys. Hom. lxx.",
     "text": "They send their disciples and Herod's soldiers together, ...", "notes": []}
   ]}
 ]
}
```

- `id`: the Gospel and the verses (`matthew-22-15-22`; across chapters `matthew-15-39-16-4`);
  the Catena sometimes prints two sections on one verse, and the second gets `-2`.
- `start`, `end`: `[chapter, verse]`, inclusive, within the chapters' verse counts
  (`catena.VERSES`, the English Bible's numbering, which the printing follows); a section may
  cross one chapter end, never two. Two sections may share a verse (the Catena splits some
  verses). Every verse of a Gospel is in some section: a verse the OCR left between two sections
  (a missed verse number) goes to the section before it, so a reading never falls between
  sections.
- `volume`: a key of `catena.VOLUMES` (the table above, with the year and the translator).
- `pages`: the first and last printed page; `leaves`: the first and last scan page; both run
  forwards, and in each volume a page is always the same distance from its leaf.
- `status`: `"unchecked"` (no text in the file at all) or `"checked"` with `checked` (exactly
  `on`, the date, and `by`, who and how; never an email address), `comments` and, when the check
  applied the volume's printed errata, `errata` (each entry as printed). No other key: a draft's
  `footnotes` and `warnings` never enter a file.
- A comment: `label` (as printed), `father` (the name shown, one of `catena.FATHERS`), `work`
  (the margin reference beside the label, or null), `text` (as printed; `*...*` is italic;
  `\n\n` separates printed paragraphs; nothing else is markup), `notes` (the other margin notes
  beside the comment, such as Scripture references, as printed), and `printed_label` only when
  the errata corrected the speaker. Aquinas's linking words: `label`, `father` and `work` null.

A comment is identified by its section's `id` and its place in the list (V2 uses that pair).

### What ships in V1: every section's place, and the text of checked sections only (question 1)

The files hold every section of the four Gospels as the tool splits them (Matthew 277, Mark 104,
Luke 245, John 190 sections), but **text only for the sections checked against the page images**.
Uncorrected OCR never enters the repository or the app, so a bug can never show it, and the
files stay small. Checking a section later adds its text to the file (a small, reviewable diff).

The other choice was to ship the whole cleaned OCR (about 4 MB) marked unchecked and hidden until
checked. It saves a checker from running the tool, but it puts known-wrong text in the app (one
bug from being shown), makes every diff of the files large, and needs the four files in memory.
Recommended: text only for checked sections.

### Loading and size

`backend/catena.py` (pure, no FastAPI) reads a Gospel's file on its first request and keeps it
(`functools.lru_cache`, at most four), checking it against the format as it reads (an error is a
bug caught by the tests before it ships). The four files are about 165 KB in all (Matthew's 89 KB
with its five checked sections; a section's entry is about 150 bytes, a checked section 8-25 KB).
The panel's answer for one Sunday is a few KB to about 25 KB (Matthew 22:34-46, two sections, 36
quotations).

## The import tool **[proposed]**

`backend/scripts/catena_import.py`, standard library (and `catena`) only, run by a developer, never
by the app, CI or Railway:

- `fetch --cache DIR`: downloads each volume's ABBYY OCR (`<item>_abbyy.gz`, about 94 MB for the
  eight). Of archive.org's OCR files, ABBYY's is the one that keeps each character's box on the
  page, italics, small capitals and type size; the plain text (`_djvu.txt`) mixes the margin notes
  into the lines and loses the italics.
- `draft --cache DIR GOSPEL`: writes `DIR/draft-<gospel>.json`, every section with its cleaned
  text (not committed; the working copy for a checker). About a minute and a half a Gospel; the
  word counts of all eight volumes are kept in `DIR/vocabulary.json`.
- `show --cache DIR "Matthew 22:15-22"`: prints the drafts of the overlapping sections and the
  addresses of their page images.
- `checkout --cache DIR "Matthew 22:15-22" --out DIR2`: writes each overlapping section to check
  as `DIR2/<id>.json` with only the keys a data file allows and a placeholder `checked` that
  `index` refuses until the checker fills it in.
- `index --cache DIR GOSPEL [--checked FILE ...]`: rewrites the Gospel's data file: each drafted
  section as an unchecked entry with no text, each checked section of the file kept exactly as it
  is, each `--checked` file (one section, as the file holds it) added; a drafted section that
  shares a verse with a checked one gives way to it, so a checker can correct a section's verses.
  Gaps between sections are filled (a verse the OCR left out goes to the section before it). The
  result must pass `catena.parse` or nothing is written.

How it splits and cleans (measured on the eight volumes, 2026-10-05):
- **The margin** is the characters left or right of the page's text column (the median start and
  end of the full lines); on the right a note starts at the first letter or digit past the
  column's end after a gap (the OCR often reads a note's first letter into the line's last word,
  "Inasmuch M"). A note runs over the lines below it, its own lines included, until a reference
  ends ("Matt. 25, 40.") or a label on the line starts a comment with its own reference. A note on a
  label's line is that comment's `work`; the others are its `notes`. A left note's last stop can
  stand in the gutter just before the column ("Acts 15," beside "in the Acts"): punctuation before
  the column's first letter goes to the note, never the text.
- **Kinds of line** by the height of the small letters against the volume's commonest: the Gospel
  text is set larger (29-30 px against 25-26 at 400 dpi), footnotes and running heads smaller;
  chapter headings by their capitals (46 px). ABBYY's type size works for seven volumes but not
  for Matthew Part II, whose OCR sizes the Gospel text and the comments alike. The running head
  gives the printed page number when it is the volume's usual distance from the leaf (or one three
  pages nearby agree on); others are counted from the pages before (the OCR read "620" and "621"
  as "20" and "21"); page signatures are dropped.
- **Sections:** Gospel lines after comments start a section; the verse numbers at the start of
  the Gospel lines give its range. A chapter heading starts the next chapter (its Roman numeral
  when that is one or two on, else the chapter after); a verse 1 with no heading moves the chapter
  on too, unless a heading follows within 60 lines, and when the next heading names the chapter
  that verse 1 moved to, the verse 1 was a misread number and the verses since go back to the
  chapter before (the first version filed John 7-10 one chapter late this way). Result: Matthew
  277, Mark 104, Luke 245, John 190 sections; the tool warns where a section does not follow the
  one before (Matthew 16, Mark 9, Luke 24, John 24), mostly a verse number the OCR missed or the
  Catena's own order (the Beatitudes in the Vulgate's order, verse 5 before verse 4). A second
  section on the same verses gets `-2`.
- **Comments:** each small-capital label starts a comment (Matthew Part II's OCR has no small
  capitals, so there a known label starting a sentence does); a label broken at the line end
  ("PSEUDO-" / "CHRYS.") is joined; the label is matched to the known labels (`LABELS`, with the
  father each names; "Id." is the father before it; OCR-garbled labels such as "Jkkomk" match too);
  italics become `*...*` with no space inside the markers.
- **Cleanup:** a word broken at the line end is joined when the whole word occurs elsewhere in the
  eight volumes at least as often as the two halves side by side; known OCR slips are replaced as
  whole words (`SLIPS`: "Csesar", "Cajsar", "C&sar" and "Caesar" are "Cæsar", "Judsea" "Judæa",
  "thai" "that", "discemer" "discerner"; `MARGIN_SLIPS`: "Horn." "Hom."); the space before ";:?!,."
  goes. Everything else is the checker's: in the five sections checked while planning, every
  section needed margin corrections, and each had a few word slips ("WJioso", "soiil", "bom").

The tool's tests (`backend/tests/test_catena_import.py`) cover the parts that decide what text comes
out (the margins, the kinds of line, the sections, the labels, the joining, the cleanup, the
index), on small invented pages, and check that no checked text carries a slip the tool knows.

## Checking a section **[proposed]**

A section is checked by comparing its cleaned draft with the page images, word by word, and
correcting the draft to the page. The checklist is `backend/data/catena/README.md`:
1. `fetch` and `draft` once; `checkout` the section for its file to correct and its page image
   addresses.
2. Each page image in bands of about a quarter of the page at 1500 px wide (the full scan is about
   2000 x 3300 px), with a zoom on every doubtful mark.
3. Every comment: the label as printed and the father it names; the margin reference beside it and
   any other margin note; the text word by word (the OCR's usual slips: "rn" read as "m", "ii" as
   "u", "æ" as "se" or "&", a dropped or added comma, a margin note's letters in the line, two words
   joined or a word left in halves); the italics' start and end; paragraph breaks inside one
   father's comment; Aquinas's linking words as an item of their own.
4. The section's first and last verse and its printed pages.
5. The volume's printed errata (the README's table): any that touch the section are applied and
   listed.
6. `checked: {"on": <date>, "by": <who>, "word by word against the page images"}` (never an email
   address), then `index --checked`.
7. A second reader checks the section again against the page images before it merges.
8. The section's id into the data test's `CHECKED` and its count into `QUOTATIONS`; the page image
   addresses in the commit message.

V1's checks (Matthew 22:15-22, 22:34-40, 22:41-46, 23:1-4, 23:5-12) are recorded in the plan: the
page images used, what the first reading corrected, and a second, independent reading of all 92
quotations (it found one more slip, a comma the margin left in Matthew 23:3). The first took about
3-6 minutes a printed page.

## The API **[proposed]**

`GET /voices?reference=Matthew%2022:15-22`

- **Who:** any signed-in user, like `GET /lectionary/readings` and `GET /translations`: the
  Catena is global reference data, so the route depends on `get_current_user`, never on
  `require_church`, and ignores `X-Church-Id` (F §1.2; `test_route_guards.USER_SCOPED`)
  (question 7).
- **Reference:** at most 200 characters (as a scripture line); read with the app's own parser
  (`scripture_refs.parse_refs`, the hymn matcher's, after `normalize_for_fetch`), so "Matthew
  22:15-22", "Matt 22:15-22", "Luke 15:1-3, 11b-32" and "John 20:19-31" all work, and the
  lectionary's optional verses in parentheses count as read ("Luke 2:1-14 (15-20)", "Luke 2:(1-7)
  8-20", "John 1:(1-9) 10-18"); the passages of the first alternative that names a Gospel count
  ("Matthew 26:14-27:66 or Matthew 27:11-54" is Matthew 26:14-27:66). Not a Gospel passage: a 422
  naming `reference`, "Choose a passage from Matthew, Mark, Luke or John.".
- **Answer:** `200 VoicesOut`:
  ```
  {reference, gospel, quotation_count, credit,
   sections: [{id, reference, pages, volume, scan_url, status,
               comments: [{label, father, work, text, notes, printed_label}]}]}
  ```
  The sections sharing at least one verse with the passages, in order; an unchecked section has
  `status: "unchecked"` and no comments; `quotation_count` counts the fathers' checked comments
  (Aquinas's linking words, `label` and `father` null, are not a quotation); `pages`
  is "748-752", `volume` "Vol. I, St. Matthew, Part III (1842)", `scan_url` the viewer at the
  section's first page; `credit` names the source (below). A
  whole chapter ("Matthew 22") gives every section of the chapter.
- **Cost and limits:** no AI, no database, no upstream call: the file is read once and kept. No
  rate-limit bucket (as `GET /translations`); the answer is small. `Cache-Control: private,
  max-age=3600`: the text changes only with a deploy. With TanStack Query's own hour on top, a
  newly checked section can take up to about two hours after its deploy to show on a page already
  open, which is harmless.
- **Errors:** 401 (signed out), 422 (no reference, too long, not a Gospel), 503 (as every route).

### The credit **[proposed]** (question 2)

Under the open panel, built by the server from the volumes of the sections shown:

> From the Catena Aurea of Thomas Aquinas, vol. I, St. Matthew, translated by Mark Pattison,
> edited by John Henry Newman (Oxford: John Henry Parker, 1841-42). Scanned from the University
> of Toronto's copy at archive.org.

Mark: "vol. II, St. Mark, translated by John Dobree Dalgairns, … 1842"; Luke: "vol. III, St. Luke,
translated by Thomas Dudley Ryder, … 1843"; John: "vol. IV, St. John, translator not named in the
volume, … 1845"; for Matthew 11-21 "Saint Mary's College of California's copy".
Not CCEL, and not CCEL's catalogue error "William Whiston" (rights check §2).

## Which Gospel passage the panel shows **[decided: planning answer 1]**, worked out **[proposed]**

On the client (`frontend/src/lib/voices.ts`), from what step 1 already has:
1. **A chosen reading from a Gospel wins:** the bulletin's two readings as step 1 resolves them
   (`effectivePicks`: the picked or automatic New Testament reading, then the Old Testament
   one); the first whose first alternative is in Matthew, Mark, Luke or John gives the passage
   (that alternative: "Mark 1:1-8 or Luke 3:1-6" asks for Mark 1:1-8).
2. **Else the Sunday's lectionary Gospel:** the lectionary answer step 1 already holds for the
   draft's date (`useLectionaryLookup`, `GET /lectionary/readings`; the server's
   `vanderbilt_lectionary` merged with Lectio), its reading set the draft uses (`selectedSetIndex`,
   or the default one); the first line whose first alternative is a Gospel. The panel says "From the Gospel for
   this Sunday: Matthew 22:15-22".
3. **Else no panel** (no date, no lectionary answer yet, another date's, none for the date, or a
   set with no Gospel).

A line counts as a Gospel passage only when it names at least a chapter and reads whole ("John
3:16-21", "John 3", "Luke 2:(1-7) 8-20"); a whole book ("John") or a line half typed ("John 3:",
"John 3:16-") is none, so typing never asks for a whole book or a reference the server cannot
read. The passage trails the scripture lines by 600 ms (the list's rows trail them by 400 ms), so
typing a Gospel line asks once, when typing stops.

On the client because the lectionary answer is already loaded there (no second lookup on the
server, and the server stays a plain text lookup), and because it must follow the picks as they
change without a request. For October 18, 2026 the lectionary lines are Isaiah 45:1-7, Psalm
96:1-9 (10-13), 1 Thessalonians 1:1-10, Matthew 22:15-22: the automatic readings are Isaiah and
1 Thessalonians, so the panel shows "From the Gospel for this Sunday: Matthew 22:15-22"; picking
Matthew 22:15-22 as the New Testament reading shows it as the chosen reading.

## The panel **[proposed]** (question 5)

Where: in the **Readings** list of step 1, under the row of the passage's line (after the list
when that line is not one of the rows, for example typed lines without the lectionary's Gospel).

Closed (the default; it stays as the member leaves it while step 1 is open, and is closed again
when the step opens anew):
- A full-width button, 44 px or taller: **Voices of the Church**, then "19 quotations on these
  verses" (one: "1 quotation on these verses"; none checked: "Not yet transcribed for this
  passage."; while loading "Loading the fathers' comments…"; after a failure "The fathers'
  comments couldn't be loaded."); `aria-expanded` and `aria-controls` from the kit's
  `Collapsible`. Under the lectionary rule, the line above it says "From the Gospel for this
  Sunday: Matthew 22:15-22".

Open:
- For each section, in verse order: its verses as a heading ("Matthew 22:15-22") and a link
  "Printed pages 748-752, Vol. I, St. Matthew, Part III (1842)" to the scan's viewer at its first
  page, in a new tab (44 px tall on phones; "(opens in a new tab)" for screen readers).
- A checked section: its quotations as a list, each headed by the father's name ("Chrysostom",
  "The Gloss") and the margin reference after it ("Chrys. Hom. lxx."), the text in 16 px with
  relaxed line height, the italics as `<em>`, printed paragraphs as paragraphs, and "In the
  margin: 1 Tim. 4, 3." for other margin notes (two notes side by side, each with its own stop:
  "In the margin: ¹ alia re frui. ² al. bonum."). A corrected speaker adds "Corrected by the
  volume's errata: printed as JEROME" under the name. Aquinas's linking words are an item headed
  "Aquinas, linking the comments", in muted text. No raw HTML.
- An unchecked section: "Not yet transcribed for this passage."
- The credit, last.
- A failure: the message and **Try again** (for screen readers "Try again: Voices of the Church").
  A 422 (a line the server cannot read as a Gospel passage) is not a failure to retry: no panel.
- At 375 px the text wraps and nothing scrolls sideways.

The panel asks the server when step 1 shows a Gospel passage (the count needs it), once per
passage once typing stops, and keeps the answer an hour. No user-facing copy of the app's has an em dash (the
Catena's own text keeps the printing's).

## Privacy, cost, rate limits

Static public-domain text: no church data, no personal data, no AI. No log line of the app's
carries the reference or the text; uvicorn's access log records each request's line (`GET
/voices?reference=Matthew%2022:15-22`), as it does for every route, which is harmless (public
data). No new bucket. Memory: four small files at most. The import tool ships in the Railway image
with the rest of `backend/` (about 40 KB), but nothing there runs or imports it.

## Testing (V1)

- `test_catena.py`: the format checks (each break a `CatenaDataError`: twenty-four kinds, the
  section keys, a verse past its chapter, three chapters, pages backwards and an email address
  among them), a printed paragraph and a second section on the same verses, Aquinas's linking
  words and a corrected speaker, a section across chapters, `sections_for` (overlap, shared verses,
  a whole chapter, two spans, another book), the Gospel of a reference and the first alternative,
  the lectionary's optional verses in parentheses (five lines), the credit, the scan addresses.
- `test_catena_data.py`: the four shipped files load with their section counts and exactly the
  checked sections, with their quotation counts; every verse of each Gospel in a section, none past
  its chapter, no section over two chapters, one leaf-to-page distance a volume and the leaves in
  order; one line a section and no key a draft adds; Matthew 22:15-22 pinned (labels, margin
  references, first and last words, printed spellings, no slips); the Sundays through November 1
  checked, the comma of Matthew 23:3 gone; the linking words on 22:40 under no father; a stop after
  italics inside them; every Gospel line of the recorded lectionaries finds its sections.
- `test_catena_import.py`: the tool on invented pages (margins and a left note's stop in the
  gutter, running heads and a misread page number, sections, chapters and a misread verse 1,
  joining, cleanup, italics, labels, comments with their references, notes and paragraphs, a page
  signature, the index, the gaps filled and the file's layout, `main index --checked`, `checkout`),
  and no checked text with a known slip.
- `test_api_voices.py`: 401; Matthew 22:15-22 as printed with the cache header and `X-Church-Id`
  ignored; the linking words under no father and not counted; an unchecked section; another
  Gospel; the 422s. `test_route_guards.py` lists the route
  as user-scoped; `test_no_streamlit_in_core.py` the two pure modules.
- Frontend: `voices.test.ts` (which passage; optional verses, a whole book and a half-typed line),
  `queries/voices.test.tsx` (the request, the key, an hour), `voices-panel.test.tsx` (closed with
  the count and 44 px; open with the quotations, the link, the italics, the paragraphs, the margin
  and the credit; the linking words, an erratum's note, two margin notes; unchecked; nothing
  checked; the lectionary label; loading, failure and Try again; no panel on a 422),
  `readings-step.test.tsx` (under the Gospel's row and the label going when the Gospel is picked;
  after the list; one request when typing stops; no panel without a Gospel).

## Risks

- **The tool's split is a heuristic.** A section's verses can be off where the OCR missed a verse
  number or a heading (the warnings above). It matters only for unchecked sections (a heading that
  says "Not yet transcribed" for slightly wrong verses); a checker corrects a section's verses
  when checking it, and `index` keeps the checked section.
- **Checking is slow.** About 3-6 minutes a printed page for a careful check; a Sunday's Gospel
  is 3-10 pages (V1's five sections were 26 pages). V1 checks the Sundays through November 1; the
  rest is "Not yet transcribed" until checked.
- **The margin references are the hardest part.** The OCR mixes them into the line or loses their
  second line; every section checked so far needed margin corrections.
- **A checker's mistake.** The check is by eye. The checklist, a second reader's full pass (V1's
  found one comma the first had missed) and the owner's phone check reduce it.
- **archive.org's addresses** (the page images and the viewer) could change; the panel's link is
  a convenience, and the text does not depend on it.
- **Matthew Part II** is a different library's copy whose OCR is poorer (no small capitals, more
  slips): checking there takes longer.

## V2: "Bring this into the liturgy" and the "after {Name}" credit (designed here; built later)

**[decided: answers 1(3), 3, 8; planning answers 5, 6]**

- **On a quotation** (in the open panel), **Bring this into the liturgy** opens a choice of one
  prayer card (the liturgy step's cards that hold text: Call to Worship, Prayer of Confession,
  ...). The AI rewrites that card, weaving in the quotation's image or phrase, with **Undo**,
  like Revise (`POST /liturgy/revise`); the reviewer's model.
- **API:** `POST /liturgy/weave` (church-scoped, the `ai` bucket, as `/liturgy/revise`):
  `{section, text, quotation: {section_id, index}, occasion, scriptures}` → `{text}`. The server
  reads the quotation from the data file by its id and place (never text sent by the page), and
  only a checked one with a father: Aquinas's linking words (`father` null) are never offered and
  never credited. The prompt asks for the image or phrase woven into the card's own words,
  never words put in the father's mouth that are not in the quotation, and no quotation marks
  around invented words.
- **The credit:** the card gains `after: {father, section_id, index} | null` (draft v5,
  `ServiceDraft` and the saved service's liturgy JSON; no migration, the liturgy is JSON). On
  the card it is a removable chip "after Chrysostom" that stays through later edits until
  removed. The printed bulletin and both Word copies print "after Chrysostom" in small type under
  that prayer. "the Gloss" reads "after the Gloss"; "a Greek expositor" "after a Greek
  expositor".
- **Open for V2's plan:** the cards offered; whether a woven card may carry two credits; the
  credit's type size in the printed bulletin; Undo after a save.

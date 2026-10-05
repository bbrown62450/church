# The Catena Aurea's text (Voices of the Church)

One file per Gospel: `matthew.json`, `mark.json`, `luke.json`, `john.json`. The text of record is
the 1841-45 Oxford printing (John Henry Parker), as scanned at archive.org (owner's source
decision, 2026-10-05; `docs/superpowers/specs/2026-10-05-voices-rights-check.md`). The format is
`backend/catena.py`'s (checked when a file loads, by `index`, and by
`backend/tests/test_catena_data.py`), and the design is
`docs/superpowers/specs/2026-10-05-voices-of-the-church-design.md`.

Every section of the Catena is listed with its verses, volume, printed pages and scan pages. Only a
section someone has **checked against the page images** has text (`"status": "checked"`); the app
shows "Not yet transcribed for this passage." for the others. Never commit unchecked text: a
draft's `footnotes` and `warnings` are raw OCR, and the format check refuses any section key but
`id`, `start`, `end`, `volume`, `pages`, `leaves`, `status` and, when checked, `checked`,
`comments` and `errata`.

A section's verses run to the verse before the next section (`index` fills a gap the OCR left
where it missed a verse number), and its printed pages follow its scan leaves (one distance
between them in each volume; `test_catena_data.py` checks both).

## Checking a section

1. Get the OCR of the eight volumes and the drafts (once; the cache is any directory outside the
   repo, about 100 MB):
   `.venv/bin/python backend/scripts/catena_import.py fetch --cache ~/catena-cache`, then
   `.venv/bin/python backend/scripts/catena_import.py draft --cache ~/catena-cache Matthew`
   (about a minute and a half a Gospel).
2. `.venv/bin/python backend/scripts/catena_import.py checkout --cache ~/catena-cache "Matthew 22:34-40" --out ~/catena-check`
   writes each section of the passage to check as `~/catena-check/<id>.json`, with only the keys
   the data file allows, and prints the addresses of its page images
   (`https://archive.org/download/<item>/page/n<leaf>.jpg`). `show` prints the whole draft,
   footnotes and warnings included, for reference only.
3. Open each page image at a size where the italics and the small letters are clear (a band of
   about a quarter of the page, 1500 px wide; zoom on any doubtful mark). For each comment, against
   the page:
   - the label as printed ("Pseudo-Chrys.", "Jerome;"), the father it names (`father`, one of
     `catena.FATHERS`; "Id." is the father before it);
   - the margin reference beside the label (`work`, as printed: "Chrys. Hom. lxx."), and any other
     margin note beside the comment (`notes`: "1 Tim. 4, 3."), each with its own stop; a note's
     punctuation is never the text's ("Acts 15, / 19." beside "the Apostles / in the Acts");
   - the text, word by word: spelling, capitals and punctuation as printed; "æ" where printed;
     a word the line end broke joined (the hyphen kept only where the word is hyphenated anyway,
     "first-fruits"); no space before ";", ":", "?", "!"; straight quotes;
   - the italics, `*...*`, starting and ending where the printing's do. A stop right after italic
     words goes inside them ("*Master,*"): the printing sets it in italic wherever the scan shows
     the difference, and a scan cannot tell an italic comma or full stop from a roman one; a stop
     the page shows roman stays outside ("*they will not*;");
   - a printed paragraph break inside one father's comment as a blank line (`\n\n`);
   - Aquinas's own words linking the comments, printed as a paragraph of their own ("It follows,
     *On these two commandments hang all the Law and the Prophets.*"), as an item of their own
     with `"label": null, "father": null, "work": null`: they are no father's;
   - the OCR's usual slips: "rn" read as "m" ("discemer"), "ii" as "u", "æ" as "se" or "&", a
     dropped or added comma, a margin note's letters or stops mixed into the text, two words joined
     or a word left in two halves.
4. Check the section's first and last verse and its printed pages against the page.
5. Check the volume's printed errata (the table below). The errata are the printers' own
   corrections and part of the printing. Where one touches the section (a page and line in it),
   apply it: a corrected word in the text; a corrected speaker in `label` and `father`, with the
   label as printed in `printed_label` ("JEROME"), so the panel says "Corrected by the volume's
   errata: printed as JEROME". List each erratum applied, as printed, in the section's `errata`.
6. Set `"checked": {"on": "<YYYY-MM-DD>", "by": "<who>, word by word against the page images"}`
   (a role, never an email address), then
   `.venv/bin/python backend/scripts/catena_import.py index --cache ~/catena-cache Matthew --checked ~/catena-check/<id>.json`
   (it refuses a file that breaks the format, the placeholder date included).
7. A second reader checks the section again, against the page images and not the first reader's
   notes, before it is merged; record both in the commit message.
8. Add the section's id to `CHECKED` and its count of the fathers' comments (not the linking
   words) to `QUOTATIONS` in `backend/tests/test_catena_data.py`, run
   `.venv/bin/python -m pytest -q backend/tests/test_catena.py backend/tests/test_catena_data.py backend/tests/test_catena_import.py backend/tests/test_api_voices.py`,
   and commit with the page image addresses in the message.

An OCR slip that recurs goes into `SLIPS` (or `MARGIN_SLIPS`) in `backend/scripts/catena_import.py`,
so later drafts have it right.

## The printed errata

Found by searching each volume's OCR for "ERRATA"/"ERRATUM" (2026-10-05). A scan can lack an
errata slip, so look at the volume's first and last leaves too.

| Volume (archive.org item) | Errata leaf | What they correct |
|---|---|---|
| Vol. I, St. Matthew, Part I (`catenaaureacomme00thomuoft`) | n23 | one erratum, a footnote on p. 96 |
| Vol. I, St. Matthew, Part II (`a6788682p201thomuoft`) | none found | |
| Vol. I, St. Matthew, Part III (`catenaurecommpt301thomuoft`) | none found | |
| Vol. II, St. Mark (`catenaaureacomme02thomuoft`) | n11 | one erratum, a footnote on p. 184 |
| Vol. III, St. Luke, Part I (`catenaaureacomme03thomuoft`) | n19 | speakers ("Page 25. line 1. for JEROME read PSEUDO-JEROME", "for GREG. NAZ. read GREG. NYSS.") and words |
| Vol. III, St. Luke, Part II (`p2catenaaureacom03thomuoft`) | n420, n422 | "Errata, Part I" and "Errata, Part II": words ("for heavenly read worldly", "for he read He"), about 45 in all |
| Vol. IV, St. John, Parts I and II | none found | |

The import tool is a developer's tool: it ships in the Railway image with the rest of `backend/`
but nothing runs or imports it there.

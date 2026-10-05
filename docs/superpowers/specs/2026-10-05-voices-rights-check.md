# Voices of the Church: rights check for the Catena Aurea (1841-45 Oxford translation)

Status: research only. No text has entered the app. Checked 2026-10-05 from the
session with curl through the session proxy. Raw pages are saved in the session
scratchpad (`scratchpad/voices/`), not in the repo.

Owner rule being applied (decisions doc, 2026-10-01 and 2026-10-05): "verify the
translation's public-domain status, with cited sources, before any text enters
the app"; "if the rights check finds anything uncertain, stop and bring it to
the owner".

Legend: **[read]** = quoted from the page at the URL. **[inferred]** = my
reasoning, not stated by a source. Nothing here is legal advice.

## Verdict: YELLOW

The 1841-45 English text itself is in the public domain in the US and the UK.
That part is GREEN.

What is uncertain is the **source we would copy it from**:

1. **CCEL**, the cleanest digital text, has only **Matthew and Mark** (no Luke,
   no John), and its copyright page says its books "may be used for personal,
   educational, or non-profit purposes" and asks people to "Contact us for
   permission to republish CCEL works or to use them commercially". Shipping
   CCEL's text in the app's data file is arguably "republishing".
2. For **Luke and John** there is no clean transcription with clear terms. The
   options are the archive.org OCR of the 1841-45 printing (public domain, but
   noisy: marginal references and OCR errors are mixed into the text) or
   isidore.co (no license statement, unknown provenance).
3. CCEL's text is close to, but **not exactly, "as printed"** (decision 4): a
   few spellings and words differ from the 1842 page, and the printed margin
   references are folded into the speaker label.

So the owner needs to decide the source (see "What the owner must decide").

## 1. Publication facts of the English translation

| Volume | Gospel | Title-page year | Translator named in the volume | Evidence |
|---|---|---|---|---|
| I, Parts I-III | Matthew | Part I MDCCCXLI (1841); Part III MDCCCXLII (1842) | Rev. Mark Pattison, M.A., Fellow of Lincoln College | archive.org scans below |
| II | Mark | MDCCCXLII (1842) | John Dobree Dalgairns, M.A., of Exeter College | archive.org |
| III, Parts I-II | Luke | MDCCCXLIII (1843) | Thomas Dudley Ryder, M.A., of Oriel College | archive.org |
| IV, Parts I-II | John | MDCCCXLV (1845) | not named in Part I (no preface found) | archive.org |

Imprint on every title page **[read]**: "OXFORD, JOHN HENRY PARKER; J. G. F. AND
J. RIVINGTON, LONDON." Printer: "BAXTER, PRINTER, OXFORD."

- Matthew Part I, `catenaaureacomme00thomuoft`: title page "VOL. I. ST. MATTHEW.
  PART I. ... MDCCCXLI."; preface ends "the Editors are indebted for the
  Translation of St. Matthew, as well as for the above introductory remarks, to
  the Rev. MARK PATTISON, M.A. Fellow of Lincoln College. J. H. N." **[read]**
  https://archive.org/download/catenaaureacomme00thomuoft/catenaaureacomme00thomuoft_djvu.txt
- Matthew Part III, `catenaurecommpt301thomuoft`: "VOL. I. ST. MATTHEW. PART III.
  ... MDCCCXUI." (OCR of MDCCCXLII; the item's metadata says "stated date is
  1842") **[read]**
  https://archive.org/download/catenaurecommpt301thomuoft/catenaurecommpt301thomuoft_djvu.txt
- Mark, `catenaaureacomme02thomuoft`: "VOL. II. ST. MARK. ... MDCCCXLII." and
  "For the translation of the Volume now presented to the reader, the Editors
  have to make their acknowledgments to JOHN DOBREE DALGAIRNS, M. A. of Exeter
  College. J. H. N." **[read]**
  https://archive.org/download/catenaaureacomme02thomuoft/catenaaureacomme02thomuoft_djvu.txt
- Luke, `catenaaureacomme03thomuoft`: "VOL. III. PART I. ST. LUKE. ...
  MDCCCXLIII." and "These introductory remarks have been supplied by the friend,
  who has translated the portion ... THOMAS DUDLEY RYDER, M. A. of Oriel
  College. J. H. N." **[read]**
  https://archive.org/download/catenaaureacomme03thomuoft/catenaaureacomme03thomuoft_djvu.txt
- John, `catenaaureacomme04thomuoft`: "VOL. IV, PART 1. ST. JOHN. ...
  MDCCCXLV." The OCR goes from the Advertisement straight into "CHAP. I." with
  no preface or translator credit **[read]**; the John translator is therefore
  not named in this copy **[inferred: may be named elsewhere; it does not change
  the rights result, since the text is 180 years old]**.
  https://archive.org/download/catenaaureacomme04thomuoft/catenaaureacomme04thomuoft_djvu.txt
- Editor: the prefaces are signed "J. H. N." **[read, above]**; HathiTrust's
  catalog: "Preface signed: J. H. N. (John Henry Newman)" **[read]**
  https://catalog.hathitrust.org/api/volumes/full/recordnumber/008977221.json

**"Library of the Fathers"?** Not formally. The Advertisement in every volume
**[read]**: "THE following Compilation not being admissible into the Library of
the Fathers from the date of some few of the authors introduced into it, the
Editors of the latter work have been led to publish it in a separate form ...
Oxford, May 6, 1841." So it is a companion to the Library of the Fathers, by its
editors, published separately.

**Source text translated** **[read, Matthew preface]**: "The Translation has been
made from the Venetian edition of 1775".

**HathiTrust record of the first edition** **[read]**: "260 Oxford, John Henry
Parker; London, Rivington, 1841-45." / "505 v.1. St. Matthew. 3 pts.--v.2. St.
Mark.--v.3. St. Luke. 2 pts.--v.4. St. John. 2 pts." Items (Princeton, Harvard)
all `rightsCode: pd`, "Full view", for example `hvd.ah3vj8` (v.1 pt.1).
https://catalog.hathitrust.org/api/volumes/full/recordnumber/008977221.json
(record page: https://catalog.hathitrust.org/Record/008977221; HathiTrust's
HTML pages are behind a bot check from this session, the JSON API is not.)

### Later editions and whether they add copyrighted material

| Edition | What it is | Rights | Source |
|---|---|---|---|
| 1864, Oxford: J.H. and J. Parker | reprint | public domain (pre-1931) | archive.org search, e.g. `p1catenaaureaco01thom` https://archive.org/advancedsearch.php?q=title%3A%28catena+aurea%29&fl%5B%5D=identifier&fl%5B%5D=date&fl%5B%5D=publisher&rows=200&output=json |
| 1870 / 1874 "New ed.", Oxford: J. Parker (6 vols.) | reset edition, "[preface by John Henry Newman ; translation by Mark Pattison]" **[read]** | HathiTrust `pd` | https://catalog.hathitrust.org/api/volumes/full/recordnumber/008412369.json |
| 1997, Southampton: Saint Austin Press | reprint "with a new introduction by Aidan Nichols"; note "English translation first published in 1841 edited by John Henry Newman." **[read]** | HathiTrust `ic` (in copyright), "Limited (search-only)" **[read]** | https://catalog.hathitrust.org/api/volumes/full/recordnumber/003993465.json |
| 2005 Wipf & Stock (8 vols.), 2013 Baronius Press, Cosimo, and many print-on-demand reprints | reprints | the 1841-45 text inside stays public domain; their introductions, typesetting and any new notes are theirs **[inferred]** | archive.org search above; Open Library https://openlibrary.org/search.json?q=catena+aurea+commentary+four+gospels ; Wikipedia (pointer only) "this edition was republished by the Baronius Press in 2013" https://en.wikipedia.org/wiki/Catena_aurea |

The only modern copyrighted additions found are the reprint introductions
(Aidan Nichols, 1997) and the reprints' own layout. **None of the candidate
sources below is based on a modern reprint**: CCEL's page breaks and footnotes
match the 1842 Parker printing page for page (section 4). **[read + inferred]**

## 2. Copyright status

**United States: public domain.** Cornell's chart, "Works First Published
Outside the U.S. ... Date of Publication: Before 1931 ... In the public domain"
**[read]** https://guides.library.cornell.edu/copyright/publicdomain . The
volumes were published in Oxford in 1841, 1842, 1843 and 1845 (title pages
above). The archive.org items carry `possible-copyright-status:
NOT_IN_COPYRIGHT`, e.g. Matthew Part III: "Evidence reported by
scanner-Liz-Ridolfo ... no visible notice of copyright; stated date is 1842."
**[read]** https://archive.org/metadata/catenaurecommpt301thomuoft . HathiTrust
marks every first-edition volume `pd` (above). The app's users and the owner's
church (Indiana) are in the US, so this is the status that governs.

**United Kingdom: public domain (completeness).** UK term is life of the author
plus 70 years **[inferred: general rule, not fetched]**. Deaths:

- John Henry Newman, editor: "(1801-1890)" **[read]** https://en.wikipedia.org/wiki/John_Henry_Newman
- Mark Pattison, Matthew: "(1813-1884)" **[read]** https://en.wikipedia.org/wiki/Mark_Pattison
- John Dobree Dalgairns, Mark: "(21 October 1818 - 6 April 1876)" **[read]** https://en.wikipedia.org/wiki/John_Dobree_Dalgairns
- Thomas Dudley Ryder, Luke: "Ryder, Thomas Dudley, 5s. Henry, of Lutterworth,
  bishop of Lichfield and Coventry. Oriel Coll., matric. 21 March, 1833, aged
  17 ... died 23 Jan., 1886." **[read]** https://en.wikisource.org/wiki/Alumni_Oxonienses:_the_Members_of_the_University_of_Oxford,_1715-1886/Ryder,_Thomas_Dudley
- John translator unnamed; even as an anonymous work published 1845 it expired
  long ago **[inferred]**.

Note on the "Whiston" credit: CCEL's metadata names "William Whiston" as
translator **[read]** (catena1.xml `<comments>(tr. William Whiston)</comments>`).
That is a CCEL cataloguing error: Whiston (d. 1752) translated Josephus; the
volumes themselves credit Pattison and Dalgairns. **[read + inferred]** The app's
credit line should not copy CCEL's metadata.

## 3. Candidate digital sources and their terms

### CCEL (ccel.org)

- Hosts **only Matthew (`catena1`) and Mark (`catena2`)**. `catena3` and
  `catena4` return 404 (HTML, XML and TXT) **[read]**. The author page lists
  "Catena Aurea - Gospel of Matthew" and "Catena Aurea - Gospel of Mark" and no
  Luke or John **[read]** https://www.ccel.org/ccel/aquinas . (The 2026-10-05
  decisions note said "catena1-4"; that is not the case.)
- Work pages: https://www.ccel.org/ccel/aquinas/catena1.html and
  https://www.ccel.org/ccel/aquinas/catena2.html . No rights line on the page;
  footer links to "Copyright" **[read]**.
- ThML metadata (https://www.ccel.org/ccel/a/aquinas/catena1.xml and
  .../catena2.xml) **[read]**:
  - `<!-- Copyright Christian Classics Ethereal Library -->`
  - `<published>London: J.G.F. and J. Rivington, 1842</published>`
  - `<DC.Date sub="Created">2000-07-09</DC.Date>`
  - `<DC.Rights />` (empty)
  - `<DC.Source />` (empty)
- Plain-text edition header (https://www.ccel.org/ccel/a/aquinas/catena1/cache/catena1.txt)
  **[read]**: "Print Basis: London: J.G.F. and J. Rivington, 1842". No rights
  line.
- CCEL copyright policy, https://www.ccel.org/about/copyright.html **[read, in full]**:
  > CCEL.org website and special contents copyright 1993-2020 Harry Plantinga.
  > Most of the editions at the Christian Classics Ethereal library are based on
  > books that are public domain in the United States. However, they may have
  > copyrighted introductions, cover art, and other special contents. A few
  > books are under another publisher's copyright and are used by permission;
  > these are noted on the book information page. These books may be used for
  > personal, educational, or non-profit purposes. Contact us for permission to
  > republish CCEL works or to use them commercially.
- Which source edition: the 1841-42 Parker/Rivington printing. CCEL's `<pb n="749">`
  through `n="752"` for Matt 22:15-22 match the printed page numbers in the
  archive.org scan of Matthew Part III (1842), and CCEL's "[ed. note: ...]"
  texts are the printed footnotes (e.g. "It seems to be the general witness of
  antiquity that there was a Hebrew copy of St. Matthew's Gospel" appears in the
  1841 Part I OCR) **[read]**. The "Imprint" credits Rivington (London) only; the
  title page reads Parker, Oxford, with Rivington, London **[read]**.
- Assessment **[inferred]**: the words are public domain; CCEL contributes
  transcription, markup and its catalog text. A faithful transcription of a
  public-domain text is generally not a new copyrightable work in the US, but
  CCEL's page states usage terms, and shipping its text in our data file is the
  kind of "republish" use it asks to be contacted about. Whether this church
  app counts as "non-profit" use is for the owner. This is the main uncertainty.

### archive.org scans of the 1841-45 printing (University of Toronto copies)

Item metadata via `https://archive.org/metadata/<id>`; OCR via
`https://archive.org/download/<id>/<id>_djvu.txt` (all available, HTTP 200).

| Identifier | Volume | Stated date | possible-copyright-status |
|---|---|---|---|
| `catenaaureacomme00thomuoft` | Matthew Part I | 1841 | NOT_IN_COPYRIGHT |
| `a6788682p201thomuoft` | Matthew Part II (Saint Mary's College of California copy) | 1841 | not set |
| `catenaurecommpt301thomuoft` | Matthew Part III | 1842 | NOT_IN_COPYRIGHT |
| `catenaaureacomme01thomuoft` | Matthew Part III (another copy; metadata "stated date is 1852" but the OCR title page reads MDCCCXLII) | 1842 | NOT_IN_COPYRIGHT |
| `catenaaureacomme02thomuoft` | Mark | 1842 | NOT_IN_COPYRIGHT |
| `catenaaureacomme03thomuoft` | Luke Part I | 1843 | NOT_IN_COPYRIGHT |
| `p2catenaaureacom03thomuoft` | Luke Part II | 1843 | NOT_IN_COPYRIGHT |
| `catenaaureacomme04thomuoft` | John Part I | 1845 | NOT_IN_COPYRIGHT |
| `p2catenaaureacom04thomuoft` | John Part II | 1845 | NOT_IN_COPYRIGHT |

(`p1catenaaureaco04thomuoft` is another copy of John Part I.) The `rights`
field is empty on all of them **[read]**. The archive.org terms-of-use page is
rendered by JavaScript and could not be read from the session
(https://archive.org/about/terms.php returned a 1.8 KB shell) **[unverified]**.

OCR quality on Matt 22:15-22 (Matthew Part III, pp. 748-752): the words are
mostly right, but the margin references are interleaved into the running text,
for example "Chrys.  worship  of  God.  CHRYS.  They  send ... Horn.  Herod's"
and "Gloss,  for  disciples.  GLOSS.  There  are ... non  occ- possible", and
there are OCR slips such as "Csesar", "Cajsar", "C&sar", "discemer", "thai",
"(o virtue" **[read]**. Usable as a base, but each passage needs hand
correction against the page images before it is "exactly as printed".

HathiTrust has full-view `pd` scans of the same edition (Princeton v.1 and v.2;
Harvard v.1 pt.1-2, v.3 pt.1-2, v.4 pt.1-2; Columbia v.1 pt.2, v.3, v.4) as a
second scan source **[read]**
https://catalog.hathitrust.org/api/volumes/brief/oclc/3427671.json and
https://catalog.hathitrust.org/api/volumes/brief/oclc/224217324.json .

### Other transcriptions

- **isidore.co** (Fr. Joseph Kenny, O.P.'s Aquinas collection, mirrored at
  https://github.com/Geremia/AquinasOperaOmnia): has all four Gospels in English
  (https://isidore.co/aquinas/english/CAMatthew.htm , CAMark.htm, CALuke.htm,
  CAJohn.htm). Its Matthew is visibly derived from CCEL's text (same
  "Then went the Pharisees; went" quotation slip, same "Cesar") **[read]**; its
  header credits "translated by John Henry Parker" (the publisher, an error)
  **[read]**. No license or copyright statement on the index page, and the
  GitHub mirror has no LICENSE file (raw LICENSE 404; README says "This
  repository is a mirror of http://dhspriory.org/thomas/") **[read]**
  https://raw.githubusercontent.com/Geremia/AquinasOperaOmnia/master/README.md .
  Provenance of the Luke and John texts is not stated. Not recommended as a
  shipped source.
- **dhspriory.org**: https://dhspriory.org/thomas/CAMatthew.htm returned 404.
- **ecatholic2000.com/catena/**: all four Gospels, but the footer reads
  "Copyright ©1999-2026 Wildfire Fellowship, Inc all rights reserved" **[read]**
  https://www.ecatholic2000.com/catena/ . Not recommended.
- **Wikisource**: no transcription; a search for "Catena Aurea" finds only
  encyclopedia articles **[read]**
  https://en.wikisource.org/w/index.php?search=Catena+Aurea&ns0=1&ns104=1 .
- **New Advent** fathers index (https://www.newadvent.org/fathers/) is the
  Schaff series, out of scope (owner answer 2).

## 4. Matthew 22:15-22 in the sources (test Sunday, October 18, 2026)

**Present in CCEL** at https://ccel.org/ccel/aquinas/catena1/catena1.ii.xxii.html
(ThML: `catena1.xml` lines ~23602-23766, div `ii.xxii` "Chapter 22").

Structure **[read]**:

- The Catena comments on **sections, not single verses**. Verses 15-22 are
  printed together first (page header "VER. 15-22" in the 1842 printing), then
  the fathers' comments on the whole section follow.
- In CCEL each verse is `<p class="scripture" ...>15. Then went the Pharisees
  ...</p>` (number prefix "15.", sometimes "Ver. 1." or a range like "3-6.").
  Sections are separated by `<hr style="width:25%" />`. Only the chapter has an
  OSIS marker: `<scripCom osisRef="Bible:Matt.22" .../>`. Verse text quoted
  inside comments is plain quotation marks.
- Each comment is `<p class="normal">` (the first may lack the class) beginning
  with an attribution and a colon: `Pseudo-Chrys.:`, `Gloss. ord.:`, `Jerome:`,
  `Chrys., Hom. lxx:`, `Gloss., non occ.:`, `Chrys.:`, `Hilary:`, `Origen:`.
  A paragraph without a label continues the previous speaker.
- Matt 22:15-22 has 28 comment paragraphs, 19 with an attribution: Jerome 6,
  Pseudo-Chrys. 4, Chrys. 4, Hilary 2, Gloss 2 (ord., non occ.), Origen 1.
- Page breaks `<pb n="749"/>` ... `n="752"` and footnotes as `[ed. note: ...]`,
  margin Scripture refs as `[marg. note: ...]` or `[<scripRef ...>]`.
- Attribution labels across Matthew (counts of paragraph openings): Jerome 813,
  Chrys. 748(+87 with work), Aug. (with work) 500, Pseudo-Chrys. 429, Remig. 370,
  Hilary 335, Origen 307, Raban. 192, Gloss (several forms), Greg., Ambrose, Bede,
  Leo, Cyprian, Chrysol. A later parser needs an alias table (e.g. "Raban." and
  "Rabanus", "Gloss.", "Gloss. ord.", "Gloss. interlin.", "Gloss. ap. Anselm").
- Mark (catena2) uses the same markup, e.g. `Theophylact:`, `Pseudo-Jerome:`,
  `Bede:` on Mark 12.

In the 1842 printing the label is the father's name in small capitals
("PSEUDO-CHRYS.", "JEROME;", "HILARY;") inline, with the work reference in the
margin ("Chrys. Hom. lxx.", "Gloss. non occ."). CCEL joins the margin reference
into the label.

Differences between CCEL and the 1842 page in this passage (word diff of CCEL
against the archive.org OCR, checked by eye) **[read]**:

| 1842 printing | CCEL |
|---|---|
| v. 17 "unto Caesar" | "unto Cesar" |
| "calls them not disciples but tempters" | "but tempter" |
| "in which His image was pourtrayed" | "portrayed" |
| "Then went the Pharisees; went to the Herodians." (one sentence) | "“Then went the Pharisees; went” to the Herodians." |
| margin "Chrys. Hom. lxx", "Gloss. non occ." | folded into the label |

Sizes **[read]**: CCEL Matthew ThML 3,021,275 bytes, TXT 2,526,126; Mark ThML
971,399, TXT 852,666 (1,064 and 685 `scripture` paragraphs). archive.org OCR
per part is about 0.7-1.1 MB (e.g. Matthew Part III 685,905 bytes).

## 5. Recommendation

- **Text of record:** the 1841-45 Oxford (Parker) printing, as scanned on
  archive.org (table above) with HathiTrust's `pd` scans as backup. This is
  public domain with no third-party usage terms found, covers all four Gospels,
  and is literally "as printed".
- **How to get clean text:** import only what the app needs, a section at a
  time, from the archive.org OCR, and correct it against the page images (the
  test Sunday needs about 4 printed pages). Use CCEL's Matthew/Mark text only if
  CCEL grants permission, since that saves most of the correction work for two
  Gospels.
- **Credit line** (panel): "Thomas Aquinas, Catena Aurea, translated under the
  editorship of John Henry Newman (Oxford: J. H. Parker, 1841-45)", plus the
  volume's translator where named. Do not use CCEL's "William Whiston".

## What the owner must decide

1. **Source for the shipped text** (pick one):
   - (a) Write to CCEL asking permission to include its Matthew and Mark text in
     the app (CCEL: "Contact us for permission to republish CCEL works"), and use
     archive.org scans for Luke and John. Fastest if CCEL says yes.
   - (b) Do not use CCEL's text; build from the archive.org 1841-45 scans for all
     four Gospels, correcting OCR per section as Sundays need them.
     (Recommended: no third-party terms, exact 1841 wording.)
   - (c) Treat the app as "non-profit" use under CCEL's page and use CCEL
     without asking. Not recommended without the owner's explicit judgment that
     the app is non-profit and that bundling counts as "use", not "republish".
2. **Luke and John:** confirm that archive.org OCR (corrected by hand) is
   acceptable for them, since no clean, clearly licensed transcription exists.
   isidore.co and ecatholic2000 are not recommended (no license; "all rights
   reserved").
3. **"Exactly as printed":** confirm that means the printed page (so CCEL's
   "Cesar"/"portrayed"/"tempter" would be corrected), and whether the
   margin work references ("Hom. lxx") are shown with the father's name.
4. **For the spec (not rights):** the Catena comments on sections such as
   15-22, not on single verses. "Grouped by verse" (decision 3) would need to
   become "grouped by section", or the plan would have to guess a verse from the
   quoted words.

## URLs used

- https://www.ccel.org/ccel/aquinas/catena1.html, https://www.ccel.org/ccel/aquinas/catena2.html
- https://www.ccel.org/ccel/aquinas/catena3.html, https://www.ccel.org/ccel/aquinas/catena4.html (404)
- https://www.ccel.org/ccel/a/aquinas/catena1.xml, https://www.ccel.org/ccel/a/aquinas/catena2.xml
- https://www.ccel.org/ccel/a/aquinas/catena1/cache/catena1.txt, .../catena2/cache/catena2.txt
- https://ccel.org/ccel/aquinas/catena1/catena1.ii.xxii.html
- https://www.ccel.org/ccel/aquinas, https://ccel.org/ccel/aquinas/catena-series/catena-series
- https://www.ccel.org/about/copyright.html
- https://archive.org/advancedsearch.php?q=title%3A%28catena+aurea%29&fl%5B%5D=identifier&fl%5B%5D=title&fl%5B%5D=date&fl%5B%5D=volume&fl%5B%5D=publisher&fl%5B%5D=possible-copyright-status&fl%5B%5D=rights&fl%5B%5D=licenseurl&rows=200&output=json
- https://archive.org/metadata/{catenaaureacomme00thomuoft, a6788682p201thomuoft, catenaurecommpt301thomuoft, catenaaureacomme01thomuoft, catenaaureacomme02thomuoft, catenaaureacomme03thomuoft, p2catenaaureacom03thomuoft, catenaaurept203thomuoft, catenaaureacomme04thomuoft, p1catenaaureaco04thomuoft, p2catenaaureacom04thomuoft}
- https://archive.org/download/{id}/{id}_djvu.txt for catenaaureacomme00thomuoft, catenaurecommpt301thomuoft, catenaaureacomme01thomuoft, catenaaureacomme02thomuoft, catenaaureacomme03thomuoft, p2catenaaureacom03thomuoft, catenaaureacomme04thomuoft, p1catenaaureaco04thomuoft
- https://archive.org/about/terms.php (JavaScript shell, unreadable)
- https://catalog.hathitrust.org/api/volumes/brief/oclc/3427671.json, .../224217324.json, .../38369001.json, .../13955563.json, .../4424508.json
- https://catalog.hathitrust.org/api/volumes/full/recordnumber/008977221.json, .../003993465.json, .../008412369.json
- https://catalog.hathitrust.org/Search/Home and https://babel.hathitrust.org/cgi/ls (bot check, 403)
- https://openlibrary.org/search.json?q=catena+aurea+commentary+four+gospels
- https://search.worldcat.org/search?q=catena+aurea+newman+1841 (page loads but results are rendered by script; no data)
- https://guides.library.cornell.edu/copyright/publicdomain
- https://en.wikipedia.org/wiki/Catena_aurea, /John_Henry_Newman, /Mark_Pattison, /John_Dobree_Dalgairns
- https://en.wikisource.org/wiki/Alumni_Oxonienses:_the_Members_of_the_University_of_Oxford,_1715-1886/Ryder,_Thomas_Dudley
- https://en.wikisource.org/w/index.php?search=Catena+Aurea&ns0=1&ns104=1
- https://isidore.co/aquinas/, https://isidore.co/aquinas/english/CAMatthew.htm (and CAMark, CALuke, CAJohn), https://isidore.co/aquinas/CAMatthew.htm
- https://raw.githubusercontent.com/Geremia/AquinasOperaOmnia/master/README.md (LICENSE, LICENSE.md, COPYING: 404)
- https://dhspriory.org/thomas/CAMatthew.htm (404)
- https://www.ecatholic2000.com/catena/, https://www.ecatholic2000.com/catena/untitled-02.shtml
- https://www.newadvent.org/fathers/

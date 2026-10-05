# Voices of the Church: owner decisions (pre-spec)

Status: decisions only, not a spec. The spec and plan come after slice 5a.

Source of the idea: the owner asked (2026-10-01) how The Faith Received
(https://mereorthodoxy.com/the-faith-received/) could serve worship
preparation. That site is a free-to-read library (19,597 works, many
translated with AI, "All rights reserved"); it stays link-only unless
Mere Orthodoxy grants permission.

## Owner answers (Beau, 2026-10-01, "all recommended")

1. In scope:
   - (1) The fathers verse by verse on the day's Gospel, from Thomas
     Aquinas's Catena Aurea in the 1841-45 Oxford English translation
     (edited by Newman), shown on the Readings step.
   - (3) "Bring this into the liturgy": the AI weaves a quotation's image
     or phrase into a card, never putting words in a father's mouth that
     are not in the source.
2. Out of scope for now: ancient collects in the prayer library, the
   homilies (Schaff's Nicene and Post-Nicene Fathers), and a link to The
   Faith Received's Scripture view.
3. For preparation only: quotations are not printed in the bulletin; only
   what "Bring this into the liturgy" weaves into a prayer reaches it.
4. Order: after 5a. Sequence: reviewer follow-up 1, Revise from "Across
   the service", 5a, Voices of the Church, 6a.
5. Source and rights: verify the translation's public-domain status, with
   cited sources, before any text enters the app. Needs ccel.org (or
   another source host) in the environment's allowed domains.
6. Only the verses actually read that Sunday get quotations, not the
   whole chapter.
7. Test case: a coming Sunday the owner is preaching, chosen when the
   spec is written.
8. Credit line: a prayer that echoes a father prints "after {Name}" in
   small type under it.

## Planning answers (Beau, 2026-10-05, "all recommended, I'm preaching October 18"; binding)

Sources checked on 2026-10-05 from the session: ccel.org is reachable and
hosts the Catena Aurea in four parts (catena1-4: Matthew, Mark, Luke, John);
archive.org has scans of the 1841 Oxford printing (for example
`catenaaureacomme04thomuoft`, `p1catenaaureaco04thomuoft`).

1. **When neither chosen reading is a Gospel**, the panel shows the fathers on
   that Sunday's lectionary Gospel, labeled ("From the Gospel for this Sunday:
   ..."). A chosen reading from a Gospel wins.
2. **The text lives in a data file the app ships with**, imported once after the
   rights check: no database change, no live dependence on ccel.org; the source
   is credited on the panel.
3. **The panel:** a collapsible **Voices of the Church** panel under the Gospel
   reading on step 1, collapsed by default with a count ("12 quotations on these
   verses"), quotations grouped by verse, each with the father's name and work.
4. **The 1841 English is shown exactly as printed** (no modernizing).
5. **"Bring this into the liturgy":** on a quotation, choose one prayer card; the
   AI rewrites that card weaving in the quotation's image or phrase, with Undo,
   like Revise; the reviewer's model.
6. **The "after {Name}" credit** prints in small type under that prayer in the
   printed bulletin and both Word copies; on the card it is a removable chip
   that stays through later edits until removed.
7. **If the rights check finds anything uncertain**, stop and bring it to the
   owner before any text goes in (a fallback: the archive.org scans of the 1841
   printing).
8. **Two PRs:** V1, the rights check, the text import and the Readings panel; V2,
   "Bring this into the liturgy" and the credit line.
9. **Test case:** Sunday, October 18, 2026 (the owner is preaching): the
   Twenty-First Sunday after Pentecost, Gospel Matthew 22:15-22 (Vanderbilt RCL,
   checked through the app's lectionary module on 2026-10-05).

## Source decision (Beau, 2026-10-05; binding)

After the rights check (`2026-10-05-voices-rights-check.md`, verdict YELLOW:
the 1841-45 Oxford translation is public domain in the US, but CCEL has only
Matthew and Mark, under terms that ask permission to republish, and no clean,
clearly licensed copy of Luke and John exists):

1. **Source (A):** the archive.org scans of the 1841-45 Oxford printing (John
   Henry Parker) for all four Gospels; not CCEL. The text is the printed wording,
   cleaned up automatically, then each section checked against the scanned page
   images before the app shows it, starting with the coming Sundays' Gospels
   (first Matthew 22:15-22 for 2026-10-18). A section not yet checked shows "Not
   yet transcribed for this passage." instead of uncorrected text.
2. **Grouping:** the panel groups quotations by the Catena's sections (for
   example Matthew 22:15-22 as one section), not by verse; planning answer 3
   reads "grouped by section". A section shows when it overlaps the verses read.
3. The 2026-10-05 planning note that CCEL hosts all four parts was wrong (it has
   catena1 and catena2 only).

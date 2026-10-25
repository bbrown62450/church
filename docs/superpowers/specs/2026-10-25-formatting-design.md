# Text formatting: design

Status: design for the owner's formatting decisions 3 to 5 of 2026-10-24 (binding; `2026-10-24-affirmation-and-formatting-decisions.md`), written with its plan `docs/superpowers/plans/2026-10-25-formatting.md`. The plan's code was built and replayed before this was committed.

## What the owner gets

The text boxes take a chosen set of markdown: **bold**, *italic*, two heading sizes, line breaks and simple lists. They print in the Word copies, the printed bulletin (PDF and Word) and so the emailed bulletin's attachments. Each box has a short "Formatting" line under it; the Review step has a text preview. A line starting with "People:" in the Call to Worship still prints in bold, and `**...**` bolds part of any line. No links, images, tables or code blocks. Text saved before the change prints exactly as before.

## Grammar (exact)

One grammar, one implementation per side: `backend/formatting.py` (prints) and `frontend/src/lib/formatting.ts` (the preview). Both pass every case of the shared fixture `backend/tests/fixtures/shared/formatting.json`.

**Lines.** The text is split on line breaks (the server has already turned `\r\n`, `\r`, a vertical tab and a form feed into `\n`, `archive._xml_safe`). A line is one of:
- `# ` then text: a heading. `## ` then text: a smaller heading.
- `- ` then text: a bulleted item (printed with "•").
- one to three digits, `.`, a space, then text: a numbered item, printed with its number as typed (no renumbering).
- anything else: text.

The mark must start the line (no leading space), and the text after it must not be blank (`# ` alone is text). `#1 hymn`, `#none`, `### three`, `-none`, `* star`, `1) one`, `1234. four` and `1.5 million` are text. One level of list only: an indented line is text.

**Blocks.** Each heading and item is its own block, one line long. Text lines next to each other form one text block that keeps its line breaks, blank lines included, exactly as a box prints today; blank lines at the start and end of a text block are dropped.

**Inline, within one line** (a mark never spans a line break):
- The line is read left to right into marks and characters: `\` followed by `*`, `#`, `-` or `.` (an escape: prints that character, never a mark), `**`, `*`, any other character.
- `**` or `*` **opens** when the character after it is not a space (space, tab or no-break space) and the character before it is not an ASCII letter or digit.
- It **closes** at the next mark of the same kind whose character before is not a space and whose character after is not an ASCII letter or digit, with at least one mark or character between.
- `**...**` is bold, `*...*` is italic; inside bold an italic opens (and the other way round), never bold in bold or italic in italic.
- A mark that does not close prints as typed. So `Psalm 23:1*`, `5 * 3 * 2`, `2*3*4`, `a**b**c`, `**God**s` and a lone `**` print as typed; `\*` prints `*`. A backslash before anything else prints as typed.
- The scan is linear in the line's length (each kind's next closing mark is found in one pass), so 20,000 characters of unclosed marks read in milliseconds.

**Dialogue boxes.** The Call to Worship and the Assurance of Pardon (`INLINE_ONLY`) take bold and italic only: their Leader and People lines are split exactly as today (`\b(Leader|People):`, any case, anywhere in the text), and each part's words read bold and italic. A `#` or `- ` there prints as typed.

**Not supported:** links, images, tables, code (inline or blocks), block quotes, HTML, underscores for emphasis, nested lists, `***`.

## Which boxes

| Box | Reads | Prints in |
|---|---|---|
| The eight liturgy cards | full grammar; Call to Worship and Assurance bold and italic only | Word copies (Prayers of the People: pastor's copy only) and the printed bulletin |
| A custom element's text | full | Word copies and the printed bulletin |
| The Affirmation's own text | full | Word copies (plain) and the printed bulletin (bold) |
| The four free-text announcements (activities, prayers and concerns, items for collection, other) | full, centered | the printed bulletin |
| Names (ushers, deacon, coffee hour, people), music titles, the sermon title, pasted reading text, settings fields | none: as typed | as today |

Pasted reading text stays as typed on purpose: scripture uses asterisks for footnotes and starts lines with verse numbers ("1. "), which would turn into lists.

## What prints where

The same blocks everywhere; only the renderer differs.

| | Word copy (`worship_service`) | Printed PDF (`printed_pdf`) | Printed Word (`printed_docx`) |
|---|---|---|---|
| Text | a paragraph with its line breaks, runs bold or italic | a paragraph, `<b>`/`<i>` | a paragraph, runs bold or italic |
| `#` | bold 13 pt, 6 pt before, kept with the next | bold 13 pt (16 leading), 6 pt before | bold 13 pt, 6 pt before, kept with the next |
| `##` | bold 12 pt, likewise | bold 12 pt (15 leading) | bold 12 pt |
| Item | marker, tab, text; 0.25 in hanging indent | marker as the bullet, text indented 18 pt | marker, tab, text; 0.25 in hanging indent |
| Announcements | n/a | heading and item lines centered, the item's marker before its text | likewise |
| Prayer of Confession (all three files); own Affirmation text (printed bulletin only; the Word copy prints it plain, as today) | every run bold, italic added | likewise | likewise |

**Headings and the section's own heading.** A heading inside a box is always under the section's heading: it never uses Word's Heading styles (so it is not in Word's navigation pane and the Word copy's section headings stay the only Heading 2s), and it is bold Times at 13 or 12 pt. In the printed bulletin the element's own heading (for example "OPENING PRAYER") stays as it is, in capitals, with the leader's name at the right; the box's headings follow under it. A heading at the foot of a PDF page moves to the next page with what follows (as an element heading does today).

**People lines.** In the Call to Worship, a People line prints in bold (the Word copy: the label plain, the words bold; the printed bulletin: both bold), as today; `*italic*` inside it is bold italic. `**...**` bolds part of a Leader line, or of any other box. "People:" lines in other boxes print as typed, as today (Questions for the owner, 2).

**The email.** `bulletin_email` attaches the files `usecases.documents` builds, so its attachments follow the table with no code of their own; the message itself is plain text, as today.

## Safety

Everything typed stays text. The PDF escapes each span (`xml.sax.saxutils.escape`, so `<`, `>` and `&` print) before adding its own `<b>`, `<i>` and `<br/>`; an item's marker is only ever "•" or digits and a full stop. python-docx writes runs as XML text, and `archive._xml_safe` already removes what XML cannot hold before anything prints. The preview draws spans as React text nodes, never `dangerouslySetInnerHTML` (the repo's lint rule forbids it). Tests type `<b>`, `<script>`, `<img onerror>`, `&amp;` and `<br/>` into a box and find them printed and shown as text.

## The Review preview

A "Text preview" card on the Review step, after the Archive card and before the Word documents, closed at first ("Show text preview", a 44 px row). Open, it shows every box that will print text, trimmed as the server trims it: the switched-on liturgy cards in order (the Prayers of the People labelled "(pastor's copy)"), the Affirmation's own text, the custom elements with a label, then the four announcements. Each box's lines are `printedLines(box, text)`: the printed bulletin's own rules, which the shared fixture pins on both sides (the fixture's expected lines are what `printed_bulletin` produces, so the preview cannot drift from print without a test failing). Style: serif, bold and italic spans, headings larger, items with their marker in a column, People lines bold, the Assurance's fixed response under its text, announcements centered. A blank box is left out; with none, "No text to preview yet."

## Help copy

Under each box that reads the full grammar, as part of the box's description for screen readers:

> Formatting: \*\*bold\*\*, \*italic\*, # Heading, ## Smaller heading, - or 1. for a list. Preview on the Review step.

Under the Call to Worship and the Assurance of Pardon:

> Formatting: \*\*bold\*\*, \*italic\*. Preview on the Review step.

Not under name boxes. No em dashes. The escape (`\*`) is in this spec and the fixture, not in the help line: a prayer rarely needs it, since a lone asterisk already prints as typed.

## AI interplay

- **Generation writes plain text, as today.** Its prompts already ask for plain liturgy text with "Leader:" and "People:" lines; nothing changes. A mark the AI did write prints formatted now instead of as asterisks, and the preview shows it. If drafts start carrying marks, a line in the default voice prompt is a small follow-up.
- **Revise keeps the marks.** It is offered on typed and saved text too, so it receives the text as typed; `REVISE_INSTRUCTION` adds: "Keep any formatting marks the draft has (\*\*bold\*\*, \*italic\*, lines starting # or ## for headings, - or 1. for lists) where they still fit, and add none." Stripping them would silently undo the user's formatting.
- **The reviewer and the pews read the words without the marks** (`formatting.plain`, in `api/routes/liturgy_review._cards`): they judge what is said aloud, a stray `**` invites a note about asterisks, and the code checks would miss a stock phrase split by a mark ("as **we** journey"). A heading keeps its words; an item keeps "- " or its number, so a list still reads as one. The notes quote the plain words, which is what prints. Nothing new is logged; no text is ever logged.

## Backward compatibility

`formatting.has_marks(text)` is the switch: text without any mark of the grammar takes each renderer's old code path unchanged, so it prints exactly as before (one paragraph, its line breaks, its spaces, a trailing blank line). Tests prove it three ways for a corpus of old text with literal `*`, `#`, `-`, digits and backslashes in every box: the printed bulletin's lines equal those of verbatim copies of the old helpers, the printed PDF is byte for byte the same and the printed Word body XML the same; and the Word copy's body XML equals the existing characterization test's verbatim Streamlit `build_docx`. Old text that does use the grammar (for example a typed "- " list in a Prayers of the People) now prints as a list; that is the feature. No saved text is rewritten.

## Limits

Unchanged: marks count toward each box's character limit (20,000 for a liturgy card and the Affirmation's own text, the custom element's and announcements' limits as today) and the counter past 18,000. A 20,000-character prayer full of marks prints in both files (tested).

## Deploy order: one PR

One PR: there is no API change (no new field, route or schema; the OpenAPI snapshot is unchanged), no migration and no stored change. Railway and Vercel deploy the same merge a few minutes apart, and either order is safe: pages first, the help line and preview show formatting while the server still prints marks as typed for those minutes; server first, marks print formatted before the help line appears. Nothing fails and nothing is saved differently, so a two-PR split would only add a second round of checks.

## No migration, no new dependency

Text is already stored as strings, as typed. No library: the subset is small, and full markdown libraries (markdown-it, marked, mistune) bring what the owner ruled out (links, HTML, code blocks from four leading spaces, lazy continuation lines) plus intraword emphasis (`2*3*4` becomes italic in CommonMark) and renumbered lists; two different libraries on two sides would also disagree. About 200 lines per side with a shared fixture is less risk.

## Testing

Backend `backend/tests/test_formatting.py` (76): the shared fixture's 26 cases through `printed_bulletin`; the marks; the old-text corpus (no marks; the printed bulletin's lines, PDF bytes and Word XML as before; the Word copy's XML as Streamlit's); the Word copy, the printed PDF and Word and the email's attachments reading the marks; nothing typed becoming markup; a prayer at the limit; the speed on 20,000 characters of unclosed marks; the reviewer's and the pews' AI messages carrying the words without marks. Frontend: `lib/formatting.test.ts` (the fixture's 26 cases, old text, no markup, speed), `formatting-help.test.tsx` (the help line in each box's description, not under names, no em dash), `text-preview-card.test.tsx` (what each box shows, typed HTML as text, a blank box left out, 44 px). Planted violations in the plan's Task 3.

## Out of scope

A toolbar (decision 4: maybe later); links, images, tables, code; underline; formatting in names, music, the sermon title, pasted readings or Settings; renumbering lists; nested lists; formatting in the email's message itself; converting old text.

## Risks

- **Old text that happens to use the grammar** (a line starting "- " or "1. ", or `**word**`) prints formatted after the merge. It is the feature, and the preview shows it before printing.
- **The preview drifts from print.** The shared fixture is the printed bulletin's own output, checked on both sides; a case added to one side fails the other until it matches.
- **Python and JavaScript differ on an edge character** (a lone surrogate before "People:", an unusual Unicode space). The TypeScript copies Python's whitespace set and word characters; the risk is a preview line split differently from print for such text, never a wrong file.
- **A long text full of marks.** Linear scan; tested at the limit.

## Questions for the owner

1. **Headings' sizes: 13 pt and 12 pt bold, in all three files** (recommended), under the section's own heading; or one size larger (14 and 12)? 13/12 keeps a prayer's heading below the Word copy's 13 pt section headings in weight and close to the printed bulletin's 11 pt element headings.
2. **"People:" lines outside the Call to Worship: keep them as typed** (recommended), or print them in bold in every box (for example a responsive Prayer of Confession or a custom element)? Bold everywhere would change how some old services print; wrapping the line in `**...**` already bolds it where wanted.

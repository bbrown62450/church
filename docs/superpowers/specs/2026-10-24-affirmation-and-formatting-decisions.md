# Affirmation of Faith and text formatting: owner decisions

Status: decisions only (owner, 2026-10-24, "all recommended"; binding), and the owner's answers A to D on the Affirmation of Faith (same day), with the owner's formatting answers 1 to 3 (2026-10-25) added below. Specs and plans follow.

The owner found that the Affirmation of Faith (always the Apostles' Creed, a fixed landmark in `OUTLINE`, `backend/liturgy_config.py`) cannot be removed or changed, and asked for bold, headings "and everything markdown can do" in the text boxes. Today the boxes take plain text; the only print formatting is a line starting with "People:" printed in bold.

## Affirmation of Faith

1. In the builder the Affirmation of Faith becomes a card like the prayers: an "Include Affirmation of Faith" switch (off: not printed or emailed), and a choice of Apostles' Creed, Nicene Creed or "your own text" (a text box like the prayers). Settings → Liturgy holds the church's default choice.
2. Built in: the Apostles' Creed and the Nicene Creed. Anything else (for example A Brief Statement of Faith) is pasted as the church's own text. The planning round checks the copyright terms of the exact English wordings used before they ship, and cites the source.

## Formatting

3. A chosen set, not full markdown: bold, italic, two heading sizes, line breaks and simple lists, in the Word file, the PDF and the emailed bulletin. No links, images, tables or code blocks.
4. Typed as markdown (`**bold**`, `*italic*`, `#` and `##`), with a short "Formatting help" line under each box and a preview on the Review step. A toolbar may come later.
5. A line starting with "People:" still prints entirely in bold by default; `**...**` bolds part of a line. Clarified 2026-10-25 (the owner's answer 2 below): "still" means where it prints in bold today, the Call to Worship. A "People:" line in any other box prints as typed, as today; the wording above had assumed bold everywhere.

## Affirmation of Faith: the owner's answers

Answered 2026-10-24, "all recommended" (binding), to the questions of the Affirmation of Faith spec (`2026-10-24-affirmation-design.md`) and its plan review:

A. Two PRs. Affirmation PR A is the server side and migration `0010_services_affirmation`, merged and confirmed live first; Affirmation PR B is the pages. Each has its own verification, pre-merge note, PR body, CI counts, merge, after-deploy check, phone check and runbook record. PR A's phone check is minimal (the app still saves and downloads as before); PR B's covers the card. PR A must be safe with today's frontend; PR B is guarded if it ever runs ahead of PR A.
B. The Apostles' Creed keeps today's traditional (1662 Book of Common Prayer) wording.
C. The Nicene Creed includes "and the Son" (no brackets).
D. No "leave it out" church default now.

## Formatting: the owner's answers

Addendum, 2026-10-25. Answered "all recommended" (binding), to the questions of the formatting spec (`2026-10-25-formatting-design.md`) and its plan review:

1. Headings inside a box. The printed bulletin (PDF and Word) prints them bold at 12 pt and 11 pt, in the case typed, under the element's own heading (11 pt bold capitals, with the leader's name at the right). The smaller one is the element heading's size; it differs by not being in capitals. The Word copy keeps bold 13 pt and 12 pt under its section headings (Word's Heading 2).
2. "People:" lines outside the Call to Worship keep printing as typed, as today; only the Call to Worship bolds People lines (item 5 above, clarified).
3. Old text: the change is accepted. The owner's read-only count of the saved services: 31 services; none with list-like lines in a prayer or a custom element; none in a bulletin; one with an asterisk before a letter. Text with no formatting marks prints exactly as before. Text with marks ("- x", "1. x", `*word*`, `**word**`, a line starting `#`, a backslash before one of those) now prints formatted, and the Review step's preview shows it first. `\*` keeps a literal asterisk.

## Order of work

6. Finish the Theme PR 1 phone check; then the Affirmation of Faith change; then formatting; then the em-dash follow-up PR; then Theme PR 2.

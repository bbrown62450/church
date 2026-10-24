# Affirmation of Faith and text formatting: owner decisions

Status: decisions only (owner, 2026-10-24, "all recommended"; binding), and the owner's answers A to D on the Affirmation of Faith (same day). Specs and plans follow.

The owner found that the Affirmation of Faith (always the Apostles' Creed, a fixed landmark in `OUTLINE`, `backend/liturgy_config.py`) cannot be removed or changed, and asked for bold, headings "and everything markdown can do" in the text boxes. Today the boxes take plain text; the only print formatting is a line starting with "People:" printed in bold.

## Affirmation of Faith

1. In the builder the Affirmation of Faith becomes a card like the prayers: an "Include Affirmation of Faith" switch (off: not printed or emailed), and a choice of Apostles' Creed, Nicene Creed or "your own text" (a text box like the prayers). Settings → Liturgy holds the church's default choice.
2. Built in: the Apostles' Creed and the Nicene Creed. Anything else (for example A Brief Statement of Faith) is pasted as the church's own text. The planning round checks the copyright terms of the exact English wordings used before they ship, and cites the source.

## Formatting

3. A chosen set, not full markdown: bold, italic, two heading sizes, line breaks and simple lists, in the Word file, the PDF and the emailed bulletin. No links, images, tables or code blocks.
4. Typed as markdown (`**bold**`, `*italic*`, `#` and `##`), with a short "Formatting help" line under each box and a preview on the Review step. A toolbar may come later.
5. A line starting with "People:" still prints entirely in bold by default; `**...**` bolds part of a line.

## Affirmation of Faith: the owner's answers

Answered 2026-10-24, "all recommended" (binding), to the questions of the Affirmation of Faith spec (`2026-10-24-affirmation-design.md`) and its plan review:

A. Two PRs. Affirmation PR A is the server side and migration `0010_services_affirmation`, merged and confirmed live first; Affirmation PR B is the pages. Each has its own verification, pre-merge note, PR body, CI counts, merge, after-deploy check, phone check and runbook record. PR A's phone check is minimal (the app still saves and downloads as before); PR B's covers the card. PR A must be safe with today's frontend; PR B is guarded if it ever runs ahead of PR A.
B. The Apostles' Creed keeps today's traditional (1662 Book of Common Prayer) wording.
C. The Nicene Creed includes "and the Son" (no brackets).
D. No "leave it out" church default now.

## Order of work

6. Finish the Theme PR 1 phone check; then the Affirmation of Faith change; then formatting; then the em-dash follow-up PR; then Theme PR 2.

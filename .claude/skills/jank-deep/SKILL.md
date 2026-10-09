---
name: jank-deep
description: Deep hunt for jank in a named part of the worship app (visual glitches, slowness, and rough edges in behavior and wording), reported as a ranked list in chat. Use when the owner types /jank-deep, optionally followed by the area to look at (for example "/jank-deep Settings → Hymns"). Report only; never fixes anything.
---

# /jank-deep

Look hard at one part of the app for anything that would feel janky to a pastor or church member using it on a phone, and report what you find. **Report only: do not edit code, commit, push, open issues or PRs, or change any data.** Fixes go through the usual plan, review and PR process afterward, if the owner wants them.

## Scope

- The area is whatever follows `/jank-deep` (a page, a step of the builder, a feature such as "emailing the bulletin"). If nothing follows it, ask which area to look at; do not sweep the whole app.
- Map the area to its code first: the route under `frontend/src/app/`, its components under `frontend/src/components/`, its queries under `frontend/src/lib/`, and the backend routes and usecases it calls under `backend/api/routes/` and `backend/usecases/`.

## What counts as jank (all four kinds)

1. **Visual:** layout that shifts after load, flicker, content jumping when data arrives, text cut off or overflowing at 375 px, sideways scrolling, tap targets smaller than 44 px, inconsistent spacing, headings or buttons that differ from the same thing on other pages, dark-mode or contrast problems.
2. **Slow or laggy:** spinners with no end, no feedback after a tap, requests fired twice, waterfalls of requests that could run together, pages that render in pieces, missing skeletons, long waits with no "still working" message, timeouts shorter than the work.
3. **Behavior:** lost work (no leave guard, a failed save that clears the form), no undo or confirmation where one is expected, dead ends, focus that drops to the page or lands somewhere odd, dialogs that close mid-request, stale data after a change elsewhere, a double tap that does something twice, error messages that show nowhere, the phone keyboard covering a field or the Save button.
4. **Wording:** confusing or inconsistent labels, jargon, messages that do not say what to do next, em dashes in user-facing copy (the project forbids them), wording that differs from the same idea on another page.

## How to look

1. **Read the code** for the area, using the list above as a checklist. Compare against the matching spec in `docs/superpowers/specs/` and the plan in `docs/superpowers/plans/`: expected behavior comes from those, never from the code itself. Note where code and spec disagree as a question, not a defect.
2. **Run what can run.** Run the area's existing tests (`.venv/bin/python -m pytest -q <files>` from the repo root; `npx vitest run <paths>` in `frontend/`). If a page can be viewed without signing in, start the frontend (`npm run dev` in `frontend/`) and use the pre-installed Chromium through Playwright (never run `playwright install`) at 375 px and at desktop width, and take screenshots into the scratchpad, not the repo.
3. **Signed-in pages:** this environment has no test sign-in, so you cannot drive signed-in pages in a real browser. Say so plainly, mark those checks NOT ASSESSED, and suggest a short check the owner can do on their phone instead.
4. Never use the owner's church, real names, emails or prayers in anything you run or write. Never sign in as the owner or call production APIs.

## Report (in chat)

Lead with a one-line verdict for the area. Then a ranked list, most painful first. For each finding:

- **What:** one plain sentence a non-programmer can picture.
- **Where:** `file:line`, and the page or step.
- **Who notices and when:** for example "a member on a phone, when the keyboard opens".
- **Evidence:** label it **observed** (from a test run or screenshot you actually made), **inferred** (from reading the code), or **NOT ASSESSED** (could not check here).
- **Confidence** (is it real?) and **priority** (how much does it matter?), kept separate.
- **Smallest check that would prove it wrong.**
- **Suggested fix**, in a sentence or two (do not apply it).

Sort each finding into one of: confirmed defect, likely defect, requirement question for the owner, product suggestion, or personal taste. Group duplicates by root cause.

End with:
- **NOT ASSESSED:** what you could not check, and whether it could change the picture.
- **Phone checks for the owner:** at most three short steps the owner can try on their phone to confirm the top findings.
- **Next step:** offer to turn the confirmed and likely defects into a plan for a small follow-up PR. Do not start it without the owner's yes.

"No jank found" is a valid answer if it is true; say what you looked at.

Keep the report free of em dashes, church ids, emails, tokens and real names.

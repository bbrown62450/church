# Printed Bulletin PR 2a: Bulletin Settings

(WIP: the plan is being written; its code is being built in a scratch worktree.)

Baseline measured 2026-10-02 at `f2bddda`: backend 1357 passed, 16 skipped; frontend 660 passed in 83 files.

Decisions so far:
- `GET /church/bulletin-settings` (any member), `PUT /church/bulletin-settings` (admins), stored in
  `churches.settings["bulletin"]`, written whole under the church row lock (other keys untouched; last save wins).
- A blank standing field prints nothing (PR 2 answer 3); the weekly fields keep PR 1's placeholders until 2b.
- The panel is a page, `/bulletin-settings`, linked from the Printed bulletin card; members read it.

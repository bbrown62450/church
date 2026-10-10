# Slice 6b-2a: Settings → People (Invite Links, Members, Pending Invites) and the One-Owner Migration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** first draft (2026-10-10). The tasks are being built and replayed; this file is committed early so a container restart loses nothing.

**Goal:** Ship the first of slice 6b-2's two PRs (owner's 6b-2 planning answers of 2026-10-10, "all recommended"; binding): **Settings → People** at `/settings/people` (Invite someone, Members, Pending invites) and migration **`0009_memberships_one_owner`**.

## Task list (draft)

- T1: Migration `0009_memberships_one_owner`, the model, the README's owner steps.
- T2: The People rules (`lib/settings/people.ts`), `lib/clipboard.ts`, the types and fixtures.
- T3: The People queries, `ConfirmDialog` with a body, `CopyLinkButton`, `InitialsAvatar`.
- T4: The Members section and the page.
- T5: Invite someone, the link panel and Pending invites.
- T6: People in the Settings nav.
- T7: Docs: the manual check items.
- T8: Verification.
- T9: The owner's pre-merge routine for 0009 (one step at a time).
- T10: The draft PR, the merge, the after-deploy check, the phone check, the record.

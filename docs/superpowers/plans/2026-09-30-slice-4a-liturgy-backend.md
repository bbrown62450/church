# Slice 4a: Liturgy Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

(WIP: this plan is being written; sections below are filled in as the planner goes.)

## Owner answers (2026-09-30, "all recommended", binding)

1. Custom elements get no AI Generate (S Risks item 7 answered "no"); recorded in F's decisions table as D17 by the docs task. Nothing custom in 4a.
2. Slice 4 ships as two PRs: 4a backend (this plan), 4b frontend later.
3. The service reviewer add-on is a separate small slice after 4b; not in 4a.
4. Owner steps: (a) before 4a is marked ready, a read-only Supabase query of stored prompt overrides, validated locally with `validate_prompts`; (b) after the merge, a live check including one real Prayers of the People generation, measured against the 30 s per-attempt timeout and the token budget.
5. Testing: automated tests; the owner's live checks are signed-in Console calls, one step at a time.

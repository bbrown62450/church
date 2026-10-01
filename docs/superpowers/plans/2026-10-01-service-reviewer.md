# Service Reviewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

(Work in progress: this plan is being written. Sections below are filled in task by task.)

**Goal:** Ship the service reviewer add-on as one PR (backend and frontend): a "Review service" button on the Liturgy step that leaves short notes under each prayer and in an "Across the service" box, "Revise with these notes" on AI-written cards, the code checks, the AI review, and the writer's new season guidance.

**Source documents:**
- Reviewer spec ("R"): `docs/superpowers/specs/2026-09-26-service-reviewer-design.md`.
- Slice 4 spec ("S4"): `docs/superpowers/specs/2026-09-25-slice-4-liturgy-design.md`, "Amendment 2026-09-26: service reviewer", and its 4a and 4b notes.
- Foundations ("F"): `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`.

Baselines checked on `3957d45` (2026-10-01): backend `1183 passed, 11 skipped`; frontend `539 passed` in 75 files.

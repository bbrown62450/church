import { describe, expect, it } from "vitest";

import { lectionary, testDraft } from "@/test/fixtures";

import {
  applyReadingSet,
  chooseReadingSet,
  editOccasion,
  editScriptureLines,
  setDate,
  setPick,
  setTranslation,
} from "./readings";
import type { DraftV1, HymnPick, StepId } from "./schema";
import { isPristine, stepStatus, stillNeeded } from "./status";
import { SHIPPED_STEPS, STEPS, stepById, stepFromPath } from "./steps";

const READINGS: ReadonlySet<StepId> = new Set<StepId>(["readings"]);
const ALL: ReadonlySet<StepId> = new Set<StepId>(["readings", "hymns", "liturgy", "review"]);
const HYMN: HymnPick = { hymn_id: "h1", title: "Amazing Grace", number: 649, hymnal: "GG2013" };

function withLiturgy(patch: Partial<DraftV1["liturgy"]>): DraftV1 {
  return testDraft((d) => ({ ...d, liturgy: { ...d.liturgy, ...patch } }));
}

function withCard(key: keyof DraftV1["liturgy"]["cards"], card: Partial<DraftV1["liturgy"]["cards"]["benediction"]>) {
  return testDraft((d) => ({
    ...d,
    liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, [key]: { ...d.liturgy.cards[key], ...card } } },
  }));
}

describe("steps (S steps.ts)", () => {
  it("lists the four steps in order, ships Date & readings (2c), and reads a step from its path", () => {
    expect(STEPS.map((s) => [s.number, s.label, s.href, s.previous, s.next])).toEqual([
      [1, "Date & readings", "/builder/readings", null, "hymns"],
      [2, "Hymns", "/builder/hymns", "readings", "liturgy"],
      [3, "Liturgy", "/builder/liturgy", "hymns", "review"],
      [4, "Review & send", "/builder/review", "liturgy", null],
    ]);
    expect([...SHIPPED_STEPS]).toEqual(["readings"]);
    expect(stepById("liturgy").label).toBe("Liturgy");
    expect(stepFromPath("/builder/hymns")).toBe("hymns");
    expect(stepFromPath("/builder/review/")).toBe("review");
    expect(stepFromPath("/builder")).toBeNull();
    expect(stepFromPath("/builder/summary")).toBeNull();
    expect(stepFromPath("/services")).toBeNull();
  });
});

describe("stepStatus (F §4.7)", () => {
  it("shows Soon for unshipped steps and Not in archive for Review", () => {
    const d = testDraft();
    expect(STEPS.map((s) => stepStatus(d, s.id).kind)).toEqual(["incomplete", "soon", "soon", "not_in_archive"]);
    expect(stepStatus(d, "readings", new Set())).toEqual({ kind: "soon" });
    expect(stepStatus(d, "review", ALL)).toEqual({ kind: "not_in_archive" });
  });

  it("counts the readings: a valid date, an occasion and a scripture (\"2 of 3\")", () => {
    const fresh = testDraft();
    expect(stepStatus(fresh, "readings", READINGS)).toEqual({ kind: "incomplete", done: 1, total: 3 });
    const occasion = editOccasion(fresh, "Harvest");
    expect(stepStatus(occasion, "readings", READINGS)).toEqual({ kind: "incomplete", done: 2, total: 3 });
    const blankLines = editScriptureLines(occasion, "\n  \n");
    expect(stepStatus(blankLines, "readings", READINGS)).toEqual({ kind: "incomplete", done: 2, total: 3 });
    const full = applyReadingSet(fresh, lectionary("2026-10-04"), 0);
    expect(stepStatus(full, "readings", READINGS)).toEqual({ kind: "complete" });
    expect(stepStatus(setDate(full, ""), "readings", READINGS)).toEqual({ kind: "incomplete", done: 2, total: 3 });
    expect(stepStatus(setDate(full, "2250-01-01"), "readings", READINGS)).toEqual({
      kind: "incomplete",
      done: 2,
      total: 3,
    });
    // Owner answer E: a field showing its message does not count.
    const twoOf3 = { kind: "incomplete", done: 2, total: 3 };
    expect(stepStatus(editOccasion(full, "x".repeat(301)), "readings", READINGS)).toEqual(twoOf3);
    expect(stepStatus(editOccasion(full, "x".repeat(300)), "readings", READINGS)).toEqual({ kind: "complete" });
    const lines = (n: number) => Array.from({ length: n }, (_, i) => `Psalm ${i + 1}`).join("\n\n");
    expect(stepStatus(editScriptureLines(full, lines(21)), "readings", READINGS)).toEqual(twoOf3);
    expect(stepStatus(editScriptureLines(full, lines(20)), "readings", READINGS)).toEqual({ kind: "complete" });
    expect(stepStatus(editScriptureLines(full, `Mark 1:1\n${"y".repeat(201)}`), "readings", READINGS)).toEqual(twoOf3);
    // The limit counts the trimmed line, as the row and the message do.
    expect(stepStatus(editScriptureLines(full, `Mark 1:1\n  ${"y".repeat(200)}  `), "readings", READINGS)).toEqual({
      kind: "complete",
    });
  });

  it("counts filled hymn slots and enabled liturgy cards with text once those steps ship", () => {
    const oneHymn = testDraft((d) => ({ ...d, hymns: { ...d.hymns, slots: { ...d.hymns.slots, opening: HYMN } } }));
    expect(stepStatus(oneHymn, "hymns", ALL)).toEqual({ kind: "incomplete", done: 1, total: 3 });
    expect(stepStatus(withCard("call_to_worship", { text: "Come" }), "liturgy", ALL)).toEqual({
      kind: "incomplete",
      done: 1,
      total: 7,
    });
  });
});

describe("isPristine (S status.ts)", () => {
  it("is true for a fresh draft, a lectionary fill and a default benediction with text", () => {
    expect(isPristine(testDraft())).toBe(true);
    expect(isPristine(applyReadingSet(testDraft(), lectionary("2026-10-04"), 0))).toBe(true);
    expect(isPristine(withCard("benediction", { text: "Halverson", origin: "default" }))).toBe(true);
  });

  it("is false once anything the user would lose is there", () => {
    const cases: [string, DraftV1][] = [
      ["typed card", withCard("call_to_worship", { text: "Come", origin: "typed" })],
      ["ai card", withCard("call_to_worship", { text: "Come", origin: "ai" })],
      ["archive card", withCard("benediction", { text: "Go", origin: "archive" })],
      ["communion chosen", withLiturgy({ communion_origin: "user" })],
      ["sermon title", withLiturgy({ sermon_title: "Grace" })],
      ["custom element", withLiturgy({ custom_elements: [{ id: "1", label: "Anthem", text: "", insert_after: "assurance" }] })],
      ["a pick", setPick(testDraft(), "ot", "Isaiah 5:1-7")],
      ["a hymn", testDraft((d) => ({ ...d, hymns: { ...d.hymns, slots: { ...d.hymns.slots, closing: HYMN } } }))],
      ["editing", testDraft((d) => ({ ...d, editing: { service_id: "s1", saved_at: "2026-09-29T16:00:00Z" } }))],
      ["user fields", editOccasion(testDraft(), "Harvest")],
      ["archive fields", testDraft((d) => ({ ...d, readings: { ...d.readings, fields_origin: "archive" } }))],
      // Owner answer Q2 (2026-09-29): a picked date, a chosen reading set and a translation override.
      ["a picked date", setDate(testDraft(), "2026-10-11")],
      ["the same date picked by hand", setDate(testDraft(), "2026-10-04")],
      [
        "a chosen reading set",
        chooseReadingSet(applyReadingSet(testDraft(), lectionary("2026-10-04"), 0), lectionary("2026-10-04"), 1),
      ],
      ["a translation", setTranslation(testDraft(), "kjv", "web")],
    ];
    for (const [name, d] of cases) expect(isPristine(d), name).toBe(false);
  });
});

describe("isPristine and the date and translation defaults (owner answer Q2)", () => {
  it("stays true for the default date, a lectionary fill of it, Use next Sunday and the church's own translation", () => {
    const filled = applyReadingSet(testDraft(), lectionary("2026-10-04"), 0);
    expect(isPristine(filled)).toBe(true);
    // "Use next Sunday" sets the date with origin "default"; the church's translation is stored as null.
    expect(isPristine(setDate(setDate(testDraft(), "2026-10-11"), "2026-10-04", "default"))).toBe(true);
    expect(isPristine(setTranslation(testDraft(), "web", "web"))).toBe(true);
    expect(isPristine(setTranslation(setTranslation(testDraft(), "kjv", "web"), "web", "web"))).toBe(true);
    const archivedDate = testDraft((d) => ({ ...d, readings: { ...d.readings, date_origin: "archive" } }));
    expect(isPristine(archivedDate)).toBe(true);
  });
});

describe("stillNeeded (S Review \"Still needed\")", () => {
  it("lists only shipped steps' gaps", () => {
    const fresh = setDate(testDraft(), "");
    expect(stillNeeded(fresh, new Set())).toEqual([]);
    expect(stillNeeded(fresh, READINGS)).toEqual([
      { step: "readings", message: "No service date", action: "Choose one" },
      { step: "readings", message: "No occasion", action: "Add one" },
      { step: "readings", message: "No scripture readings", action: "Add one" },
    ]);
    expect(stillNeeded(applyReadingSet(testDraft(), lectionary("2026-10-04"), 0), READINGS)).toEqual([]);
  });
});

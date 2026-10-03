import { describe, expect, it } from "vitest";

import { lectionary, serviceBulletin, testDraft } from "@/test/fixtures";

import { fingerprint } from "./fingerprint";
import { draftToServicePayload } from "./mapping";
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
import { isDirty, isPristine, reviewStatus, saveMode, stepStatus, stillNeeded, withoutTranslation } from "./status";
import { SHIPPED_STEPS, STEPS, stepById, stepFromPath } from "./steps";
import { applyCarry, keepCarried, setAnnouncement, setPartLeader, setPastedText, setPerson } from "./bulletin";
import { DEFAULT_BENEDICTION_FALLBACK } from "@/lib/liturgy/defaults";

const READINGS: ReadonlySet<StepId> = new Set<StepId>(["readings"]);
const ALL: ReadonlySet<StepId> = new Set<StepId>(["readings", "hymns", "liturgy", "review"]);
const HYMN: HymnPick = { hymn_id: "h1", title: "Amazing Grace", number: 649, hymnal: "GG2013" };

/** A new draft with last week's coffee hour carried in (printed bulletin PR 2b). */
function carriedDraft(): DraftV1 {
  const announcements = { ...serviceBulletin().announcements, coffee_hour: "The Example family" };
  const previous = { service_id: "s0", service_date_iso: "2026-09-27", bulletin: serviceBulletin({ announcements }) };
  return applyCarry(testDraft(), previous, "2026-10-04");
}

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
  it("lists the four steps in order, ships all four (2c, 3b, 4b and Review in 5a-3), and reads a step from its path", () => {
    expect(STEPS.map((s) => [s.number, s.label, s.href, s.previous, s.next])).toEqual([
      [1, "Date & readings", "/builder/readings", null, "hymns"],
      [2, "Hymns", "/builder/hymns", "readings", "liturgy"],
      [3, "Liturgy", "/builder/liturgy", "hymns", "review"],
      [4, "Review & send", "/builder/review", "liturgy", null],
    ]);
    expect([...SHIPPED_STEPS]).toEqual(["readings", "hymns", "liturgy", "review"]);
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
    expect(STEPS.map((s) => stepStatus(d, s.id).kind)).toEqual(["incomplete", "incomplete", "incomplete", "not_in_archive"]);
    expect(stepStatus(d, "liturgy", READINGS)).toEqual({ kind: "soon" });
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
      done: 2, // and the Benediction, following the church default (slice 4b)
      total: 7,
    });
  });
});

describe("isPristine (S status.ts)", () => {
  it("is true for a fresh draft, a lectionary fill and a default benediction with text", () => {
    expect(isPristine(testDraft())).toBe(true);
    expect(isPristine(applyReadingSet(testDraft(), lectionary("2026-10-04"), 0))).toBe(true);
    expect(isPristine(withCard("benediction", { text: DEFAULT_BENEDICTION_FALLBACK, origin: "default" }))).toBe(true);
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
      ["editing", testDraft((d) => ({ ...d, editing: { service_id: "s1", saved_at: "2026-09-29T16:00:00Z", date_iso: "2026-10-04" } }))],
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
      // Printed bulletin PR 2b: anything typed on the Bulletin step.
      ["an announcement", setAnnouncement(testDraft(), "coffee_hour", "The Example family")],
      ["last week's kept", keepCarried(carriedDraft(), "coffee_hour")],
      ["a person this week", setPerson(testDraft(), "organist", "")],
      ["a part's leader", setPartLeader(testDraft(), "sermon", "Rev. Guest")],
      ["pasted text", setPastedText(testDraft(), "Psalm 23", "The Lord is my shepherd.")],
    ];
    for (const [name, d] of cases) expect(isPristine(d), name).toBe(false);
    // Last week's text carried in and not touched comes back on its own: nothing to lose.
    expect(isPristine(carriedDraft())).toBe(true);
  });
});

describe("the Bulletin step's status (printed bulletin PR 2b)", () => {
  it("is Soon until it ships, then Optional, or how many boxes from last week are still to check", () => {
    expect(stepStatus(testDraft(), "bulletin", ALL)).toEqual({ kind: "soon" });
    const shipped = new Set<StepId>([...ALL, "bulletin"]);
    expect(stepStatus(testDraft(), "bulletin", shipped)).toEqual({ kind: "optional" });
    expect(stepStatus(carriedDraft(), "bulletin", shipped)).toEqual({ kind: "to_check", count: 1 });
    expect(stillNeeded(carriedDraft(), shipped)).toEqual(stillNeeded(testDraft(), shipped)); // never "Still to do"
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
    // New service and roll-forward look past an override with withoutTranslation, which copies.
    const kjv = setTranslation(testDraft(), "kjv", "web");
    expect(isPristine(withoutTranslation(kjv))).toBe(true);
    expect(kjv.readings.translation).toBe("kjv");
  });
});

describe("isPristine and the hymns step (owner answer 1, 2026-09-29)", () => {
  it("counts a hymn slot and a chosen hymnal, never the Exclude switch or the other ideas", () => {
    const hymns = (patch: Partial<DraftV1["hymns"]>) => testDraft((d) => ({ ...d, hymns: { ...d.hymns, ...patch } }));
    expect(isPristine(hymns({ hymnal: "PH1990" }))).toBe(false);
    expect(isPristine(hymns({ slots: { opening: null, response: HYMN, closing: null } }))).toBe(false);
    const ideas = { for_date_iso: "2026-10-04", by_slot: { opening: [HYMN], response: [], closing: [HYMN] } };
    expect(isPristine(hymns({ exclude_recent: false }))).toBe(true);
    expect(isPristine(hymns({ alternatives: ideas }))).toBe(true);
    expect(isPristine(hymns({ exclude_recent: false, alternatives: ideas }))).toBe(true);
  });
});

describe("isPristine and the liturgy step (owner answer 1, 2026-09-30)", () => {
  it("counts a switch moved from its default and text that prints, never a card following the church default", () => {
    // Everything that ends up in the service counts: text, the switches, communion, the title, custom elements.
    expect(isPristine(withCard("call_to_worship", { enabled: false }))).toBe(false);
    expect(isPristine(withCard("prayers_of_the_people", { enabled: true }))).toBe(false);
    expect(isPristine(withCard("benediction", { enabled: false }))).toBe(false);
    expect(isPristine(withCard("opening_prayer", { text: "Gracious God", origin: "typed" }))).toBe(false);
    // A Benediction still following the church default is not the user's work, whatever the default says.
    expect(isPristine(withCard("benediction", { text: "Go in peace.", origin: "default" }))).toBe(true);
    expect(isPristine(withCard("benediction", { text: "", origin: "default" }))).toBe(true);
    // Text that prints nothing is not work: blank typing, a blank title.
    expect(isPristine(withCard("assurance", { text: "  \n ", origin: "empty" }))).toBe(true);
    expect(isPristine(withLiturgy({ sermon_title: "   " }))).toBe(true);
    // A card switched off and back on again is as it was.
    expect(isPristine(withCard("call_to_worship", { enabled: true }))).toBe(true);
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

  it("counts the hymns step n of 3 and lists each empty slot (slice 3b) and a hymn not in the hymnal (5a-3)", () => {
    const filled = applyReadingSet(testDraft(), lectionary("2026-10-04"), 0);
    const withSlots = (slots: Partial<DraftV1["hymns"]["slots"]>) => ({
      ...filled,
      hymns: { ...filled.hymns, slots: { ...filled.hymns.slots, ...slots } },
    });
    expect(stepStatus(filled, "hymns")).toEqual({ kind: "incomplete", done: 0, total: 3 });
    expect(stepStatus(withSlots({ opening: HYMN, closing: HYMN }), "hymns")).toEqual({ kind: "incomplete", done: 2, total: 3 });
    const archived = { ...HYMN, hymn_id: null }; // shown as "Not in your hymnal", still a pick
    const all = withSlots({ opening: HYMN, response: archived, closing: HYMN });
    expect(stepStatus(all, "hymns")).toEqual({ kind: "complete" });
    const hymnsShipped = new Set<StepId>(["readings", "hymns"]); // the liturgy's rows are 4b's test below
    expect(stillNeeded(filled, hymnsShipped)).toEqual([
      { step: "hymns", message: "No Opening hymn", action: "Choose one" },
      { step: "hymns", message: "No Response hymn", action: "Choose one" },
      { step: "hymns", message: "No Closing hymn", action: "Choose one" },
    ]);
    expect(stillNeeded(withSlots({ response: HYMN }), hymnsShipped)).toEqual([
      { step: "hymns", message: "No Opening hymn", action: "Choose one" },
      { step: "hymns", message: "No Closing hymn", action: "Choose one" },
    ]);
    expect(stillNeeded(all, hymnsShipped)).toEqual([
      { step: "hymns", message: "Amazing Grace isn't in your hymnal", action: "Choose a replacement" },
    ]);
    expect(stillNeeded(withSlots({ opening: HYMN, response: HYMN, closing: HYMN }), hymnsShipped)).toEqual([]);
    expect(stillNeeded(filled, READINGS)).toEqual([]); // before 3b: no hymn rows
    expect(stillNeeded(filled, hymnsShipped).some((item) => item.step === "liturgy")).toBe(false);
  });

  it("counts the liturgy's enabled cards with text and lists the empty ones and a missing title (slice 4b)", () => {
    const d = testDraft(); // the Benediction follows the church default: 1 of 7
    expect(stepStatus(d, "liturgy")).toEqual({ kind: "incomplete", done: 1, total: 7 });
    const allOff = withLiturgy({
      cards: Object.fromEntries(
        Object.entries(d.liturgy.cards).map(([key, card]) => [key, { ...card, enabled: false }]),
      ) as DraftV1["liturgy"]["cards"],
    });
    expect(stepStatus(allOff, "liturgy")).toEqual({ kind: "complete" }); // every card off
    const rows = stillNeeded(withCard("assurance", { enabled: false })).filter((item) => item.step === "liturgy");
    expect(rows).toEqual([
      { step: "liturgy", message: "Call to Worship is empty", action: "Write or generate it", href: "/builder/liturgy#card-call_to_worship" },
      { step: "liturgy", message: "Opening Prayer is empty", action: "Write or generate it", href: "/builder/liturgy#card-opening_prayer" },
      {
        step: "liturgy",
        message: "Prayer of Confession is empty",
        action: "Write or generate it",
        href: "/builder/liturgy#card-prayer_of_confession",
      },
      {
        step: "liturgy",
        message: "Prayer for Illumination is empty",
        action: "Write or generate it",
        href: "/builder/liturgy#card-prayer_for_illumination",
      },
      { step: "liturgy", message: "Offertory Prayer is empty", action: "Write or generate it", href: "/builder/liturgy#card-offertory_prayer" },
      { step: "liturgy", message: "No sermon title", action: "Add one" },
    ]);
    const titled = withLiturgy({ sermon_title: "Living Water" });
    expect(stillNeeded(titled).some((item) => item.message === "No sermon title")).toBe(false);
  });
});

describe("the archive status and what Save does (slice 5a-3; S status.ts)", () => {
  const saved = (d: DraftV1, dateIso: string | null = d.readings.date_iso): DraftV1 => ({
    ...d,
    editing: { service_id: "s1", saved_at: "2026-10-01T14:42:00+00:00", date_iso: dateIso },
    saved_fingerprint: fingerprint(draftToServicePayload(d)),
  });

  it("reviewStatus is not in the archive, saved, or changed since; the step bar shows it once Review ships", () => {
    const fresh = testDraft();
    expect(reviewStatus(fresh)).toBe("not_in_archive");
    expect(reviewStatus(editOccasion(fresh, "Harvest"))).toBe("not_in_archive"); // never saved
    const clean = saved(editOccasion(fresh, "Harvest"));
    expect(reviewStatus(clean)).toBe("saved");
    expect(isDirty(clean)).toBe(false);
    expect(reviewStatus(editOccasion(clean, "Harvest Home"))).toBe("unsaved_changes");
    expect(reviewStatus(editOccasion(clean, "Harvest  "))).toBe("saved"); // trimmed as the server trims it
    expect(stepStatus(clean, "review")).toEqual({ kind: "saved" });
    expect(stepStatus(editOccasion(clean, "Harvest Home"), "review")).toEqual({ kind: "unsaved_changes" });
    expect(stepStatus(fresh, "review")).toEqual({ kind: "not_in_archive" });
    expect(stepStatus(clean, "review", READINGS)).toEqual({ kind: "not_in_archive" }); // before 5a-3
  });

  it("saveMode saves new, saves changes on the saved date, and saves a copy on another date or for an undated service", () => {
    const d = testDraft();
    expect(saveMode(d)).toBe("new");
    expect(saveMode(saved(d))).toBe("update");
    expect(saveMode(setDate(saved(d), "2026-10-11"))).toBe("copy");
    expect(saveMode(saved(d, null))).toBe("copy"); // a saved service with no date
  });
});

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CHURCH_IDS, churchProfile, DRAFT_NOW, lectionary, testDraft, USER_ID } from "@/test/fixtures";

import { draftToServicePayload } from "./mapping";
import {
  applyReadingSet,
  chooseReadingSet,
  editOccasion,
  editScriptureLines,
  setPick,
  setTranslation,
  shouldAutoApply,
} from "./readings";
import { corruptDraftKey, draftKey, type DraftV1 } from "./schema";
import { DraftStore, WRITE_DELAY_MS, type DraftNotice, type DraftStorage } from "./store";

const GRACE = churchProfile();
const KEY = draftKey(USER_ID, GRACE.id);

/** A Map-backed storage that records writes; `failWrites` makes every write fail (quota), `failKeys` only those keys'. */
function memoryStorage(initial: Record<string, string> = {}) {
  const data = new Map(Object.entries(initial));
  const writes: string[] = [];
  const storage: DraftStorage & { failWrites: boolean; failKeys: Set<string> } = {
    failWrites: false,
    failKeys: new Set(),
    read: (key) => data.get(key) ?? null,
    write: (key, value) => {
      writes.push(key);
      if (storage.failWrites || storage.failKeys.has(key)) return false;
      data.set(key, value);
      return true;
    },
    remove: (key) => {
      data.delete(key);
    },
  };
  return { storage, data, writes };
}

/** A clock the test moves by hand, starting at DRAFT_NOW (Tuesday, September 29, 2026). */
function clock(start = DRAFT_NOW) {
  let t = start.getTime();
  return { now: () => new Date(t), advance: (ms: number) => (t += ms) };
}

function makeStore(storage: DraftStorage, now = clock().now) {
  const notices: DraftNotice[] = [];
  const store = new DraftStore({ userId: USER_ID, church: GRACE, storage, now, notify: (n) => notices.push(n) });
  return { store, notices };
}

function stored(data: Map<string, string>, key = KEY): DraftV1 {
  return JSON.parse(data.get(key) ?? "null") as DraftV1;
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("DraftStore load (F §4.6 Versioning)", () => {
  it("starts a fresh draft under the user and church key and writes it 400 ms after start", () => {
    const { storage, data } = memoryStorage();
    const { store, notices } = makeStore(storage);
    expect(store.key).toBe(`wsb:draft:${USER_ID}:${GRACE.id}`);
    expect(store.getSnapshot()).toMatchObject({ persistence: "ok", draft: { readings: { date_iso: "2026-10-04" } } });
    expect(data.size).toBe(0); // nothing is written during a render
    store.start();
    vi.advanceTimersByTime(WRITE_DELAY_MS - 1);
    expect(data.size).toBe(0);
    vi.advanceTimersByTime(1);
    expect(stored(data)).toEqual(store.getSnapshot().draft);
    expect(notices).toEqual([]);
  });

  it("loads a valid stored draft as it is and writes nothing", () => {
    const saved = editOccasion(testDraft(), "Harvest");
    const { storage, writes } = memoryStorage({ [KEY]: JSON.stringify(saved) });
    const { store } = makeStore(storage);
    store.start();
    vi.runAllTimers();
    expect(store.getSnapshot().draft).toEqual(saved);
    expect(writes).toEqual([]);
  });

  it("backs up a draft it cannot restore, starts fresh and reports it once", () => {
    for (const raw of ["{not json", JSON.stringify({ ...testDraft(), version: 2 }), JSON.stringify({ version: 1 })]) {
      const { storage, data } = memoryStorage({ [KEY]: raw });
      const { store, notices } = makeStore(storage);
      store.start();
      store.start(); // StrictMode runs effects twice
      expect(data.get(corruptDraftKey(USER_ID, GRACE.id))).toBe(raw);
      expect(notices).toEqual(["restore_failed"]);
      vi.runAllTimers();
      expect(stored(data).readings.fields_origin).toBe("empty");
      expect(stored(data).save_key).toBe(store.getSnapshot().draft.save_key);
    }

    // The backup cannot be written (quota): the unrestorable draft stays in the main key until the user edits.
    const raw = JSON.stringify({ ...testDraft(), version: 2 });
    const { storage, data } = memoryStorage({ [KEY]: raw, [corruptDraftKey(USER_ID, GRACE.id)]: "older backup" });
    storage.failKeys.add(corruptDraftKey(USER_ID, GRACE.id));
    const { store, notices } = makeStore(storage);
    store.start();
    vi.runAllTimers();
    expect(data.get(KEY)).toBe(raw);
    expect(data.has(corruptDraftKey(USER_ID, GRACE.id))).toBe(false); // the old backup was being replaced anyway
    expect(notices).toEqual(["restore_failed"]);
    store.update((d) => editOccasion(d, "Harvest"));
    vi.runAllTimers();
    expect(stored(data).readings.occasion).toBe("Harvest");
  });

  it("normalizes a stale pick left by a refresh while the textarea had focus, and the payload already sends \"\"", () => {
    const filled = applyReadingSet(testDraft(), lectionary("2026-10-04"), 0);
    const stale = editScriptureLines(setPick(filled, "ot", "Psalm 80:7-15"), "Isaiah 5:1-7\nPhilippians 3:4b-14");
    expect(draftToServicePayload(stale).selected_ot_ref).toBe("");
    const { storage, data } = memoryStorage({ [KEY]: JSON.stringify(stale) });
    const { store } = makeStore(storage);
    expect(store.getSnapshot().draft.readings.selected_ot_ref).toBe("");
    store.start();
    vi.runAllTimers();
    expect(stored(data).readings.selected_ot_ref).toBe("");
  });

  it("rolls a pristine draft's passed default date forward, even with a default benediction, but not an edited one", () => {
    const pastPristine = testDraft((d) => ({
      ...d,
      liturgy: {
        ...d.liturgy,
        cards: { ...d.liturgy.cards, benediction: { enabled: true, text: "Halverson", origin: "default" } },
      },
    }));
    const tenDaysLater = clock(new Date(DRAFT_NOW.getTime() + 10 * 86_400_000)); // Friday, October 9
    const rolled = makeStore(memoryStorage({ [KEY]: JSON.stringify(pastPristine) }).storage, tenDaysLater.now).store;
    expect(rolled.getSnapshot().draft.readings).toMatchObject({ date_iso: "2026-10-11", date_origin: "default" });
    expect(rolled.getSnapshot().draft.liturgy.include_communion).toBe(false);
    // Stamped just after the stored draft, not now, so a newer unwritten edit from another tab still wins.
    const rolledAt = new Date(Date.parse(pastPristine.updated_at) + 1).toISOString();
    expect(rolled.getSnapshot().draft.updated_at).toBe(rolledAt);
    const olderTabEdit = {
      ...editOccasion(pastPristine, "Harvest"),
      updated_at: new Date(Date.parse(rolledAt) + 86_400_000).toISOString(), // a day later, still before now
    };
    rolled.handleStorageEvent(KEY, JSON.stringify(olderTabEdit));
    expect(rolled.getSnapshot().draft.readings.occasion).toBe("Harvest");

    const edited = editOccasion(pastPristine, "Harvest");
    const kept = makeStore(memoryStorage({ [KEY]: JSON.stringify(edited) }).storage, tenDaysLater.now).store;
    expect(kept.getSnapshot().draft.readings.date_iso).toBe("2026-10-04");
  });
});

describe("DraftStore roll-forward and owner answers Q2 and A", () => {
  it("keeps a passed default date when a reading set was chosen, and rolls one with only a translation picked", () => {
    const tenDaysLater = clock(new Date(DRAFT_NOW.getTime() + 10 * 86_400_000)); // Friday, October 9
    const filled = applyReadingSet(testDraft(), lectionary("2026-10-04"), 0);
    const chosen = chooseReadingSet(filled, lectionary("2026-10-04"), 1);
    const kept = makeStore(memoryStorage({ [KEY]: JSON.stringify(chosen) }).storage, tenDaysLater.now).store;
    expect(kept.getSnapshot().draft.readings.date_iso).toBe("2026-10-04");
    const { store } = makeStore(memoryStorage({ [KEY]: JSON.stringify(filled) }).storage, tenDaysLater.now);
    expect(store.getSnapshot().draft.readings.date_iso).toBe("2026-10-11"); // the automatic fill alone rolls
    // Owner answer A: a translation override does not hold the date back, and it is kept.
    const translated = setTranslation(filled, "kjv", "web");
    const rolled = makeStore(memoryStorage({ [KEY]: JSON.stringify(translated) }).storage, tenDaysLater.now).store;
    expect(rolled.getSnapshot().draft.readings).toMatchObject({ date_iso: "2026-10-11", translation: "kjv" });
  });
});

describe("DraftStore changes (S store.ts)", () => {
  it("debounces writes, bumps updated_at, and ignores a recipe that returns the same draft", () => {
    const { storage, data, writes } = memoryStorage({ [KEY]: JSON.stringify(testDraft()) });
    const time = clock();
    const { store } = makeStore(storage, time.now);
    store.start();
    const listener = vi.fn();
    store.subscribe(listener);

    store.update((d) => d);
    vi.runAllTimers();
    expect(writes).toEqual([]);
    expect(listener).not.toHaveBeenCalled();

    time.advance(1_000);
    store.update((d) => editOccasion(d, "Harv"));
    vi.advanceTimersByTime(200);
    store.update((d) => editOccasion(d, "Harvest"));
    vi.advanceTimersByTime(WRITE_DELAY_MS - 1);
    expect(writes).toEqual([]);
    vi.advanceTimersByTime(1);
    expect(writes).toEqual([KEY]);
    expect(stored(data).readings.occasion).toBe("Harvest");
    expect(stored(data).updated_at).toBe(time.now().toISOString());
    expect(listener).toHaveBeenCalledTimes(2);
  });

  it("applies each recipe to the latest draft, so an edit in the same tick survives an auto-fill", () => {
    const { storage } = memoryStorage();
    const { store } = makeStore(storage);
    const lect = lectionary("2026-10-04");
    store.update((d) => editOccasion(d, "Harvest Sunday"));
    store.update((d) => (shouldAutoApply(d, lect) ? applyReadingSet(d, lect, 0) : d));
    expect(store.getSnapshot().draft.readings).toMatchObject({ occasion: "Harvest Sunday", fields_origin: "user" });
  });

  it("setLastStep writes the step but leaves updated_at alone", () => {
    const saved = testDraft();
    const { storage, data } = memoryStorage({ [KEY]: JSON.stringify(saved) });
    const { store } = makeStore(storage);
    store.setLastStep("readings");
    vi.runAllTimers();
    expect(data.get(KEY)).toBe(JSON.stringify(saved)); // unchanged: already "readings"
    store.setLastStep("hymns");
    vi.runAllTimers();
    expect(stored(data)).toMatchObject({ last_step: "hymns", updated_at: saved.updated_at });
  });

  it("replace stores the next draft with normalized picks and a new updated_at", () => {
    const { storage, data } = memoryStorage();
    const time = clock();
    const { store } = makeStore(storage, time.now);
    time.advance(5_000);
    const next = setPick(testDraft(), "nt", "Matthew 21:33-46"); // no scripture lines: a stale pick
    store.replace(next);
    vi.runAllTimers();
    expect(stored(data)).toMatchObject({
      save_key: next.save_key,
      updated_at: time.now().toISOString(),
      readings: { selected_nt_ref: "" },
    });
  });

  it("switches to memory-only when a write fails, and reports it once", () => {
    const { storage, data } = memoryStorage();
    storage.failWrites = true;
    const { store, notices } = makeStore(storage);
    store.start();
    vi.runAllTimers();
    expect(store.getSnapshot().persistence).toBe("memory-only");
    store.update((d) => editOccasion(d, "Harvest"));
    store.flush();
    expect(notices).toEqual(["memory_only"]);
    expect(store.getSnapshot().draft.readings.occasion).toBe("Harvest"); // still in memory

    // Storage recovers: the next flush (pagehide, hide) retries the failed write.
    storage.failWrites = false;
    store.flush();
    expect(stored(data).readings.occasion).toBe("Harvest");
    expect(store.getSnapshot().persistence).toBe("ok");
  });

  it("adopts another tab's strictly newer draft (normalized) and ignores equal, foreign or broken ones", () => {
    const base = testDraft();
    const { storage, writes } = memoryStorage({ [KEY]: JSON.stringify(base) });
    const { store, notices } = makeStore(storage);
    const { handleStorageEvent } = store; // bound, like the other public methods
    store.update((d) => editOccasion(d, "Mine")); // a pending write
    const mine = store.getSnapshot().draft;

    handleStorageEvent(KEY, JSON.stringify({ ...mine, readings: { ...mine.readings, occasion: "Same time" } }));
    store.handleStorageEvent(draftKey(USER_ID, CHURCH_IDS.hope), JSON.stringify({ ...mine, church_id: CHURCH_IDS.hope }));
    store.handleStorageEvent(KEY, "{broken");
    store.handleStorageEvent(KEY, null);
    expect(store.getSnapshot().draft).toBe(mine);

    const filled = applyReadingSet(base, lectionary("2026-10-04"), 0);
    const theirs = {
      ...setPick(editScriptureLines(filled, "Isaiah 5:1-7"), "nt", "Matthew 21:33-46"),
      updated_at: new Date(Date.parse(mine.updated_at) + 1).toISOString(),
    };
    store.handleStorageEvent(KEY, JSON.stringify(theirs));
    expect(store.getSnapshot().draft).toEqual({ ...theirs, readings: { ...theirs.readings, selected_nt_ref: "" } });
    expect(notices).toEqual(["adopted"]);
    vi.runAllTimers();
    expect(writes).toEqual([]); // my pending write was dropped: theirs is newer
  });
});

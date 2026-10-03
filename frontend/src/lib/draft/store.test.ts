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
import { corruptDraftKey, draftKey, freshDraft, type DraftV1 } from "./schema";
import { DraftStore, WRITE_DELAY_MS, type DraftNotice, type DraftStorage } from "./store";
import { DEFAULT_BENEDICTION_FALLBACK } from "@/lib/liturgy/defaults";

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
    for (const raw of ["{not json", JSON.stringify({ ...testDraft(), version: 4 }), JSON.stringify({ version: 1 })]) {
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
    const raw = JSON.stringify({ ...testDraft(), version: 4 });
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
        cards: { ...d.liturgy.cards, benediction: { enabled: true, text: DEFAULT_BENEDICTION_FALLBACK, origin: "default" } },
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

describe("DraftStore roll-forward and the hymns step (owner answer 1, 2026-09-29)", () => {
  it("keeps a passed default date when a hymnal was chosen, and rolls one with only the switch or ideas changed", () => {
    const tenDaysLater = clock(new Date(DRAFT_NOW.getTime() + 10 * 86_400_000)); // Friday, October 9
    const hymns = (patch: Partial<DraftV1["hymns"]>) => testDraft((d) => ({ ...d, hymns: { ...d.hymns, ...patch } }));
    const load = (d: DraftV1) =>
      makeStore(memoryStorage({ [KEY]: JSON.stringify(d) }).storage, tenDaysLater.now).store.getSnapshot().draft;
    expect(load(hymns({ hymnal: "PH1990" })).readings.date_iso).toBe("2026-10-04");
    const pick = { hymn_id: "h1", title: "Amazing Grace", number: 649, hymnal: "GG2013" };
    const ideas = { for_date_iso: "2026-10-04", by_slot: { opening: [pick], response: [], closing: [] } };
    const rolled = load(hymns({ exclude_recent: false, alternatives: ideas }));
    expect(rolled.readings.date_iso).toBe("2026-10-11");
    expect(rolled.hymns).toMatchObject({ exclude_recent: false, alternatives: ideas }); // kept, and hidden by date
  });
});

describe("DraftStore roll-forward and the liturgy step (owner answer 1, 2026-09-30)", () => {
  it("keeps a passed default date when a card was switched, and rolls one whose Benediction follows the default", () => {
    const tenDaysLater = clock(new Date(DRAFT_NOW.getTime() + 10 * 86_400_000)); // Friday, October 9
    const card = (key: "prayers_of_the_people" | "benediction", patch: object) =>
      testDraft((d) => ({
        ...d,
        liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, [key]: { ...d.liturgy.cards[key], ...patch } } },
      }));
    const load = (d: DraftV1) =>
      makeStore(memoryStorage({ [KEY]: JSON.stringify(d) }).storage, tenDaysLater.now).store.getSnapshot().draft;
    expect(load(card("prayers_of_the_people", { enabled: true })).readings.date_iso).toBe("2026-10-04");
    expect(load(card("benediction", { text: "Go in peace.", origin: "default" })).readings.date_iso).toBe("2026-10-11");
  });
});

describe("DraftStore and the liturgy defaults (slice 4 spec, Draft store integration)", () => {
  function defaultsStore(storage: DraftStorage, now = clock().now) {
    return new DraftStore({ userId: USER_ID, church: GRACE, storage, now, liturgyDefaults: { defaultBenediction: DEFAULT_BENEDICTION_FALLBACK } });
  }

  it("fills a fresh draft's Benediction with the church default and follows a new default until the card is edited", () => {
    const { storage, data } = memoryStorage();
    const t = clock();
    const store = defaultsStore(storage, t.now);
    store.start();
    expect(store.getSnapshot().draft.liturgy.cards.benediction).toEqual({ enabled: true, text: DEFAULT_BENEDICTION_FALLBACK, origin: "default" });
    vi.advanceTimersByTime(WRITE_DELAY_MS);
    expect(stored(data).liturgy.cards.benediction.text).toBe(DEFAULT_BENEDICTION_FALLBACK);

    // An admin changes the default (6a) and the profile refetches: an automatic change, 1 ms after the draft.
    const before = store.getSnapshot().draft.updated_at;
    t.advance(60_000);
    store.setLiturgyDefaults({ defaultBenediction: "The Lord bless you and keep you." });
    const followed = store.getSnapshot().draft;
    expect(followed.liturgy.cards.benediction.text).toBe("The Lord bless you and keep you.");
    expect(followed.updated_at).toBe(new Date(Date.parse(before) + 1).toISOString());
    store.setLiturgyDefaults({ defaultBenediction: "The Lord bless you and keep you." });
    expect(store.getSnapshot().draft).toBe(followed); // the same default: nothing to do

    // Every change keeps the defaults: New service's fresh draft gets the default too.
    store.update((d) => ({ ...d, liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, benediction: { enabled: true, text: "Go in peace.", origin: "typed" } } } }));
    store.setLiturgyDefaults({ defaultBenediction: DEFAULT_BENEDICTION_FALLBACK });
    expect(store.getSnapshot().draft.liturgy.cards.benediction.text).toBe("Go in peace.");
    store.replace(freshDraft({ church: GRACE, user: { id: USER_ID }, now: t.now() }));
    expect(store.getSnapshot().draft.liturgy.cards.benediction).toEqual({ enabled: true, text: DEFAULT_BENEDICTION_FALLBACK, origin: "default" });
  });

  it("loads a stored draft with today's default and the date's communion, stamped just after the stored draft", () => {
    const old = testDraft((d) => ({
      ...d,
      updated_at: "2026-09-29T15:00:00.000Z",
      liturgy: { ...d.liturgy, include_communion: false }, // stored before 4b: the rule says on for October 4
    }));
    const { storage } = memoryStorage({ [KEY]: JSON.stringify(old) });
    const draft = defaultsStore(storage).getSnapshot().draft;
    expect(draft.liturgy.cards.benediction.text).toBe(DEFAULT_BENEDICTION_FALLBACK);
    expect(draft.liturgy.include_communion).toBe(true);
    expect(draft.updated_at).toBe("2026-09-29T15:00:00.001Z");
    // Without defaults (slice 2's tests), the store changes nothing.
    expect(makeStore(memoryStorage({ [KEY]: JSON.stringify(old) }).storage).store.getSnapshot().draft).toEqual(old);
  });

  it("gives an adopted draft the default in memory only, so a newer write from another tab still wins", () => {
    const { storage, writes } = memoryStorage();
    const store = defaultsStore(storage);
    store.start();
    vi.runAllTimers();
    writes.length = 0;
    const mine = store.getSnapshot().draft;
    const benediction = (d: DraftV1, text: string, origin: "default" | "typed"): DraftV1 => ({
      ...d,
      liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, benediction: { enabled: true, text, origin } } },
    });
    // The other tab wrote before its profile loaded: a blank Benediction still following the default.
    const theirs = { ...benediction(editOccasion(mine, "From the other tab"), "", "default"), updated_at: new Date(Date.parse(mine.updated_at) + 1).toISOString() };
    store.handleStorageEvent(KEY, JSON.stringify(theirs));
    const adopted = store.getSnapshot().draft;
    expect(adopted.readings.occasion).toBe("From the other tab");
    expect(adopted.liturgy.cards.benediction).toEqual({ enabled: true, text: DEFAULT_BENEDICTION_FALLBACK, origin: "default" });
    expect(adopted.updated_at).toBe(theirs.updated_at); // not stamped: the default is not an edit
    vi.runAllTimers();
    expect(writes).toEqual([]); // and not written back over the other tab's copy
    // The other tab then types its own Benediction, 1 ms later: adopted, the default does not outrank it.
    const typed = { ...benediction(theirs, "Go in peace.", "typed"), updated_at: new Date(Date.parse(theirs.updated_at) + 1).toISOString() };
    store.handleStorageEvent(KEY, JSON.stringify(typed));
    expect(store.getSnapshot().draft.liturgy.cards.benediction).toEqual({ enabled: true, text: "Go in peace.", origin: "typed" });
    expect(store.getSnapshot().draft.updated_at).toBe(typed.updated_at);
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

  it("replace writes at once, so a page that mounts next reads it (slice 5a-3: Services opens the builder)", () => {
    const { storage, data } = memoryStorage();
    const { store } = makeStore(storage);
    const next = { ...testDraft(), editing: { service_id: "s1", saved_at: "2026-10-01T14:42:00+00:00", date_iso: "2026-10-04" } };
    store.replace(next);
    expect(stored(data)).toMatchObject({ editing: next.editing, save_key: next.save_key }); // no timer run
    expect(makeStore(storage).store.getSnapshot().draft.editing).toEqual(next.editing);
  });

  it("never adopts a draft an older version of the app wrote, however new, and writes over it (slice 5a-3: an old tab)", () => {
    const { storage, data } = memoryStorage({ [KEY]: JSON.stringify(testDraft()) });
    const { store, notices } = makeStore(storage);
    store.update((d) => editOccasion(d, "Mine"));
    const mine = store.getSnapshot().draft;
    // An open tab still running version 1 code writes its fresh draft, a minute later.
    const old = JSON.stringify({ ...testDraft(), version: 1, updated_at: new Date(Date.parse(mine.updated_at) + 60_000).toISOString() });
    store.handleStorageEvent(KEY, old);
    data.set(KEY, old);
    store.syncFromStorage();
    expect(store.getSnapshot().draft).toBe(mine);
    store.flush();
    expect(stored(data)).toMatchObject({ version: 3, readings: { occasion: "Mine" } });
    expect(notices).toEqual([]);
  });

  it("puts its draft back over an old tab's with nothing to write, and a store loaded from the old tab's takes it (build review M3)", () => {
    const { storage, data } = memoryStorage({ [KEY]: JSON.stringify(testDraft()) });
    const builder = makeStore(storage).store;
    builder.update((d) => editOccasion(d, "Mine"));
    builder.flush();
    const mine = builder.getSnapshot().draft;
    // An open tab still running version 1 code writes its fresh draft, a minute later, with nothing pending here.
    data.set(KEY, JSON.stringify({ ...testDraft(), version: 1, updated_at: new Date(Date.parse(mine.updated_at) + 60_000).toISOString() }));
    // Services renders before the builder unmounts, so its store loads the old tab's draft...
    const services = makeStore(storage);
    expect(services.store.getSnapshot().draft.readings.occasion).toBe("");
    builder.flush(); // ...then the builder unmounts and flushes,
    expect(stored(data)).toMatchObject({ version: 3, readings: { occasion: "Mine" } });
    services.store.syncFromStorage({ quiet: true }); // and Services reads it back once mounted.
    expect(services.store.getSnapshot().draft).toMatchObject({ readings: { occasion: "Mine" }, updated_at: mine.updated_at });
    expect(services.notices).toEqual([]);
    // Once it has its own draft, the times decide again.
    data.set(KEY, JSON.stringify({ ...mine, readings: { ...mine.readings, occasion: "Older" }, updated_at: new Date(DRAFT_NOW.getTime() - 1000).toISOString() }));
    services.store.syncFromStorage();
    expect(services.store.getSnapshot().draft.readings.occasion).toBe("Mine");
    // A current-version draft is never written over with nothing pending.
    builder.flush();
    expect(stored(data).readings.occasion).toBe("Older");
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
    const { storage, writes, data } = memoryStorage({ [KEY]: JSON.stringify(base) });
    const { store, notices } = makeStore(storage);
    const { handleStorageEvent } = store; // bound, like the other public methods
    store.update((d) => editOccasion(d, "Mine")); // a pending write
    const mine = store.getSnapshot().draft;

    handleStorageEvent(KEY, JSON.stringify({ ...mine, readings: { ...mine.readings, occasion: "Same time" } }));
    store.handleStorageEvent(draftKey(USER_ID, CHURCH_IDS.hope), JSON.stringify({ ...mine, church_id: CHURCH_IDS.hope }));
    store.handleStorageEvent(KEY, "{broken");
    store.handleStorageEvent(KEY, null);
    store.syncFromStorage(); // shown again: the stored draft (base) is older than mine
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

    // Shown again (slice 2c): the stored draft is read directly, before its storage event arrives.
    const typed = {
      ...editOccasion(theirs, "Typed in the other tab"),
      updated_at: new Date(Date.parse(theirs.updated_at) + 1).toISOString(),
    };
    data.set(KEY, JSON.stringify(typed));
    store.syncFromStorage();
    expect(store.getSnapshot().draft.readings.occasion).toBe("Typed in the other tab");
    store.handleStorageEvent(KEY, JSON.stringify(typed)); // the late event is not newer
    expect(notices).toEqual(["adopted", "adopted"]);

    // A flush that finds a strictly newer stored draft (its event still on the way) adopts it instead of writing.
    store.update((d) => editOccasion(d, "Mine, stamped earlier")); // this clock is behind the other tab's
    const later = {
      ...editOccasion(typed, "Written just before my flush"),
      updated_at: new Date(Date.parse(typed.updated_at) + 1).toISOString(),
    };
    data.set(KEY, JSON.stringify(later));
    store.flush();
    expect(writes).toEqual([]);
    expect(store.getSnapshot().draft.readings.occasion).toBe("Written just before my flush");
    expect(notices).toEqual(["adopted", "adopted", "adopted"]);
  });
});

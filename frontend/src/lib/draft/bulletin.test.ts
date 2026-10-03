import { describe, expect, it } from "vitest";

import type { PreviousBulletin } from "@/lib/api/types";
import { serviceBody } from "@/lib/documents";
import { churchProfile, filledBulletinSettings, savedService, serviceBulletin, testDraft, USER_ID } from "@/test/fixtures";

import {
  applyCarry,
  bulletinFromService,
  bulletinPayload,
  bulletinStatus,
  followSaveMode,
  keepCarried,
  notChecked,
  notCheckedLine,
  printedNotFilledIn,
  setAnnouncement,
  setMusic,
  setPartLeader,
  setPastedText,
  setPerson,
  shouldCarry,
} from "./bulletin";
import { fingerprint } from "./fingerprint";
import { draftToServicePayload, markSaved, serviceToDraft } from "./mapping";
import { editScriptureLines, setDate, setPick } from "./readings";
import { keyForPost } from "./save-key";
import type { DraftV1 } from "./schema";
import { reviewStatus, saveMode } from "./status";

/** Last week's service (invented): the music and three announcements. */
function lastWeek(overrides: Partial<PreviousBulletin> = {}): PreviousBulletin {
  return {
    service_id: "s-last",
    service_date_iso: "2026-09-27",
    bulletin: serviceBulletin({
      prelude: { title: "Morning Voluntary", composer: "Pat Example" },
      announcements: {
        ...serviceBulletin().announcements,
        ushers: "Sam Sample",
        coffee_hour: "The Example family",
        prayer_concerns: "For all who are ill.",
      },
    }),
    ...overrides,
  };
}

const carried = (d: DraftV1 = testDraft()) => applyCarry(d, lastWeek(), d.readings.date_iso);

describe("carry forward (PR 2 planning answer 5)", () => {
  it("carries last week's music and announcements into a new draft once for its date, each marked to check", () => {
    const d = testDraft();
    expect(shouldCarry(d)).toBe(true);
    const c = carried(d);
    expect(c.bulletin).toMatchObject({
      prelude: { title: "Morning Voluntary", composer: "Pat Example" },
      announcements: { ushers: "Sam Sample", coffee_hour: "The Example family", prayer_concerns: "For all who are ill." },
      carried: ["prelude", "ushers", "coffee_hour", "prayer_concerns"],
      edited: [],
      carried_for: "2026-10-04",
    });
    expect(shouldCarry(c)).toBe(false); // once per date
    expect(applyCarry(c, lastWeek(), "2026-10-04")).toBe(c);
    expect(applyCarry(d, lastWeek(), "2026-10-11")).toBe(d); // the date moved meanwhile
    // Nothing saved before the date: nothing carries, and it is not looked up again for that date.
    const none = applyCarry(d, { service_id: null, service_date_iso: null, bulletin: serviceBulletin() }, "2026-10-04");
    expect(none.bulletin).toMatchObject({ carried: [], carried_for: "2026-10-04" });
  });

  it("carries again for a new date into every box not edited or kept, a box at a time (plan review fix M1)", () => {
    const moved = setDate(carried(), "2026-10-11", "user");
    expect(shouldCarry(moved)).toBe(true);
    const again = applyCarry(moved, lastWeek({ bulletin: serviceBulletin() }), "2026-10-11");
    expect(again.bulletin).toMatchObject({ prelude: { title: "" }, announcements: { ushers: "" }, carried: [] });
    // Typed, cleared or kept: that box stays as it is; the others still carry.
    let d = setAnnouncement(carried(), "coffee_hour", "The Sample family");
    d = keepCarried(setAnnouncement(d, "prayer_concerns", ""), "ushers");
    expect(d.bulletin.edited).toEqual(["ushers", "coffee_hour", "prayer_concerns"]);
    const next = applyCarry(setDate(d, "2026-10-11", "user"), lastWeek({ bulletin: serviceBulletin({ prelude: { title: "Festive Postlude", composer: "" } }) }), "2026-10-11");
    expect(next.bulletin).toMatchObject({
      prelude: { title: "Festive Postlude", composer: "" },
      announcements: { ushers: "Sam Sample", coffee_hour: "The Sample family", prayer_concerns: "" },
      carried: ["prelude"],
    });
    // A box typed before the carry arrives (or after a failed lookup) does not stop the others.
    const early = setAnnouncement(testDraft(), "other", "Typed before any carry.");
    expect(shouldCarry(early)).toBe(true);
    expect(carried(early).bulletin).toMatchObject({
      announcements: { other: "Typed before any carry.", ushers: "Sam Sample" },
      carried: ["prelude", "ushers", "coffee_hour", "prayer_concerns"],
    });
    // Every box touched: nothing is left to carry.
    const all = (["prelude", "postlude"] as const).reduce(
      (x, piece) => setMusic(x, piece, "title", "Typed"),
      (["ushers", "deacon", "coffee_hour", "activities", "prayer_concerns", "collection", "other"] as const).reduce(
        (x, key) => setAnnouncement(x, key, "Typed"),
        testDraft(),
      ),
    );
    expect(shouldCarry(all)).toBe(false);
    // The people, a part's leader and pasted text never stop it: they never carry.
    expect(shouldCarry(setPerson(setPartLeader(testDraft(), "sermon", "Rev. Guest"), "organist", ""))).toBe(true);
  });

  it("never carries into a saved service, a draft without a real date, or while a save's outcome is unknown (plan review fix I2)", () => {
    expect(shouldCarry({ ...testDraft(), editing: { service_id: "s1", saved_at: "x", date_iso: "2026-10-04" } })).toBe(false);
    expect(shouldCarry(setDate(testDraft(), "", "user"))).toBe(false);
    const pending = { ...testDraft(), save_key_fingerprint: "the body of a POST whose answer was lost" };
    expect(shouldCarry(pending)).toBe(false);
    expect(carried(pending)).toBe(pending);
  });
});

describe("Save as new service (plan review fix I4)", () => {
  const saved = serviceBulletin({
    prelude: { title: "Morning Voluntary", composer: "Pat Example" },
    people: { worship_leader: "Rev. Guest", liturgist: null, organist: null },
    leaders: { sermon: "Rev. Guest" },
    announcements: { ...serviceBulletin().announcements, coffee_hour: "The Example family" },
    reading_text: { ot: "", nt: "Pasted text." },
    unchecked: ["coffee_hour"],
  });
  const opened = (): DraftV1 => ({
    ...testDraft(),
    editing: { service_id: "s-last", saved_at: "2026-09-27T12:00:00+00:00", date_iso: "2026-10-04" },
    bulletin: bulletinFromService(saved, savedService()),
  });

  it("on another date marks the music and announcements to check and starts this week's people, leaders and texts empty", () => {
    const d = opened();
    expect(followSaveMode(d)).toBe(d); // the saved date: nothing changes
    const copy = followSaveMode(setDate(d, "2026-10-11", "user"));
    expect(copy.bulletin).toMatchObject({
      prelude: saved.prelude,
      announcements: { coffee_hour: "The Example family" },
      people: { worship_leader: null, liturgist: null, organist: null },
      leaders: {},
      pasted: {},
      carried: ["prelude", "coffee_hour"],
      set_aside: { people: saved.people, leaders: saved.leaders, pasted: { "Matthew 21:33-46": "Pasted text." }, carried: ["coffee_hour"] },
    });
    expect(followSaveMode(copy)).toBe(copy);
    expect(bulletinPayload(copy).unchecked).toEqual(["prelude", "coffee_hour"]);
    // Saved as the new service: what was set aside belongs to the other one.
    const savedCopy = markSaved(copy, savedService({ service_date_iso: "2026-10-11" }), "fp");
    expect(savedCopy.bulletin.set_aside).toBeNull();
    expect(followSaveMode(savedCopy)).toBe(savedCopy);
  });

  it("puts back what it set aside on the saved date, keeping anything typed meanwhile, and sets nothing aside during an unknown save", () => {
    let copy = followSaveMode(setDate(opened(), "2026-10-11", "user"));
    copy = setAnnouncement(setPerson(copy, "organist", "Jordan Doe"), "coffee_hour", "The Sample family");
    const back = followSaveMode(setDate(copy, "2026-10-04", "user"));
    expect(back.bulletin).toMatchObject({
      people: { worship_leader: "Rev. Guest", liturgist: null, organist: "Jordan Doe" },
      leaders: { sermon: "Rev. Guest" },
      pasted: { "Matthew 21:33-46": "Pasted text." },
      announcements: { coffee_hour: "The Sample family" },
      carried: [], // the coffee hour was edited meanwhile
      set_aside: null,
    });
    const pending = { ...setDate(opened(), "2026-10-11", "user"), save_key_fingerprint: "fp" };
    expect(followSaveMode(pending)).toBe(pending);
  });
});

describe("Save as new service after a save whose outcome is unknown (2b-2 build review C1, M5)", () => {
  const saved = savedService({
    bulletin: serviceBulletin({
      people: { worship_leader: "Rev. Guest", liturgist: null, organist: null },
      leaders: { sermon: "Rev. Guest" },
      reading_text: { ot: "", nt: "Pasted Matthew text" },
      announcements: { ...serviceBulletin().announcements, prayer_concerns: "For Sam." },
    }),
  });
  const open = () => serviceToDraft(saved, { church: churchProfile(), user: { id: USER_ID } });

  it("puts back the set-aside fields on the saved date while the POST's key is pending, so Save changes keeps them", () => {
    let d = open();
    const before = serviceBody(d).bulletin;
    d = followSaveMode(setDate(d, "2026-10-11", "user")); // Review: Save as new service
    expect(d.bulletin.set_aside).not.toBeNull();
    d = keyForPost(d, fingerprint(draftToServicePayload(d))); // the POST's answer was lost
    const back = followSaveMode(setDate(d, "2026-10-04", "user")); // back to the saved date
    expect(back.bulletin.set_aside).toBeNull();
    expect(saveMode(back)).toBe("update");
    expect(reviewStatus(back)).toBe("saved");
    const put = serviceBody(back).bulletin; // what Save changes sends
    expect(put).toEqual(before);
    expect(put?.people.worship_leader).toBe("Rev. Guest");
    expect(put?.leaders).toEqual({ sermon: "Rev. Guest" });
    expect(put?.reading_text.nt).toBe("Pasted Matthew text");
  });

  it("markSaved keeps the set-aside fields after a save over the same service and drops them after a new one", () => {
    let d = followSaveMode(setDate(open(), "2026-10-11", "user"));
    d = setDate(d, "2026-10-04", "user"); // set aside, then saved over the same service before Review ran again
    const put = markSaved(d, saved, fingerprint(draftToServicePayload(d)));
    expect(put.bulletin.set_aside).toEqual(d.bulletin.set_aside);
    const restored = followSaveMode(put);
    expect(restored.bulletin.people.worship_leader).toBe("Rev. Guest");
    expect(restored.bulletin.pasted).toEqual({ "Matthew 21:33-46": "Pasted Matthew text" });
    const copy = followSaveMode(setDate(open(), "2026-10-11", "user"));
    const posted = markSaved(copy, savedService({ id: "s-new", service_date_iso: "2026-10-11" }), "fp");
    expect(posted.bulletin.set_aside).toBeNull();
  });

  it("an undated saved service does not enter copy mode on open", () => {
    const d = serviceToDraft(savedService({ service_date_iso: null, service_date: "" }), {
      church: churchProfile(),
      user: { id: USER_ID },
    });
    expect(d.editing?.date_iso).toBeNull();
    expect(followSaveMode(d)).toBe(d);
  });
});

describe("editing the Bulletin step", () => {
  it("an edit or Keep as is clears a box's From last week; the other boxes keep theirs", () => {
    let d = carried();
    d = setMusic(d, "prelude", "composer", "Pat Example, arr.");
    d = keepCarried(d, "ushers");
    expect(d.bulletin.carried).toEqual(["coffee_hour", "prayer_concerns"]);
    expect(d.bulletin.announcements.ushers).toBe("Sam Sample");
    expect(notChecked(d)).toEqual(["coffee hour", "prayers and concerns"]);
    expect(notCheckedLine(notChecked(d))).toBe("From last week, not checked yet: coffee hour, prayers and concerns.");
    expect(bulletinStatus(d)).toEqual({ kind: "to_check", count: 2 });
    expect(bulletinStatus(testDraft())).toEqual({ kind: "optional" });
    expect(setAnnouncement(d, "deacon", "")).toBe(d); // no change, same draft
  });

  it("sends the fields trimmed, the people as set, the part leaders with a name and the pasted text of the readings printed", () => {
    let d = editScriptureLines(testDraft(), "Isaiah 5:1-7\nPsalm 80:7-15\nPhilippians 3:4b-14\nMatthew 21:33-46");
    d = setMusic(d, "postlude", "title", "  Festive Postlude ");
    d = setPerson(setPerson(d, "worship_leader", " Rev. Guest "), "liturgist", "");
    d = setPartLeader(setPartLeader(setPartLeader(d, "sermon", "Pat Example "), "offering", "x"), "offering", "");
    d = setPastedText(d, "Philippians 3:4b-14", " Pasted for the NT. ");
    d = setPastedText(d, "Psalm 23", "For a reading no longer chosen.");
    d = setAnnouncement(d, "activities", " Tuesday: Bible study.\nWednesday: Choir. ");
    const p = bulletinPayload(d);
    expect(p.postlude).toEqual({ title: "Festive Postlude", composer: "" });
    expect(p.people).toEqual({ worship_leader: "Rev. Guest", liturgist: "", organist: null });
    expect(p.leaders).toEqual({ sermon: "Pat Example" });
    expect(p.announcements.activities).toBe("Tuesday: Bible study.\nWednesday: Choir.");
    expect(p.reading_text).toEqual({ ot: "", nt: "Pasted for the NT." });
    expect(p.unchecked).toEqual([]);
    expect(bulletinPayload(carried()).unchecked).toEqual(["prelude", "ushers", "coffee_hour", "prayer_concerns"]);
    // Another NT pick: its own box, empty; the text pasted for Philippians stays in the draft.
    const other = setPick(d, "nt", "Matthew 21:33-46");
    expect(bulletinPayload(other).reading_text.nt).toBe("");
    expect(bulletinPayload(setPick(other, "nt", "Philippians 3:4b-14")).reading_text.nt).toBe("Pasted for the NT.");
  });

  it("opens a saved service's bulletin as it was saved, its pasted text under the reading's reference, its unchecked boxes marked again", () => {
    const saved = serviceBulletin({
      people: { worship_leader: null, liturgist: "Sam Sample", organist: null },
      leaders: { sermon: "Rev. Guest" },
      reading_text: { ot: "", nt: "Pasted text." },
      unchecked: ["coffee_hour", "prelude"],
    });
    const b = bulletinFromService(saved, savedService());
    expect(b).toMatchObject({ people: saved.people, leaders: saved.leaders, carried: ["prelude", "coffee_hour"], edited: [], carried_for: null });
    expect(bulletinFromService(serviceBulletin(), savedService()).carried).toEqual([]);
    expect(b.pasted).toEqual({ "Matthew 21:33-46": "Pasted text." }); // savedService picks the Gospel
  });
});

describe("printedNotFilledIn (PR 2 planning answer 3)", () => {
  it("lists the blank standing fields, this week's people as changed, then the prelude, postlude and announcements", () => {
    const settings = filledBulletinSettings({ phone: "", organist: "" });
    expect(printedNotFilledIn(settings, testDraft())).toEqual(["phone", "organist", "prelude", "postlude", "announcements"]);
    let d = setPerson(setPerson(testDraft(), "organist", "Jordan Doe"), "liturgist", "");
    d = setMusic(setAnnouncement(d, "deacon", "Alex Example"), "prelude", "title", "Morning Voluntary");
    expect(printedNotFilledIn(settings, d)).toEqual(["phone", "liturgist", "postlude"]);
    expect(printedNotFilledIn(undefined, d)).toEqual(["postlude"]); // settings still loading
  });
});

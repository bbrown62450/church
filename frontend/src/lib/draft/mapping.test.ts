import { describe, expect, it } from "vitest";

import { churchProfile, hymnId, lectionary, savedService, SERVICE_ID, serviceBulletin, testDraft, USER_ID } from "@/test/fixtures";

import { keepCarried, setAnnouncement, setPastedText } from "./bulletin";
import { fingerprint } from "./fingerprint";
import { draftToServicePayload, markSaved, serviceToDraft } from "./mapping";
import { applyReadingSet, editScriptureLines, setPick, showAvailableBanner } from "./readings";
import type { DraftV1 } from "./schema";
import { isDirty, reviewStatus, saveMode, stillNeeded } from "./status";
import { DEFAULT_BENEDICTION_FALLBACK } from "@/lib/liturgy/defaults";
import { editCardText, setCommunion } from "@/lib/liturgy/cards";

const OPEN_AT = new Date(Date.UTC(2026, 9, 2, 13, 0)); // Friday, October 2, 2026
const opened = (service = savedService()) =>
  serviceToDraft(service, { church: churchProfile(), user: { id: USER_ID }, now: OPEN_AT });

describe("draftToServicePayload (slice 5a-3)", () => {
  it("maps a fresh draft to the ServiceDraft shape", () => {
    expect(draftToServicePayload(testDraft())).toEqual({
      service_date_iso: "2026-10-04",
      occasion: "",
      scriptures: [],
      hymns: { opening: null, response: null, closing: null },
      liturgy: { benediction: DEFAULT_BENEDICTION_FALLBACK }, // the church default (slice 4b)
      sermon_title: "",
      selected_ot_ref: "",
      selected_nt_ref: "",
      include_communion: true,
      custom_elements: [],
      hymnal: null,
    });
  });

  it("trims and drops blank lines, keeps enabled non-empty cards, slot-keyed hymns and elements without ids", () => {
    const d: DraftV1 = testDraft((base) => {
      const lines = editScriptureLines(base, "  Isaiah 5:1-7 \n\n   \nPsalm 80:7-15");
      return {
        ...lines,
        hymns: {
          ...lines.hymns,
          hymnal: "GG2013",
          slots: { ...lines.hymns.slots, response: { hymn_id: "h1", title: "Amazing Grace", number: 649, hymnal: "GG2013" } },
        },
        liturgy: {
          ...lines.liturgy,
          cards: {
            ...lines.liturgy.cards,
            call_to_worship: { enabled: true, text: "Come, let us worship.", origin: "typed" },
            opening_prayer: { enabled: false, text: "Hidden", origin: "typed" },
            assurance: { enabled: true, text: "   ", origin: "typed" },
          },
          custom_elements: [{ id: "x1", label: "Anthem", text: "Choir", insert_after: "assurance" }],
        },
      };
    });
    const payload = draftToServicePayload(d);
    expect(payload.scriptures).toEqual(["Isaiah 5:1-7", "Psalm 80:7-15"]);
    expect(payload.liturgy).toEqual({ call_to_worship: "Come, let us worship.", benediction: DEFAULT_BENEDICTION_FALLBACK });
    expect(payload.hymns.response).toEqual({ hymn_id: "h1", title: "Amazing Grace", number: 649, hymnal: "GG2013" });
    expect(payload.hymns.opening).toBeNull();
    expect(payload.hymnal).toBe("GG2013");
    expect(payload.custom_elements).toEqual([{ label: "Anthem", text: "Choir", insert_after: "assurance" }]);
  });

  it("sends only picks that are still options, whatever the stored draft holds", () => {
    const filled = applyReadingSet(testDraft(), lectionary("2026-10-04"), 0);
    const picked = setPick(setPick(filled, "ot", "Psalm 80:7-15"), "nt", "Matthew 21:33-46");
    expect(draftToServicePayload(picked)).toMatchObject({
      selected_ot_ref: "Psalm 80:7-15",
      selected_nt_ref: "Matthew 21:33-46",
    });
    // The Psalm line deleted while the textarea had focus: the stored pick is stale.
    const stale = editScriptureLines(picked, "Isaiah 5:1-7\nPhilippians 3:4b-14\nMatthew 21:33-46");
    expect(stale.readings.selected_ot_ref).toBe("Psalm 80:7-15");
    expect(draftToServicePayload(stale)).toMatchObject({ selected_ot_ref: "", selected_nt_ref: "Matthew 21:33-46" });
  });

  it("trims every text as the server does and leaves out a custom element without a label", () => {
    let d = { ...testDraft(), readings: { ...testDraft().readings, occasion: "  Harvest " } };
    d = editCardText(d, "call_to_worship", "  Come, let us worship.\n");
    d = { ...d, liturgy: { ...d.liturgy, sermon_title: " Living Water ", custom_elements: [
      { id: "a", label: " Anthem ", text: " Choir\n", insert_after: "sermon" },
      { id: "b", label: "   ", text: "No label", insert_after: "end" },
    ] } };
    expect(draftToServicePayload(d)).toMatchObject({
      occasion: "Harvest",
      liturgy: { call_to_worship: "Come, let us worship." },
      sermon_title: "Living Water",
      custom_elements: [{ label: "Anthem", text: "Choir", insert_after: "sermon" }],
    });
  });
});

describe("serviceToDraft and markSaved (slice 5a-3; F §4.6 Loading an archived service)", () => {
  it("opens a saved service as a new draft that is already Saved, on Review, for that date", () => {
    const d = opened();
    expect(d).toMatchObject({
      user_id: USER_ID,
      church_id: churchProfile().id,
      created_at: OPEN_AT.toISOString(),
      last_step: "review",
      save_key_fingerprint: null,
      version: 4,
      editing: { service_id: SERVICE_ID, saved_at: "2026-10-01T14:42:00.123456+00:00", date_iso: "2026-10-04" },
      readings: {
        date_iso: "2026-10-04",
        date_origin: "archive",
        reading_set: null,
        fields_origin: "archive",
        occasion: "World Communion Sunday",
        scriptures: ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"],
        selected_ot_ref: "",
        selected_nt_ref: "Matthew 21:33-46",
        translation: null,
      },
      hymns: {
        hymnal: "GG2013",
        exclude_recent: true,
        alternatives: null,
        slots: {
          opening: { hymn_id: hymnId(1), title: "Holy, Holy, Holy! Lord God Almighty", number: 1, hymnal: "GG2013" },
          response: null,
          closing: { hymn_id: null, title: "Old Favorite", number: 12, hymnal: "PH1990" }, // not in the hymnal
        },
      },
      liturgy: { sermon_title: "Living Water", include_communion: true, communion_origin: "archive" },
    });
    expect(d.save_key).not.toBe(opened().save_key);
    expect(d.liturgy.cards.call_to_worship).toEqual({ enabled: true, text: "Leader: Come. People: We come.", origin: "archive" });
    expect(d.liturgy.cards.benediction).toEqual({ enabled: true, text: "Go in peace.", origin: "archive" });
    expect(d.liturgy.cards.opening_prayer).toEqual({ enabled: false, text: "", origin: "empty" });
    expect(d.liturgy.custom_elements).toEqual([{ id: expect.any(String), label: "Anthem", text: "Choir", insert_after: "sermon" }]);
    expect(isDirty(d)).toBe(false);
    expect(reviewStatus(d)).toBe("saved");
    expect(saveMode(d)).toBe("update");
    expect(d.saved_fingerprint).toBe(fingerprint(draftToServicePayload(d)));
    expect(stillNeeded(d).filter((item) => item.step === "hymns")).toEqual([
      { step: "hymns", message: "No Response hymn", action: "Choose one" },
      { step: "hymns", message: "Old Favorite isn't in your hymnal", action: "Choose a replacement" },
    ]);
    // Owner answer 5: no "Readings for … are available" while the date is the saved date; it shows on another date.
    const sets = lectionary("2026-10-04", { reading_sets: [{ name: "Other", source: "merged", scriptures: ["Genesis 1:1"] }] });
    expect(showAvailableBanner(d, sets)).toBe(false);
    const moved = { ...d, readings: { ...d.readings, date_iso: "2026-10-11", date_origin: "user" as const } };
    expect(showAvailableBanner(moved, { ...sets, date: "2026-10-11" })).toBe(true);
    expect(showAvailableBanner({ ...moved, readings: { ...moved.readings, date_iso: "2026-10-04" } }, sets)).toBe(false); // back on the saved date
  });

  it("opens an undated service on the next Sunday, keeps every element, and adds no Benediction it lacks", () => {
    const d = opened(
      savedService({
        service_date_iso: null,
        service_date: "",
        liturgy: {},
        custom_elements: [{ label: "Old place", text: "", insert_after: "bogus" as "end" }],
      }),
    );
    expect(d.readings).toMatchObject({ date_iso: "2026-10-04", date_origin: "default", fields_origin: "archive" });
    expect(d.editing?.date_iso).toBeNull();
    expect(saveMode(d)).toBe("copy");
    expect(d.liturgy.cards.benediction).toEqual({ enabled: false, text: "", origin: "empty" }); // no church default added
    expect(d.liturgy.custom_elements[0]).toMatchObject({ label: "Old place", insert_after: "end" });
    expect(isDirty(d)).toBe(false);
  });

  it("opens a saved service's bulletin fields Saved, and an edit to them is an unsaved change (PR 2b)", () => {
    const bulletin = serviceBulletin({
      prelude: { title: "Morning Voluntary", composer: "Pat Example" },
      people: { worship_leader: "Rev. Guest", liturgist: null, organist: "" },
      leaders: { sermon: "Rev. Guest" },
      reading_text: { ot: "", nt: "Pasted text." },
      unchecked: ["prelude"],
    });
    const d = opened(savedService({ bulletin }));
    const { cover_image_id: noPicture, ...payload } = bulletin;
    expect(noPicture).toBeNull();
    expect(draftToServicePayload(d).bulletin).toEqual(payload); // no picture: left out of the payload (PR 3b)
    expect(reviewStatus(d)).toBe("saved");
    expect(d.bulletin.carried).toEqual(["prelude"]); // still to check, on any device (plan review fix I3)
    expect(reviewStatus(keepCarried(d, "prelude"))).toBe("unsaved_changes");
    expect(reviewStatus(setAnnouncement(d, "coffee_hour", "The Example family"))).toBe("unsaved_changes");
    expect(reviewStatus(setPastedText(d, "Matthew 21:33-46", ""))).toBe("unsaved_changes");
    // Nothing filled in: no bulletin in the payload, so a draft saved before PR 2b keeps its fingerprint.
    expect("bulletin" in draftToServicePayload(opened())).toBe(false);
  });

  it("markSaved records the save and keeps a default Benediction and communion as saved (owner answer 4)", () => {
    const d = testDraft((base) => ({ ...base, readings: { ...base.readings, occasion: "Harvest" } }));
    expect(d.liturgy.cards.benediction.origin).toBe("default");
    const fp = fingerprint(draftToServicePayload(d));
    const saved = markSaved(d, savedService({ saved_at: "2026-10-02T13:00:00+00:00" }), fp);
    expect(saved.editing).toEqual({ service_id: SERVICE_ID, saved_at: "2026-10-02T13:00:00+00:00", date_iso: "2026-10-04" });
    expect(saved.saved_fingerprint).toBe(fp);
    expect(saved.liturgy.cards.benediction).toEqual({ enabled: true, text: DEFAULT_BENEDICTION_FALLBACK, origin: "archive" });
    expect(saved.liturgy.communion_origin).toBe("archive");
    expect(reviewStatus(saved)).toBe("saved");
    // A blank default Benediction becomes an empty card; communion the user set stays the user's.
    const blank = testDraft((base) => setCommunion({
      ...base,
      liturgy: { ...base.liturgy, cards: { ...base.liturgy.cards, benediction: { enabled: true, text: "", origin: "default" } } },
    }, false));
    const after = markSaved(blank, savedService(), fingerprint(draftToServicePayload(blank)));
    expect(after.liturgy.cards.benediction.origin).toBe("empty");
    expect(after.liturgy.communion_origin).toBe("user");
  });
});

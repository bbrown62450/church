/**
 * The Affirmation of Faith in the draft (affirmation spec, "Data shape"): the
 * card's transitions, following the church default, what is sent and
 * fingerprinted (the Apostles' Creed switched on is left out of the payload,
 * so a draft saved before the change stays "Saved"), opening and saving a
 * service, "Nothing the user would lose" and the summary line.
 */
import { describe, expect, it } from "vitest";

import { documentRequest, savedCopyFingerprint, serviceBody } from "@/lib/documents";
import { followSaveMode } from "@/lib/draft/bulletin";
import { draftToServicePayload, markSaved, serviceToDraft } from "@/lib/draft/mapping";
import { setDate } from "@/lib/draft/readings";
import { isPristine, reviewStatus, saveMode } from "@/lib/draft/status";
import { churchProfile, DRAFT_NOW, savedService, testDraft, USER_ID } from "@/test/fixtures";

import {
  editAffirmationText,
  restoreAffirmationDefault,
  setAffirmationChoice,
  setAffirmationInclude,
} from "./cards";
import { applyLiturgyDefaults, DEFAULT_BENEDICTION_FALLBACK } from "./defaults";
import { affirmationSummary } from "./summary";

const OWN = "We trust in God the Holy Spirit.";
const NICENE_DEFAULT = { choice: "nicene", text: "" } as const;
const defaults = (defaultAffirmation = NICENE_DEFAULT) => ({ defaultBenediction: DEFAULT_BENEDICTION_FALLBACK, defaultAffirmation });

describe("the Affirmation of Faith card (affirmation spec)", () => {
  it("makes the card the member's own on any change, and Use church default follows the default again", () => {
    const d = testDraft();
    const off = setAffirmationInclude(d, false);
    expect(off.liturgy.affirmation).toEqual({ include: false, choice: "apostles", text: "", origin: "user" });
    expect(setAffirmationInclude(off, false)).toBe(off); // nothing changes: the same draft
    const own = editAffirmationText(setAffirmationChoice(d, "own"), OWN);
    expect(own.liturgy.affirmation).toEqual({ include: true, choice: "own", text: OWN, origin: "user" });
    // The own text stays in the draft while a creed is picked, so switching back finds it.
    expect(setAffirmationChoice(setAffirmationChoice(own, "nicene"), "own").liturgy.affirmation.text).toBe(OWN);
    expect(restoreAffirmationDefault(own, { choice: "own", text: "Church text." }).liturgy.affirmation).toEqual({
      include: true, choice: "own", text: "Church text.", origin: "default" });
  });

  it("follows the church default while the origin is default, and never after a change", () => {
    const d = testDraft();
    expect(applyLiturgyDefaults(d, defaults()).liturgy.affirmation).toEqual({
      include: true, choice: "nicene", text: "", origin: "default" });
    const followed = applyLiturgyDefaults(d, defaults());
    expect(applyLiturgyDefaults(followed, defaults())).toBe(followed);
    const mine = setAffirmationChoice(d, "own");
    expect(applyLiturgyDefaults(mine, defaults()).liturgy.affirmation).toEqual(mine.liturgy.affirmation);
    expect(applyLiturgyDefaults(d, { defaultBenediction: DEFAULT_BENEDICTION_FALLBACK })).toBe(d); // no default given
  });

  it("leaves the Apostles' Creed switched on out of the payload, and always sends it in the body", () => {
    const d = testDraft();
    expect("affirmation" in draftToServicePayload(d)).toBe(false);
    expect(documentRequest(d, "bulletin").service.affirmation).toEqual({ include: true, choice: "apostles", text: "" });
    expect(draftToServicePayload(setAffirmationInclude(d, false)).affirmation).toEqual({ include: false, choice: "apostles", text: "" });
    expect(draftToServicePayload(setAffirmationChoice(d, "nicene")).affirmation).toEqual({ include: true, choice: "nicene", text: "" });
    const own = editAffirmationText(setAffirmationChoice(d, "own"), `  ${OWN}\n`);
    expect(draftToServicePayload(own).affirmation).toEqual({ include: true, choice: "own", text: OWN });
    // Own text typed, then a creed picked: the text is not sent.
    expect(draftToServicePayload(setAffirmationChoice(own, "nicene")).affirmation?.text).toBe("");
  });

  it("opens a saved service with its Affirmation, a service without one as the Apostles' Creed, and a save keeps it Saved", () => {
    const at = { church: churchProfile(), user: { id: USER_ID }, now: DRAFT_NOW };
    const old = serviceToDraft(savedService({ affirmation: undefined }), at);
    expect(old.liturgy.affirmation).toEqual({ include: true, choice: "apostles", text: "", origin: "archive" });
    expect(reviewStatus(old)).toBe("saved");
    const off = serviceToDraft(savedService({ affirmation: { include: false, choice: "nicene", text: "" } }), at);
    expect(off.liturgy.affirmation).toEqual({ include: false, choice: "nicene", text: "", origin: "archive" });
    expect(reviewStatus(off)).toBe("saved");
    expect(reviewStatus(setAffirmationInclude(off, true))).toBe("unsaved_changes");
    // A save makes a card that followed the default the service's own.
    const fresh = applyLiturgyDefaults(testDraft(), defaults());
    const saved = markSaved(fresh, savedService(), "fp");
    expect(saved.liturgy.affirmation).toEqual({ include: true, choice: "nicene", text: "", origin: "archive" });
  });

  it("posts a saved service's Nicene Creed when it is saved as a new service on another date", () => {
    const at = { church: churchProfile(), user: { id: USER_ID }, now: DRAFT_NOW };
    const opened = serviceToDraft(savedService({ affirmation: { include: true, choice: "nicene", text: "" } }), at);
    const copy = followSaveMode(setDate(opened, "2026-10-11", "user"));
    expect(saveMode(copy)).toBe("copy");
    expect(copy.liturgy.affirmation).toEqual({ include: true, choice: "nicene", text: "", origin: "archive" });
    expect(serviceBody(copy).affirmation).toEqual({ include: true, choice: "nicene", text: "" });
  });

  it("fingerprints the archive's copy the way the body is sent (a missing Affirmation is the Apostles' Creed)", () => {
    const body = documentRequest(testDraft(), "bulletin").service;
    const fromServer = { ...body, affirmation: undefined };
    expect(savedCopyFingerprint(fromServer)).toBe(savedCopyFingerprint(body));
    const own = documentRequest(editAffirmationText(setAffirmationChoice(testDraft(), "own"), OWN), "bulletin").service;
    expect(savedCopyFingerprint({ ...own, affirmation: { include: true, choice: "own", text: ` ${OWN} ` } })).toBe(savedCopyFingerprint(own));
    expect(savedCopyFingerprint(own)).not.toBe(savedCopyFingerprint(body));
  });

  it("counts a changed Affirmation as work, and one following the default as none", () => {
    const d = testDraft();
    expect(isPristine(d)).toBe(true);
    expect(isPristine(applyLiturgyDefaults(d, defaults()))).toBe(true);
    expect(isPristine(setAffirmationInclude(d, true))).toBe(false); // the same value, but the member's own now
  });

  it("names the Affirmation in the summary", () => {
    const d = testDraft();
    expect(affirmationSummary(d.liturgy.affirmation)).toBe("Affirmation of Faith: Apostles' Creed");
    expect(affirmationSummary(setAffirmationChoice(d, "nicene").liturgy.affirmation)).toBe("Affirmation of Faith: Nicene Creed");
    expect(affirmationSummary(setAffirmationChoice(d, "own").liturgy.affirmation)).toBe("Affirmation of Faith: Your own text (nothing typed yet)");
    expect(affirmationSummary(editAffirmationText(setAffirmationChoice(d, "own"), OWN).liturgy.affirmation)).toBe(
      "Affirmation of Faith: Your own text");
    expect(affirmationSummary(setAffirmationInclude(d, false).liturgy.affirmation)).toBe("Affirmation of Faith: Off");
  });
});

/**
 * The review provider (reviewer spec, "User experience", API; slice 4 spec,
 * reviewer amendment "UI hooks", "Sermon text" and Testing): one review of
 * every switched-on card with text, with generation's resolved sermon text
 * (WEB for an ESV church); notes in memory only; a card changed meanwhile
 * gets none; cancel, a failure and New service; Revise with its Undo and the
 * stale rule. The step's own tests (`review-step.test.tsx`) cover the screen.
 */
import { act, screen, waitFor } from "@testing-library/react";
import { useEffect } from "react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Toaster } from "@/components/ui/sonner";
import type { ReviewBody, ReviseBody } from "@/lib/api/types";
import { DraftProvider, useDraft, type DraftApi } from "@/lib/draft/context";
import { editScriptureLines } from "@/lib/draft/readings";
import { draftKey, type DraftV1, type SectionKey } from "@/lib/draft/schema";
import { fakeError, installFakeApi, type FakeHandler } from "@/test/fake-api";
import {
  church,
  churchProfile,
  DRAFT_NOW,
  me,
  reviewNote,
  reviewResult,
  reviewRoute,
  reviseRoute,
  testDraft,
  USER_ID,
} from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { editCardText } from "./cards";
import { LiturgyGenerationProvider, useLiturgyGeneration } from "./generation";
import { LiturgyReviewProvider, reviewDoneMessage, useLiturgyReview, type LiturgyReview } from "./review";
import { DEFAULT_BENEDICTION_FALLBACK } from "@/lib/liturgy/defaults";

const KEY = draftKey(USER_ID, church().id);
const STOCK = 'Stock phrase "as we journey". Say it more naturally.';
const PHILIPPIANS = {
  reference: "Philippians 3:4b-14",
  status: "ok",
  sections: [{ reference: "Philippians 3:4b-14", status: "ok", text: "I press on toward the goal." }],
};

const handle: { current: LiturgyReview | null } = { current: null };
const draftHandle: { current: DraftApi | null } = { current: null };
/** The generation provider, for Undo (as the card's Undo button calls it). */
const generationHandle: { current: ReturnType<typeof useLiturgyGeneration> | null } = { current: null };

function Probe() {
  const review = useLiturgyReview();
  const generation = useLiturgyGeneration();
  const api = useDraft();
  useEffect(() => {
    handle.current = review;
    draftHandle.current = api;
    generationHandle.current = generation;
  });
  const r = review.review;
  const cards = (["call_to_worship", "opening_prayer", "benediction"] as SectionKey[]).map((key) => {
    const notes = r?.cards[key];
    const shown = notes === undefined ? "none" : `${notes.stale ? "faded " : ""}${notes.notes.map((n) => n.text).join(" | ") || "looks good"}`;
    return `${key}: ${api.draft.liturgy.cards[key].text} [${api.draft.liturgy.cards[key].origin}] notes ${shown}; revising ${review.revising[key] ? "yes" : "no"}; error ${review.reviseErrors[key]?.message ?? "none"}; undo ${generation.undo[key]?.kind ?? "none"}`;
  });
  return (
    <ul aria-label="review">
      <li>running: {review.running ? "yes" : "no"}</li>
      <li>status: {r?.aiStatus ?? "none"}; service: {r?.service.map((n) => n.text).join(" | ") || "none"}</li>
      <li>error: {review.error ?? "none"}</li>
      <li>said: {review.announcement || "nothing"}</li>
      {cards.map((line) => (
        <li key={line}>{line}</li>
      ))}
    </ul>
  );
}

function card(d: DraftV1, key: SectionKey, text: string, origin: DraftV1["liturgy"]["cards"]["benediction"]["origin"], enabled = true): DraftV1 {
  return { ...d, liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, [key]: { enabled, text, origin } } } };
}

/** October 4's readings (the NT reading is Philippians), a typed Call to Worship, an AI Opening Prayer, the default Benediction. */
function seeded(): DraftV1 {
  let d = editScriptureLines(testDraft(), "Isaiah 5:1-7\nPsalm 80:7-15\nPhilippians 3:4b-14\nMatthew 21:33-46");
  d = card(d, "call_to_worship", "Leader: As we journey, come.", "typed");
  d = card(d, "opening_prayer", "Gracious God, as we journey, hear us.", "ai");
  return card(d, "prayer_of_confession", "Merciful God,", "archive", false);
}

function renderProvider(routes: Record<string, FakeHandler>, profile = churchProfile(), draft = seeded()) {
  window.localStorage.setItem(KEY, JSON.stringify(draft));
  const api = installFakeApi({ "POST /scripture/passages": { passages: [PHILIPPIANS] }, ...routes });
  const view = renderWithProviders(
    <>
      <DraftProvider userId={USER_ID} church={profile}>
        <LiturgyGenerationProvider church={profile}>
          <LiturgyReviewProvider church={profile} sermonWaitMs={2_000}>
            <Probe />
          </LiturgyReviewProvider>
        </LiturgyGenerationProvider>
      </DraftProvider>
      <Toaster />
    </>,
    { me: me(), church: church() },
  );
  return Object.assign(api, { view });
}

const ANSWER = reviewResult({
  cards: [
    { section: "call_to_worship", notes: [reviewNote("rules", STOCK, "code")] },
    { section: "opening_prayer", notes: [reviewNote("rules", STOCK, "code"), reviewNote("read_aloud", "The prayer runs long.")] },
    { section: "benediction", notes: [] },
  ],
  service_notes: [reviewNote("repetition", "Two prayers say journey.")],
});

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
  toast.dismiss(); // sonner replays a toast still showing to the next Toaster
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("the review (R User experience, API)", () => {
  it("reviews every switched-on card with text once, with generation's sermon text (WEB for ESV), notes in memory only", async () => {
    const api = renderProvider(
      { "POST /liturgy/review": reviewRoute(() => ANSWER) },
      churchProfile({ effective_translation: "esv", bible_translation: "esv" }),
    );
    act(() => handle.current?.start());
    expect(screen.getByText("running: yes")).toBeInTheDocument();
    expect(await screen.findByText("said: Review finished. 4 notes.")).toBeInTheDocument();
    expect(screen.getByText("running: no")).toBeInTheDocument();
    expect(screen.getByText(`opening_prayer: Gracious God, as we journey, hear us. [ai] notes ${STOCK} | The prayer runs long.; revising no; error none; undo none`)).toBeInTheDocument();
    // Not sent, so no notes and no "Looks good." (an answer for it would be ignored).
    expect(screen.getByText((text) => text.startsWith(`benediction: ${DEFAULT_BENEDICTION_FALLBACK} [default] notes none;`))).toBeInTheDocument();
    expect(screen.getByText("status: ok; service: Two prayers say journey.")).toBeInTheDocument();
    const passages = api.requests.filter((r) => r.path === "/scripture/passages");
    expect(passages.map((r) => r.body)).toEqual([{ refs: ["Philippians 3:4b-14"], translation: "web" }]);
    const reviews = api.requests.filter((r) => r.path === "/liturgy/review");
    expect(reviews).toHaveLength(1);
    const body = reviews[0].body as ReviewBody;
    expect(body.cards.map((c) => [c.section, c.origin])).toEqual([
      ["call_to_worship", "typed"],
      ["opening_prayer", "ai"],
    ]); // the Benediction follows the church default: not reviewed (owner, 2026-10-02)
    expect(body.sermon_text).toEqual({ ref: "Philippians 3:4b-14", text: "I press on toward the goal." });
    // Never saved: the stored draft holds no note.
    await waitFor(() => expect(window.localStorage.getItem(KEY)).toContain("as we journey"));
    expect(window.localStorage.getItem(KEY)).not.toContain("runs long");
    expect(reviewDoneMessage(1)).toBe("Review finished. 1 note.");
    expect(reviewDoneMessage(0)).toBe("Review finished. No notes.");
    expect(reviewDoneMessage(2, true)).toBe("Review finished. 2 notes. Only quick checks ran.");
  });

  it("gives no notes to a card edited while the review ran; Cancel and a failure keep the notes already shown", async () => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => (release = resolve));
    const api = renderProvider({
      "POST /liturgy/review": reviewRoute(async () => {
        await gate;
        return ANSWER;
      }),
    });
    act(() => handle.current?.start());
    await waitFor(() => expect(api.requests.some((r) => r.path === "/liturgy/review")).toBe(true));
    act(() => draftHandle.current?.update((d) => editCardText(d, "call_to_worship", "Leader: Come, all.")));
    act(() => handle.current?.start()); // already running: nothing more is sent
    release();
    expect(await screen.findByText("said: Review finished. 3 notes.")).toBeInTheDocument();
    expect(screen.getByText(/^call_to_worship: Leader: Come, all\. \[typed\] notes none;/)).toBeInTheDocument();
    expect(api.requests.filter((r) => r.path === "/liturgy/review")).toHaveLength(1);

    // Cancel: nothing changes, and the next review can start.
    api.set("POST /liturgy/review", () => new Promise<never>(() => {}));
    act(() => handle.current?.start());
    expect(screen.getByText("running: yes")).toBeInTheDocument();
    act(() => handle.current?.cancel());
    expect(screen.getByText("running: no")).toBeInTheDocument();
    expect(screen.getByText(/^opening_prayer: .* notes Stock phrase/)).toBeInTheDocument();
    // A failure shows its message and keeps the notes.
    api.set("POST /liturgy/review", fakeError(500, "internal_error", "Something went wrong."));
    act(() => handle.current?.start());
    expect(await screen.findByText("error: Something went wrong. (Ref: 4f9a2c1e)")).toBeInTheDocument();
    expect(screen.getByText(/^opening_prayer: .* notes Stock phrase/)).toBeInTheDocument();
  });

  it("New service drops every note and stops a running review silently", async () => {
    const api = renderProvider({ "POST /liturgy/review": reviewRoute(() => ANSWER) });
    act(() => handle.current?.start());
    expect(await screen.findByText("said: Review finished. 4 notes.")).toBeInTheDocument();
    api.set("POST /liturgy/review", () => new Promise<never>(() => {}));
    act(() => handle.current?.start());
    const current = draftHandle.current!.peek();
    act(() => draftHandle.current?.replace({ ...current, created_at: "2026-09-29T16:30:00.000Z" }));
    expect(screen.getByText("running: no")).toBeInTheDocument();
    expect(screen.getByText("status: none; service: none")).toBeInTheDocument();
    expect(screen.getByText(/^opening_prayer: .* notes none;/)).toBeInTheDocument();
  });
});

describe("Revise with these notes (R Revise)", () => {
  async function reviewed(routes: Record<string, FakeHandler>) {
    const api = renderProvider({ "POST /liturgy/review": reviewRoute(() => ANSWER), ...routes });
    act(() => handle.current?.start());
    expect(await screen.findByText("said: Review finished. 4 notes.")).toBeInTheDocument();
    return api;
  }

  it("sends the card's text and remaining notes, then replaces it as an AI draft with Undo", async () => {
    const api = await reviewed({ "POST /liturgy/revise": reviseRoute(() => ({ text: "Gracious God, hear us." })) });
    act(() => handle.current?.dismiss("opening_prayer", "opening_prayer-1"));
    const started: (boolean | undefined)[] = [];
    act(() => {
      started.push(handle.current?.revise("benediction")); // no notes: nothing to revise with
      started.push(handle.current?.revise("opening_prayer"));
      started.push(handle.current?.revise("opening_prayer")); // already running
    });
    expect(started).toEqual([false, true, false]);
    expect(screen.getByText(/^opening_prayer: .*revising yes;/)).toBeInTheDocument();
    expect(await screen.findByText("opening_prayer: Gracious God, hear us. [ai] notes none; revising no; error none; undo revised")).toBeInTheDocument();
    const revisions = api.requests.filter((r) => r.path === "/liturgy/revise");
    expect(revisions).toHaveLength(1);
    expect(revisions[0].body as ReviseBody).toMatchObject({
      section: "opening_prayer",
      text: "Gracious God, as we journey, hear us.",
      notes: [STOCK],
      sermon_text: { ref: "Philippians 3:4b-14", text: "I press on toward the goal." },
    });
    act(() => generationHandle.current?.applyUndo("opening_prayer"));
    expect(await screen.findByText(/^opening_prayer: Gracious God, as we journey, hear us\. \[ai\] notes none;/)).toBeInTheDocument();
  });

  it("keeps a card edited meanwhile, and shows why a revision failed", async () => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => (release = resolve));
    const api = await reviewed({
      "POST /liturgy/revise": reviseRoute(async () => {
        await gate;
        return { text: "Revised." };
      }),
    });
    act(() => {
      handle.current?.revise("opening_prayer");
    });
    await waitFor(() => expect(api.requests.some((r) => r.path === "/liturgy/revise")).toBe(true));
    act(() => draftHandle.current?.update((d) => editCardText(d, "opening_prayer", "My own words.")));
    release();
    expect(await screen.findByText("Kept your edits, so the revised draft for Opening Prayer was not used.")).toBeInTheDocument();
    // The toast (sonner, a timer) and the end of the revision (a React update) can land in either order: wait for both.
    expect(await screen.findByText(/^opening_prayer: My own words\. \[typed\] notes faded Stock phrase .* \| The prayer runs long\.; revising no;/)).toBeInTheDocument();

    act(() => draftHandle.current?.update((d) => card(d, "opening_prayer", "Holy One, as we journey.", "ai")));
    act(() => handle.current?.start());
    expect(await screen.findByText("said: Review finished. 4 notes.")).toBeInTheDocument();
    api.set("POST /liturgy/revise", fakeError(422, "prompt_invalid", "This prayer is too long to revise."));
    act(() => {
      handle.current?.revise("opening_prayer");
    });
    expect(await screen.findByText(/^opening_prayer: Holy One, as we journey\. \[ai\] notes Stock phrase.*; revising no; error This prayer is too long to revise\.;/)).toBeInTheDocument();
  });

  it("checks again once the sermon text has loaded: a card changed meanwhile is left out of the review, and its revision sends nothing", async () => {
    const loads: (() => void)[] = [];
    const api = renderProvider({
      "POST /scripture/passages": () => new Promise((resolve) => loads.push(() => resolve({ passages: [PHILIPPIANS] }))),
      "POST /liturgy/review": reviewRoute(() => ANSWER),
      "POST /liturgy/revise": reviseRoute(() => ({ text: "Revised." })),
    });
    act(() => handle.current?.start());
    await waitFor(() => expect(loads).toHaveLength(1));
    act(() => draftHandle.current?.update((d) => editCardText(d, "call_to_worship", "Leader: Come, all.")));
    act(() => loads[0]());
    expect(await screen.findByText("said: Review finished. 3 notes.")).toBeInTheDocument();
    const sent = api.requests.find((r) => r.path === "/liturgy/review")?.body as ReviewBody;
    expect(sent.cards.map((c) => c.section)).toEqual(["opening_prayer"]);

    // A new NT reading, so Revise loads its sermon text again; the card is edited meanwhile.
    act(() => draftHandle.current?.update((d) => editScriptureLines(d, "Isaiah 5:1-7\nPsalm 80:7-15\nRomans 8:1-11\nMatthew 21:33-46")));
    act(() => {
      handle.current?.revise("opening_prayer");
    });
    await waitFor(() => expect(loads).toHaveLength(2));
    act(() => draftHandle.current?.update((d) => editCardText(d, "opening_prayer", "My own words.")));
    act(() => loads[1]());
    expect(await screen.findByText("Kept your edits, so the revised draft for Opening Prayer was not used.")).toBeInTheDocument();
    // The toast (sonner, a timer) and the end of the revision (a React update) can land in either order: wait for both.
    expect(await screen.findByText(/^opening_prayer: My own words\. \[typed\] notes faded Stock phrase .* \| The prayer runs long\.; revising no;/)).toBeInTheDocument();
    expect(api.requests.some((r) => r.path === "/liturgy/revise")).toBe(false);
  });
});

describe("Revise the other prayers (reviewer follow-up 2)", () => {
  const OPENING = 'Several prayers open with "Gracious God".';
  const ACROSS = 'Opens with "Gracious God" like the Call to Worship; open differently.';

  /** Each prayer's revision waits for its own release; `sent` lists the sections in the order they were sent. */
  function gated(answers: Partial<Record<SectionKey, string>>) {
    const gates = new Map<string, () => void>();
    const route = reviseRoute(async (body) => {
      await new Promise<void>((resolve) => gates.set(body.section, resolve));
      return { text: answers[body.section as SectionKey] ?? "" };
    });
    return { route, release: (key: SectionKey) => gates.get(key)?.() };
  }

  function threeShare(): DraftV1 {
    let d = card(seeded(), "call_to_worship", "Leader: Gracious God, come.", "typed");
    d = card(d, "prayer_of_confession", "Gracious God, we confess.", "archive");
    return card(d, "assurance", "Gracious God, you forgive.", "ai");
  }

  const ANSWER_ACROSS = reviewResult({
    cards: [{ section: "opening_prayer", notes: [reviewNote("read_aloud", "The prayer runs long.")] }],
    service_notes: [reviewNote("repetition", OPENING, "code"), reviewNote("repetition", "Two prayers say journey.")],
  });

  function sentNotes(api: ReturnType<typeof renderProvider>) {
    return api.requests.filter((r) => r.path === "/liturgy/revise").map((r) => r.body as ReviseBody).map((b) => [b.section, b.text, b.notes]);
  }

  it("revises every prayer but the first one at a time, each told the openings so far; the note goes once all were revised", async () => {
    const { route, release } = gated({
      opening_prayer: "Holy One, hear us.",
      prayer_of_confession: "Merciful God, we confess.",
      assurance: "Leader: Loving God, you forgive.",
    });
    const api = renderProvider({ "POST /liturgy/review": reviewRoute(() => ANSWER_ACROSS), "POST /liturgy/revise": route }, churchProfile(), threeShare());
    act(() => handle.current?.start());
    expect(await screen.findByText("said: Review finished. 3 notes.")).toBeInTheDocument();
    const started: (boolean | undefined)[] = [];
    act(() => {
      started.push(handle.current?.reviseAcross("service-1")); // an AI note: the app does not know the prayers
      started.push(handle.current?.reviseAcross("service-0"));
      started.push(handle.current?.reviseAcross("service-0")); // already running
    });
    expect(started).toEqual([false, true, false]);
    // One at a time, in service order; every one shows as revising from the start.
    await waitFor(() => expect(sentNotes(api)).toHaveLength(1));
    expect(handle.current?.revising).toEqual({ opening_prayer: true, prayer_of_confession: true, assurance: true });
    expect(screen.getByText(`status: ok; service: ${OPENING} | Two prayers say journey.`)).toBeInTheDocument();
    act(() => release("opening_prayer"));
    expect(await screen.findByText("opening_prayer: Holy One, hear us. [ai] notes none; revising no; error none; undo revised")).toBeInTheDocument();
    await waitFor(() => expect(sentNotes(api)).toHaveLength(2));
    act(() => release("prayer_of_confession"));
    await waitFor(() => expect(sentNotes(api)).toHaveLength(3));
    expect(sentNotes(api)).toEqual([
      ["opening_prayer", "Gracious God, as we journey, hear us.", [ACROSS]],
      ["prayer_of_confession", "Gracious God, we confess.", [`${ACROSS.slice(0, -1)}, not with "Holy One".`]],
      ["assurance", "Gracious God, you forgive.", [`${ACROSS.slice(0, -1)}, not with "Holy One" or "Merciful God".`]],
    ]);
    expect(screen.getByText(`status: ok; service: ${OPENING} | Two prayers say journey.`)).toBeInTheDocument();
    act(() => release("assurance"));
    expect(await screen.findByText("status: ok; service: Two prayers say journey.")).toBeInTheDocument();
    expect(handle.current?.revising).toEqual({});
    expect(screen.getByText(/^call_to_worship: Leader: Gracious God, come\. \[typed\] notes none; revising no; error none; undo none$/)).toBeInTheDocument();
    expect(draftHandle.current?.peek().liturgy.cards.prayer_of_confession).toEqual({ enabled: true, text: "Merciful God, we confess.", origin: "ai" });
    expect(draftHandle.current?.peek().liturgy.cards.assurance).toEqual({ enabled: true, text: "Leader: Loving God, you forgive.", origin: "ai" });
  });

  it("never removes the note of a newer review, even one with the same note", async () => {
    const { route, release } = gated({ opening_prayer: "Holy One, hear us.", prayer_of_confession: "Merciful God, we confess.", assurance: "Loving God, you forgive." });
    const api = renderProvider({ "POST /liturgy/review": reviewRoute(() => ANSWER_ACROSS), "POST /liturgy/revise": route }, churchProfile(), threeShare());
    act(() => handle.current?.start());
    expect(await screen.findByText("said: Review finished. 3 notes.")).toBeInTheDocument();
    act(() => void handle.current?.reviseAcross("service-0"));
    await waitFor(() => expect(sentNotes(api)).toHaveLength(1));
    act(() => release("opening_prayer"));
    await waitFor(() => expect(sentNotes(api)).toHaveLength(2));
    act(() => release("prayer_of_confession"));
    await waitFor(() => expect(sentNotes(api)).toHaveLength(3));
    // A new review while the last one runs: it brings the same note (same id, same words).
    act(() => handle.current?.start());
    await waitFor(() => expect(api.requests.filter((r) => r.path === "/liturgy/review")).toHaveLength(2));
    expect(await screen.findByText("running: no")).toBeInTheDocument();
    act(() => release("assurance"));
    expect(await screen.findByText(/^opening_prayer: Holy One, hear us\. \[ai\]/)).toBeInTheDocument();
    await waitFor(() => expect(handle.current?.revising).toEqual({}));
    expect(draftHandle.current?.peek().liturgy.cards.assurance.text).toBe("Loving God, you forgive.");
    expect(screen.getByText(`status: ok; service: ${OPENING} | Two prayers say journey.`)).toBeInTheDocument();
  });

  it("skips a prayer switched off before its turn (another tab), sending nothing for it and keeping the note", async () => {
    const { route, release } = gated({ opening_prayer: "Holy One, hear us.", assurance: "Loving God, you forgive." });
    const api = renderProvider({ "POST /liturgy/review": reviewRoute(() => ANSWER_ACROSS), "POST /liturgy/revise": route }, churchProfile(), threeShare());
    act(() => handle.current?.start());
    expect(await screen.findByText("said: Review finished. 3 notes.")).toBeInTheDocument();
    act(() => void handle.current?.reviseAcross("service-0"));
    await waitFor(() => expect(sentNotes(api)).toHaveLength(1));
    // Switched off while it waits, with no Cancel (as another tab's change arrives): its turn sends nothing.
    act(() => draftHandle.current?.update((d) => card(d, "prayer_of_confession", "Gracious God, we confess.", "archive", false)));
    act(() => release("opening_prayer"));
    await waitFor(() => expect(sentNotes(api)).toHaveLength(2));
    expect(sentNotes(api).map(([section]) => section)).toEqual(["opening_prayer", "assurance"]);
    expect(handle.current?.revising).toEqual({ assurance: true });
    act(() => release("assurance"));
    await waitFor(() => expect(handle.current?.revising).toEqual({}));
    expect(draftHandle.current?.peek().liturgy.cards.assurance).toEqual({ enabled: true, text: "Loving God, you forgive.", origin: "ai" });
    expect(draftHandle.current?.peek().liturgy.cards.prayer_of_confession).toEqual({ enabled: false, text: "Gracious God, we confess.", origin: "archive" });
    expect(screen.queryByText(/revised draft for Prayer of Confession/)).toBeNull(); // skipped silently, as a switch-off in this tab
    expect(screen.getByText(`status: ok; service: ${OPENING} | Two prayers say journey.`)).toBeInTheDocument();
  });

  const KEPT = `status: ok; service: ${OPENING} | Two prayers say journey.`;

  /** Three prayers share the opening; the batch has started and sent the Opening Prayer, which waits. */
  async function begun(route: FakeHandler) {
    const api = renderProvider({ "POST /liturgy/review": reviewRoute(() => ANSWER_ACROSS), "POST /liturgy/revise": route }, churchProfile(), threeShare());
    act(() => handle.current?.start());
    expect(await screen.findByText("said: Review finished. 3 notes.")).toBeInTheDocument();
    act(() => void handle.current?.reviseAcross("service-0"));
    await waitFor(() => expect(sentNotes(api)).toHaveLength(1));
    return api;
  }

  /** Lets any revision still in flight settle (the fake API answers on the next tasks). */
  async function settle() {
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
    });
  }

  it("keeps the note when an Undo mid-batch brought the shared opening back, even though every one was revised", async () => {
    const { route, release } = gated({ opening_prayer: "Holy One, hear us.", prayer_of_confession: "Merciful God, we confess.", assurance: "Loving God, you forgive." });
    const api = await begun(route);
    act(() => release("opening_prayer"));
    expect(await screen.findByText(/^opening_prayer: Holy One, hear us\. \[ai\] .*undo revised$/)).toBeInTheDocument();
    act(() => generationHandle.current?.applyUndo("opening_prayer"));
    expect(await screen.findByText(/^opening_prayer: Gracious God, as we journey, hear us\. \[ai\]/)).toBeInTheDocument();
    await waitFor(() => expect(sentNotes(api)).toHaveLength(2));
    act(() => release("prayer_of_confession"));
    await waitFor(() => expect(sentNotes(api)).toHaveLength(3));
    act(() => release("assurance"));
    await waitFor(() => expect(handle.current?.revising).toEqual({}));
    expect(draftHandle.current?.peek().liturgy.cards.assurance.text).toBe("Loving God, you forgive.");
    expect(screen.getByText(KEPT)).toBeInTheDocument();
  });

  it("keeps the note and offers the button again when every one was revised but the AI kept the opening (owner answer A)", async () => {
    const { route, release } = gated({
      opening_prayer: "Gracious God, hear us.",
      prayer_of_confession: "Gracious God, we confess our sins.",
      assurance: "Gracious God, you forgive us.",
    });
    const api = await begun(route);
    act(() => release("opening_prayer"));
    await waitFor(() => expect(sentNotes(api)).toHaveLength(2));
    act(() => release("prayer_of_confession"));
    await waitFor(() => expect(sentNotes(api)).toHaveLength(3));
    act(() => release("assurance"));
    await waitFor(() => expect(handle.current?.revising).toEqual({}));
    expect(draftHandle.current?.peek().liturgy.cards.assurance).toEqual({ enabled: true, text: "Gracious God, you forgive us.", origin: "ai" });
    expect(handle.current?.reviseErrors).toEqual({});
    expect(screen.getByText(KEPT)).toBeInTheDocument();
    // The prayers still share the opening, so the button offers them again.
    let again: boolean | undefined;
    act(() => {
      again = handle.current?.reviseAcross("service-0");
    });
    expect(again).toBe(true);
    await waitFor(() => expect(sentNotes(api)).toHaveLength(4));
    expect(sentNotes(api)[3]).toEqual(["opening_prayer", "Gracious God, hear us.", [ACROSS]]);
  });

  it("stops when a 429's wait began before the next prayer's turn: nothing more is sent, the wait shows on it, the note stays", async () => {
    const { route, release } = gated({ opening_prayer: "Holy One, hear us." });
    const api = await begun(route);
    act(() => generationHandle.current?.noteRateLimit(Date.now() + 30_000)); // Generate's 429 on another card
    act(() => release("opening_prayer"));
    expect(await screen.findByText(/^opening_prayer: Holy One, hear us\. \[ai\]/)).toBeInTheDocument();
    await waitFor(() => expect(handle.current?.revising).toEqual({}));
    await settle();
    expect(sentNotes(api)).toHaveLength(1);
    expect(handle.current?.reviseErrors.prayer_of_confession?.message).toBe("Too many requests — try again in 30 s.");
    expect(handle.current?.reviseErrors.assurance).toBeUndefined();
    expect(screen.getByText(KEPT)).toBeInTheDocument();
  });

  it("stops when the kept first prayer no longer opens with the words", async () => {
    const { route, release } = gated({ opening_prayer: "Holy One, hear us." });
    const api = await begun(route);
    act(() => draftHandle.current?.update((d) => editCardText(d, "call_to_worship", "Leader: Come, all.")));
    act(() => release("opening_prayer"));
    await waitFor(() => expect(handle.current?.revising).toEqual({}));
    await settle();
    expect(sentNotes(api)).toHaveLength(1);
    expect(draftHandle.current?.peek().liturgy.cards.prayer_of_confession.text).toBe("Gracious God, we confess.");
    expect(screen.getByText(KEPT)).toBeInTheDocument();
  });

  it("New service mid-batch: nothing shows as revising and nothing more is sent", async () => {
    const { route, release } = gated({ opening_prayer: "Holy One, hear us." });
    const api = await begun(route);
    const current = draftHandle.current!.peek();
    act(() => draftHandle.current?.replace({ ...current, created_at: "2026-09-29T16:30:00.000Z" }));
    expect(handle.current?.revising).toEqual({});
    act(() => release("opening_prayer"));
    await settle();
    expect(sentNotes(api)).toHaveLength(1);
    expect(handle.current?.revising).toEqual({});
  });

  it("unmounting mid-batch sends nothing more and logs no error", async () => {
    const errors = vi.spyOn(console, "error");
    const { route, release } = gated({ opening_prayer: "Holy One, hear us." });
    const api = await begun(route);
    api.view.unmount();
    release("opening_prayer");
    await settle();
    expect(sentNotes(api)).toHaveLength(1);
    expect(errors).not.toHaveBeenCalled();
  });

  it("goes on after a prayer's revision failed (not a 429), showing the failure on it and keeping the note", async () => {
    const gates = new Map<string, () => void>();
    const api = await begun(
      reviseRoute(async (body) => {
        await new Promise<void>((resolve) => gates.set(body.section, resolve));
        return body.section === "opening_prayer" ? fakeError(500, "internal_error", "Something went wrong.") : { text: `Holy ${body.section}.` };
      }),
    );
    act(() => gates.get("opening_prayer")?.());
    expect(await screen.findByText(/^opening_prayer: Gracious God, as we journey, hear us\. \[ai\] .*error Something went wrong\./)).toBeInTheDocument();
    await waitFor(() => expect(sentNotes(api)).toHaveLength(2));
    act(() => gates.get("prayer_of_confession")?.());
    await waitFor(() => expect(sentNotes(api)).toHaveLength(3));
    act(() => gates.get("assurance")?.());
    await waitFor(() => expect(handle.current?.revising).toEqual({}));
    expect(draftHandle.current?.peek().liturgy.cards.assurance.text).toBe("Holy assurance.");
    expect(screen.getByText(KEPT)).toBeInTheDocument();
  });

  it("skips a prayer edited in another tab before its turn, saying it kept the edits, and keeps the note", async () => {
    const { route, release } = gated({ opening_prayer: "Holy One, hear us.", assurance: "Loving God, you forgive." });
    const api = await begun(route);
    act(() => draftHandle.current?.update((d) => card(d, "prayer_of_confession", "Gracious God, my own words.", "typed")));
    act(() => release("opening_prayer"));
    expect(await screen.findByText("Kept your edits, so the revised draft for Prayer of Confession was not used.")).toBeInTheDocument();
    await waitFor(() => expect(sentNotes(api)).toHaveLength(2));
    expect(sentNotes(api).map(([section]) => section)).toEqual(["opening_prayer", "assurance"]);
    act(() => release("assurance"));
    await waitFor(() => expect(handle.current?.revising).toEqual({}));
    expect(draftHandle.current?.peek().liturgy.cards.prayer_of_confession.text).toBe("Gracious God, my own words.");
    expect(screen.getByText(KEPT)).toBeInTheDocument();
  });
});

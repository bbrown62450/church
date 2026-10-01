/**
 * The generation provider's sermon text (slice 4 spec, "Sermon text";
 * Testing `generation.test.tsx`, amendment 2026-09-26): a batch reads the
 * passage once and every request carries it; a fetch that fails or takes too
 * long still sends the batch, without it and with no toast; Cancel during the
 * wait sends nothing. And S step 6 before sending: a card whose text became
 * the member's while it waited in the queue (Undo, another tab) is not sent.
 * The step's own tests (T9) cover the rest of the flow.
 */
import { act, screen, waitFor } from "@testing-library/react";
import { useEffect } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Toaster } from "@/components/ui/sonner";
import type { GenerateLiturgyBody } from "@/lib/api/types";
import { DraftProvider, useDraft } from "@/lib/draft/context";
import { editScriptureLines } from "@/lib/draft/readings";
import { draftKey, type DraftV1, type SectionKey } from "@/lib/draft/schema";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { church, churchProfile, DRAFT_NOW, generateRoute, me, sectionResult, testDraft, USER_ID } from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { LiturgyGenerationProvider, MAX_IN_FLIGHT, SERMON_WAIT_MS, useLiturgyGeneration, type LiturgyGeneration } from "./generation";

const KEY = draftKey(USER_ID, church().id);
const FOUR: SectionKey[] = ["call_to_worship", "opening_prayer", "prayer_of_confession", "assurance"];
const PHILIPPIANS = {
  reference: "Philippians 3:4b-14",
  status: "ok",
  sections: [{ reference: "Philippians 3:4b-14", status: "ok", text: "I press on toward the goal." }],
};

/** The provider's latest value, for the test to call (set after each render). */
const handle: { current: LiturgyGeneration | null } = { current: null };
const generation = {
  generate: (...args: Parameters<LiturgyGeneration["generate"]>) => handle.current?.generate(...args),
  cancel: (...args: Parameters<LiturgyGeneration["cancel"]>) => handle.current?.cancel(...args),
  setUndo: (...args: Parameters<LiturgyGeneration["setUndo"]>) => handle.current?.setUndo(...args),
  applyUndo: (...args: Parameters<LiturgyGeneration["applyUndo"]>) => handle.current?.applyUndo(...args),
};

function Probe() {
  const g = useLiturgyGeneration();
  useEffect(() => {
    handle.current = g;
  });
  const { draft } = useDraft();
  return (
    <ul>
      {FOUR.map((key) => (
        <li key={key}>
          {key}: {draft.liturgy.cards[key].text || "empty"} / {g.runs[key]?.phase ?? "idle"}
        </li>
      ))}
    </ul>
  );
}

/** Pat's draft with October 4's readings (the NT reading is Philippians), in the providers the shell mounts. */
function renderProvider(routes: Record<string, FakeHandler>, sermonWaitMs?: number, recipe: (d: DraftV1) => DraftV1 = (d) => d) {
  window.localStorage.setItem(
    KEY,
    JSON.stringify(recipe(editScriptureLines(testDraft(), "Isaiah 5:1-7\nPsalm 80:7-15\nPhilippians 3:4b-14\nMatthew 21:33-46"))),
  );
  const api = installFakeApi(routes);
  const profile = churchProfile();
  renderWithProviders(
    <>
      <DraftProvider userId={USER_ID} church={profile}>
        <LiturgyGenerationProvider church={profile} sermonWaitMs={sermonWaitMs}>
          <Probe />
        </LiturgyGenerationProvider>
      </DraftProvider>
      <Toaster />
    </>,
    { me: me(), church: church() },
  );
  return api;
}

const generateCalls = (requests: RecordedRequest[]) => requests.filter((r) => r.path === "/liturgy/generate");

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("the sermon text (S Sermon text)", () => {
  it("reads the passage once for a batch of 4, then sends 4 requests with the same sermon_text, 3 at a time", async () => {
    let open = 0;
    let most = 0;
    const api = renderProvider({
      "POST /scripture/passages": { passages: [PHILIPPIANS] },
      "POST /liturgy/generate": generateRoute(async (section) => {
        open += 1;
        most = Math.max(most, open);
        await new Promise((resolve) => setTimeout(resolve, 20));
        open -= 1;
        return { section, status: "generated", text: `${section} text`, error: null };
      }),
    });
    act(() => generation.generate(FOUR, { aiAvailable: true, bulk: true }));
    for (const key of FOUR) expect(await screen.findByText(`${key}: ${key} text / idle`)).toBeInTheDocument();
    expect(api.requests.filter((r) => r.path === "/scripture/passages")).toHaveLength(1);
    expect(api.requests.find((r) => r.path === "/scripture/passages")?.body).toEqual({ refs: ["Philippians 3:4b-14"], translation: "web" });
    const calls = generateCalls(api.requests);
    expect(calls.map((r) => (r.body as GenerateLiturgyBody).sections)).toEqual(FOUR.map((key) => [key]));
    for (const call of calls) {
      expect((call.body as GenerateLiturgyBody).sermon_text).toEqual({ ref: "Philippians 3:4b-14", text: "I press on toward the goal." });
    }
    expect(most).toBeLessThanOrEqual(MAX_IN_FLIGHT);
    expect(await screen.findByText("Wrote 4 sections.")).toBeInTheDocument();
  });

  it("sends the batch without sermon_text, and no toast about it, when the passage fails or takes too long", async () => {
    expect(SERMON_WAIT_MS).toBe(10_000);
    const failing = renderProvider({
      "POST /scripture/passages": fakeError(500, "internal_error", "Something went wrong."),
      "POST /liturgy/generate": generateRoute(),
    });
    act(() => generation.generate(["call_to_worship"], { aiAvailable: true }));
    expect(await screen.findByText("call_to_worship: Call to Worship written by the AI. / idle")).toBeInTheDocument();
    expect(generateCalls(failing.requests)[0].body).not.toHaveProperty("sermon_text");
    expect(screen.queryByText(/Something went wrong/)).toBeNull();
  });

  it("goes without the sermon text once the wait passes (shortened here), and Cancel during the wait sends nothing", async () => {
    const never = new Promise<never>(() => {});
    const api = renderProvider(
      { "POST /scripture/passages": () => never, "POST /liturgy/generate": generateRoute() },
      50,
    );
    act(() => generation.generate(["opening_prayer"], { aiAvailable: true }));
    expect(screen.getByText("opening_prayer: empty / queued")).toBeInTheDocument();
    expect(await screen.findByText("opening_prayer: Opening Prayer written by the AI. / idle")).toBeInTheDocument();
    expect(generateCalls(api.requests)[0].body).not.toHaveProperty("sermon_text");

    act(() => generation.generate(["assurance"], { aiAvailable: true }));
    expect(screen.getByText("assurance: empty / queued")).toBeInTheDocument();
    act(() => generation.cancel(["assurance"]));
    expect(screen.getByText("assurance: empty / idle")).toBeInTheDocument();
    // A later batch waits as long, so once its answer is in, the cancelled one would have been sent.
    act(() => generation.generate(["prayer_of_confession"], { aiAvailable: true }));
    expect(await screen.findByText("prayer_of_confession: Prayer of Confession written by the AI. / idle")).toBeInTheDocument();
    expect(generateCalls(api.requests).map((r) => (r.body as GenerateLiturgyBody).sections)).toEqual([
      ["opening_prayer"],
      ["prayer_of_confession"],
    ]);
    expect(screen.getByText("assurance: empty / idle")).toBeInTheDocument();
  });
});

/** A generate route that holds every section until the test releases it, so the 4th card waits in the queue. */
function heldRoute() {
  const waiting = new Map<string, () => void>();
  const route = generateRoute(async (section) => {
    await new Promise<void>((resolve) => waiting.set(section, resolve));
    return sectionResult(section, `New ${section}`);
  });
  return { route, release: (key: SectionKey) => waiting.get(key)?.() };
}

const withAssurance = (text: string, origin: "ai" | "typed") => (d: DraftV1): DraftV1 => ({
  ...d,
  liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, assurance: { enabled: true, text, origin } } },
});

describe("a card that changed while it waited (S step 6, before sending)", () => {
  it("Undo while Waiting… sends nothing: the card keeps the text Undo brought back", async () => {
    const held = heldRoute();
    const api = renderProvider({ "POST /scripture/passages": { passages: [PHILIPPIANS] }, "POST /liturgy/generate": held.route }, undefined, withAssurance("You are forgiven (AI).", "ai"));
    act(() => generation.setUndo("assurance", { kind: "replaced", previous: { text: "You are forgiven.", origin: "typed" } }));
    act(() => generation.generate(FOUR, { aiAvailable: true }));
    await waitFor(() => expect(generateCalls(api.requests)).toHaveLength(MAX_IN_FLIGHT));
    expect(screen.getByText("assurance: You are forgiven (AI). / queued")).toBeInTheDocument();
    act(() => generation.applyUndo("assurance"));
    for (const key of FOUR.slice(0, 3)) held.release(key);
    expect(await screen.findByText("Kept your edits — the new AI draft for Assurance of Pardon was not used.")).toBeInTheDocument();
    expect(screen.getByText("assurance: You are forgiven. / idle")).toBeInTheDocument();
    expect(generateCalls(api.requests).map((r) => (r.body as GenerateLiturgyBody).sections[0])).toEqual(FOUR.slice(0, 3));
  });

  it("an edit from another tab while the card waits sends nothing", async () => {
    const held = heldRoute();
    const api = renderProvider({ "POST /scripture/passages": { passages: [PHILIPPIANS] }, "POST /liturgy/generate": held.route });
    act(() => generation.generate(FOUR, { aiAvailable: true }));
    await waitFor(() => expect(generateCalls(api.requests)).toHaveLength(MAX_IN_FLIGHT));
    const theirs = withAssurance("From the other tab", "typed")(JSON.parse(window.localStorage.getItem(KEY) ?? "null") as DraftV1);
    act(() => {
      window.dispatchEvent(
        new StorageEvent("storage", { key: KEY, newValue: JSON.stringify({ ...theirs, updated_at: "2026-09-29T17:00:00.000Z" }) }),
      );
    });
    expect(await screen.findByText("assurance: From the other tab / queued")).toBeInTheDocument();
    for (const key of FOUR.slice(0, 3)) held.release(key);
    expect(await screen.findByText("Kept your edits — the new AI draft for Assurance of Pardon was not used.")).toBeInTheDocument();
    expect(screen.getByText("assurance: From the other tab / idle")).toBeInTheDocument();
    expect(generateCalls(api.requests)).toHaveLength(3);
  });
});

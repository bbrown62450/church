/**
 * The generation provider's sermon text (slice 4 spec, "Sermon text";
 * Testing `generation.test.tsx`, amendment 2026-09-26): a batch reads the
 * passage once and every request carries it; a fetch that fails or takes too
 * long still sends the batch, without it and with no toast; Cancel during the
 * wait sends nothing. And S step 6 before sending: a card whose text became
 * the member's while it waited in the queue (Undo, another tab) is not sent.
 * From the T1-T10 review: New service mid-run, a 429's wait (which New
 * service does not end), cancel on unmount, Undo only over the text it left,
 * and the bulk toast's wording. The step's own tests (T9) cover the rest.
 */
import { act, screen, waitFor } from "@testing-library/react";
import { useEffect } from "react";
import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from "vitest";

import { toast } from "sonner";

import { Toaster } from "@/components/ui/sonner";
import type { GenerateLiturgyBody } from "@/lib/api/types";
import { DraftProvider, useDraft, type DraftApi } from "@/lib/draft/context";
import { editScriptureLines } from "@/lib/draft/readings";
import { draftKey, type DraftV1, type SectionKey } from "@/lib/draft/schema";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { church, churchProfile, DRAFT_NOW, generateRoute, me, sectionResult, testDraft, USER_ID } from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import {
  bulkMessage,
  LiturgyGenerationProvider,
  MAX_IN_FLIGHT,
  SERMON_WAIT_MS,
  SERVICE_CHANGED_BULK,
  useLiturgyGeneration,
  type LiturgyGeneration,
} from "./generation";

const KEY = draftKey(USER_ID, church().id);
const FOUR: SectionKey[] = ["call_to_worship", "opening_prayer", "prayer_of_confession", "assurance"];
const PHILIPPIANS = {
  reference: "Philippians 3:4b-14",
  status: "ok",
  sections: [{ reference: "Philippians 3:4b-14", status: "ok", text: "I press on toward the goal." }],
};

/** The provider's latest value, for the test to call (set after each render). */
const handle: { current: LiturgyGeneration | null } = { current: null };
/** The draft API, for New service (`replace`) and reads. */
const draftHandle: { current: DraftApi | null } = { current: null };
const generation = {
  generate: (...args: Parameters<LiturgyGeneration["generate"]>) => handle.current?.generate(...args),
  cancel: (...args: Parameters<LiturgyGeneration["cancel"]>) => handle.current?.cancel(...args),
  setUndo: (...args: Parameters<LiturgyGeneration["setUndo"]>) => handle.current?.setUndo(...args),
  applyUndo: (...args: Parameters<LiturgyGeneration["applyUndo"]>) => handle.current?.applyUndo(...args),
};

function Probe() {
  const g = useLiturgyGeneration();
  const api = useDraft();
  useEffect(() => {
    handle.current = g;
    draftHandle.current = api;
  });
  const { draft } = api;
  return (
    <>
      <ul>
        {FOUR.map((key) => (
          <li key={key}>
            {key}: {draft.liturgy.cards[key].text || "empty"} / {g.runs[key]?.phase ?? "idle"}
          </li>
        ))}
      </ul>
      <ul aria-label="state">
        {FOUR.map((key) => (
          <li key={key}>
            {key} error: {g.errors[key]?.message ?? "none"} / until {g.errors[key]?.retryAt ?? "none"}; undo: {g.undo[key]?.kind ?? "none"}
          </li>
        ))}
        <li>limited until: {g.rateLimitedUntil ?? "none"}</li>
      </ul>
    </>
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
  const view = renderWithProviders(
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
  return Object.assign(api, { view });
}

const generateCalls = (requests: RecordedRequest[]) => requests.filter((r) => r.path === "/liturgy/generate");

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
  toast.dismiss(); // sonner replays a toast still showing to the next Toaster
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
    act(() =>
      generation.setUndo("assurance", {
        kind: "replaced",
        previous: { text: "You are forgiven.", origin: "typed" },
        after: "You are forgiven (AI).",
      }),
    );
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

/** The stored draft, as another tab would read it before writing its own edit. */
function storedDraft(): DraftV1 {
  return JSON.parse(window.localStorage.getItem(KEY) ?? "null") as DraftV1;
}

function fromOtherTab(d: DraftV1, updatedAt = "2026-09-29T17:00:00.000Z") {
  act(() => {
    window.dispatchEvent(new StorageEvent("storage", { key: KEY, newValue: JSON.stringify({ ...d, updated_at: updatedAt }) }));
  });
}

const RATE_LIMITED = fakeError(429, "rate_limited", "Too many requests. Try again in 30 seconds.", { details: { retry_after_seconds: 30 } });

describe("the provider after the T1-T10 review", () => {
  it("New service mid-run cancels every run with one toast, and the answers land nowhere", async () => {
    const held = heldRoute();
    const api = renderProvider({ "POST /scripture/passages": { passages: [PHILIPPIANS] }, "POST /liturgy/generate": held.route });
    act(() => generation.generate(FOUR, { aiAvailable: true, bulk: true }));
    await waitFor(() => expect(generateCalls(api.requests)).toHaveLength(MAX_IN_FLIGHT));
    const current = draftHandle.current?.peek() as DraftV1;
    act(() => draftHandle.current?.replace({ ...current, created_at: "2026-09-29T16:30:00.000Z" }));
    expect(await screen.findByText(SERVICE_CHANGED_BULK)).toBeInTheDocument();
    for (const key of FOUR) expect(screen.getByText(`${key}: empty / idle`)).toBeInTheDocument();
    for (const key of FOUR.slice(0, 3)) held.release(key);
    // Positive: a later run on the new service is written, so the old answers had their chance to land.
    act(() => generation.generate(["assurance"], { aiAvailable: true }));
    await waitFor(() => expect(generateCalls(api.requests)).toHaveLength(4));
    held.release("assurance");
    expect(await screen.findByText("assurance: New assurance / idle")).toBeInTheDocument();
    for (const key of FOUR.slice(0, 3)) expect(screen.getByText(`${key}: empty / idle`)).toBeInTheDocument();
    expect(screen.getAllByText(SERVICE_CHANGED_BULK)).toHaveLength(1);
    expect(screen.queryByText(/^Wrote|was discarded\.$|Kept your edits/)).toBeNull();
    expect(generateCalls(api.requests)).toHaveLength(4);
  });

  it("keeps a 429's wait as retryAt and rateLimitedUntil; New service does not end it, and generate sends nothing until then", async () => {
    const api = renderProvider({ "POST /scripture/passages": { passages: [PHILIPPIANS] }, "POST /liturgy/generate": RATE_LIMITED });
    const until = DRAFT_NOW.getTime() + 30_000;
    act(() => generation.generate(["call_to_worship"], { aiAvailable: true }));
    expect(await screen.findByText(`call_to_worship error: Too many requests — try again in 30 s. / until ${until}; undo: none`)).toBeInTheDocument();
    expect(screen.getByText(`limited until: ${until}`)).toBeInTheDocument();
    // New service clears the cards' errors, but not the wait.
    vi.setSystemTime(DRAFT_NOW.getTime() + 10_000);
    const current = draftHandle.current?.peek() as DraftV1;
    act(() => draftHandle.current?.replace({ ...current, created_at: "2026-09-29T16:00:10.000Z" }));
    expect(await screen.findByText("call_to_worship error: none / until none; undo: none")).toBeInTheDocument();
    expect(screen.getByText(`limited until: ${until}`)).toBeInTheDocument();
    act(() => generation.generate(["opening_prayer"], { aiAvailable: true }));
    expect(screen.getByText(`opening_prayer error: Too many requests — try again in 20 s. / until ${until}; undo: none`)).toBeInTheDocument();
    expect(screen.getByText("opening_prayer: empty / idle")).toBeInTheDocument();
    expect(generateCalls(api.requests)).toHaveLength(1);
    // Once the wait is over, it sends.
    vi.setSystemTime(until);
    api.set("POST /liturgy/generate", generateRoute());
    act(() => generation.generate(["opening_prayer"], { aiAvailable: true }));
    expect(await screen.findByText("opening_prayer: Opening Prayer written by the AI. / idle")).toBeInTheDocument();
    expect(generateCalls(api.requests)).toHaveLength(2);
  });

  it("cancels its requests when it unmounts (leaving the builder), and their answers are never written", async () => {
    const held = heldRoute();
    const api = renderProvider({ "POST /scripture/passages": { passages: [PHILIPPIANS] }, "POST /liturgy/generate": held.route });
    act(() => generation.generate(["call_to_worship"], { aiAvailable: true }));
    await waitFor(() => expect(generateCalls(api.requests)).toHaveLength(1));
    const calls = (fetch as unknown as Mock<typeof fetch>).mock.calls.filter(([input]) => String(input).endsWith("/liturgy/generate"));
    const signal = calls[0][1]?.signal as AbortSignal;
    expect(signal.aborted).toBe(false);
    api.view.unmount();
    expect(signal.aborted).toBe(true);
    held.release("call_to_worship");
    await waitFor(() => expect(storedDraft().liturgy.cards.call_to_worship.text).toBe(""));
    expect(screen.queryByText(/Wrote|discarded|Kept your edits/)).toBeNull();
  });

  it("a result written over a blank card removes its Cleared. Undo", async () => {
    renderProvider({ "POST /scripture/passages": { passages: [PHILIPPIANS] }, "POST /liturgy/generate": generateRoute() });
    act(() => generation.setUndo("call_to_worship", { kind: "cleared", previous: { text: "Come.", origin: "typed" }, after: "" }));
    expect(screen.getByText("call_to_worship error: none / until none; undo: cleared")).toBeInTheDocument();
    act(() => generation.generate(["call_to_worship"], { aiAvailable: true }));
    expect(await screen.findByText("call_to_worship: Call to Worship written by the AI. / idle")).toBeInTheDocument();
    expect(screen.getByText("call_to_worship error: none / until none; undo: none")).toBeInTheDocument();
  });

  it("an onWritten listener that throws is logged; the draft is still written and the other listeners still run", async () => {
    const logged = vi.spyOn(console, "error").mockImplementation(() => {});
    renderProvider(
      { "POST /scripture/passages": { passages: [PHILIPPIANS] }, "POST /liturgy/generate": generateRoute() },
      undefined,
      withAssurance("You are forgiven.", "typed"),
    );
    const boom = new Error("listener failed");
    const heard: SectionKey[] = [];
    const offs = [
      handle.current!.onWritten(() => {
        throw boom;
      }),
      handle.current!.onWritten((key) => heard.push(key)),
    ];
    act(() => generation.generate(["assurance"], { aiAvailable: true }));
    expect(await screen.findByText("assurance: Assurance of Pardon written by the AI. / idle")).toBeInTheDocument();
    expect(screen.getByText("assurance error: none / until none; undo: replaced")).toBeInTheDocument();
    expect(heard).toEqual(["assurance"]);
    expect(logged).toHaveBeenCalledWith("A liturgy onWritten listener threw:", boom);
    await waitFor(() => expect(storedDraft().liturgy.cards.assurance.origin).toBe("ai"));
    for (const off of offs) off();
  });

  it("Undo restores only over the AI text it wrote: an edit from another tab since then stays", async () => {
    renderProvider(
      { "POST /scripture/passages": { passages: [PHILIPPIANS] }, "POST /liturgy/generate": generateRoute() },
      undefined,
      withAssurance("You are forgiven.", "typed"),
    );
    act(() => generation.generate(["assurance"], { aiAvailable: true }));
    expect(await screen.findByText("assurance: Assurance of Pardon written by the AI. / idle")).toBeInTheDocument();
    expect(screen.getByText("assurance error: none / until none; undo: replaced")).toBeInTheDocument();
    await waitFor(() => expect(storedDraft().liturgy.cards.assurance.origin).toBe("ai"));
    fromOtherTab(withAssurance("Edited in the other tab", "typed")(storedDraft()));
    expect(await screen.findByText("assurance: Edited in the other tab / idle")).toBeInTheDocument();
    act(() => generation.applyUndo("assurance"));
    expect(screen.getByText("assurance: Edited in the other tab / idle")).toBeInTheDocument();
    expect(screen.getByText("assurance error: none / until none; undo: none")).toBeInTheDocument();
  });

  it("a bulk run with a card dropped by the stale rule says only what was written", async () => {
    const held = heldRoute();
    const api = renderProvider({ "POST /scripture/passages": { passages: [PHILIPPIANS] }, "POST /liturgy/generate": held.route });
    act(() => generation.generate(FOUR, { aiAvailable: true, bulk: true }));
    await waitFor(() => expect(generateCalls(api.requests)).toHaveLength(MAX_IN_FLIGHT));
    await waitFor(() => expect(storedDraft().created_at).toBe(testDraft().created_at));
    fromOtherTab(withAssurance("From the other tab", "typed")(storedDraft()));
    expect(await screen.findByText("assurance: From the other tab / queued")).toBeInTheDocument();
    for (const key of FOUR.slice(0, 3)) held.release(key);
    expect(await screen.findByText("Wrote 3 of 4 sections.")).toBeInTheDocument();
    expect(screen.getByText("Kept your edits — the new AI draft for Assurance of Pardon was not used.")).toBeInTheDocument();
    expect(screen.queryByText(/show what went wrong/)).toBeNull();
  });

  it("words the bulk toast for one section, none written, and cards that show nothing", () => {
    expect(bulkMessage(0, 0, 0)).toBeNull(); // cancelled whole
    expect(bulkMessage(1, 1, 0)).toBe("Wrote 1 section.");
    expect(bulkMessage(5, 5, 0)).toBe("Wrote 5 sections.");
    expect(bulkMessage(2, 6, 4)).toBe("Wrote 2 of 6 sections. The rest show what went wrong.");
    expect(bulkMessage(0, 1, 1)).toBe("Couldn't write the section. It shows what went wrong.");
    expect(bulkMessage(0, 4, 4)).toBe("Couldn't write any sections. They show what went wrong.");
    // Cards dropped by the stale rule show nothing (their own toast said why).
    expect(bulkMessage(3, 4, 0)).toBe("Wrote 3 of 4 sections.");
    expect(bulkMessage(2, 5, 1)).toBe("Wrote 2 of 5 sections. One shows what went wrong.");
    expect(bulkMessage(1, 5, 2)).toBe("Wrote 1 of 5 sections. 2 show what went wrong.");
    expect(bulkMessage(0, 1, 0)).toBe("Couldn't write the section.");
    expect(bulkMessage(0, 3, 0)).toBe("Couldn't write any sections.");
    expect(bulkMessage(0, 3, 1)).toBe("Couldn't write any sections. One shows what went wrong.");
    expect(bulkMessage(0, 4, 2)).toBe("Couldn't write any sections. 2 show what went wrong.");
  });
});

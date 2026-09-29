/**
 * `useLectionarySync()` in the shell (S "useLectionarySync", Testing
 * `readings-step.test.tsx` fill and debounce cases; AC14). Only `Date` is
 * faked (Tuesday, September 29, 2026), so a fresh draft is dated Sunday,
 * October 4, and the 400 ms debounce runs on real timers.
 */
import { act, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import type { Lectionary } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import { applyReadingSet, editOccasion, setDate } from "@/lib/draft/readings";
import { draftKey, type DraftV1 } from "@/lib/draft/schema";
import { fakeError, installFakeApi, type FakeHandler } from "@/test/fake-api";
import { church, churchProfile, DRAFT_NOW, lectionary, lectionaryRoute, me, testDraft, USER_ID } from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { useLectionaryLookup } from "./lectionary-sync";

const KEY = draftKey(USER_ID, church().id);

/** What a step would show: the draft's readings and the lookup's date. */
function Probe() {
  const { draft, update } = useDraft();
  const { lookupDate, settled } = useLectionaryLookup();
  const r = draft.readings;
  return (
    <div>
      <p>Occasion: {r.occasion || "none"}</p>
      <p>Filled for: {r.reading_set?.date_iso ?? "nothing"}</p>
      <p>Lookup: {lookupDate} {settled ? "settled" : "waiting"}</p>
      <button type="button" onClick={() => update((d) => setDate(d, "2026-10-11"))}>
        October 11
      </button>
      <button type="button" onClick={() => update((d) => setDate(d, "2026-10-18"))}>
        October 18
      </button>
    </div>
  );
}

function renderSync(lookup: FakeHandler, seed?: DraftV1) {
  if (seed) window.localStorage.setItem(KEY, JSON.stringify(seed));
  const api = installFakeApi({ "GET /church": churchProfile(), "GET /lectionary/readings": lookup });
  const view = renderWithProviders(
    <BuilderLayout>
      <Probe />
    </BuilderLayout>,
    { me: me(), church: church(), path: "/builder/readings" },
  );
  const lookups = () => api.requests.filter((r) => r.path.startsWith("/lectionary/"));
  return { ...view, api, lookups };
}

/** October 18's own answer, so the test can tell which date filled the fields. */
function byDate(date: string): Lectionary {
  const answer = lectionary(date);
  return date === "2026-10-18"
    ? { ...answer, reading_sets: [{ ...answer.reading_sets[0], name: "Twenty-First Sunday after Pentecost" }] }
    : answer;
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("useLectionarySync (S useLectionarySync)", () => {
  it("fills a fresh draft from next Sunday's lectionary, looked up as the user with no church header", async () => {
    const { lookups } = renderSync(lectionaryRoute(byDate));
    expect(await screen.findByText("Occasion: Nineteenth Sunday after Pentecost")).toBeInTheDocument();
    expect(screen.getByText("Filled for: 2026-10-04")).toBeInTheDocument();
    expect(lookups().map((r) => r.path)).toEqual(["/lectionary/readings?date=2026-10-04"]);
    expect(lookups()[0].headers["X-Church-Id"]).toBeUndefined();
  });

  it("looks up only the last of two dates set within 400 ms, and refills the older date's lectionary fields", async () => {
    const { user, lookups } = renderSync(lectionaryRoute(byDate));
    await screen.findByText("Filled for: 2026-10-04");
    await user.click(screen.getByRole("button", { name: "October 11" }));
    await user.click(screen.getByRole("button", { name: "October 18" }));
    expect(screen.getByText("Lookup: 2026-10-04 waiting")).toBeInTheDocument();
    expect(await screen.findByText("Occasion: Twenty-First Sunday after Pentecost")).toBeInTheDocument();
    expect(screen.getByText("Filled for: 2026-10-18")).toBeInTheDocument();
    expect(screen.getByText("Lookup: 2026-10-18 settled")).toBeInTheDocument();
    expect(lookups().map((r) => r.path)).toEqual([
      "/lectionary/readings?date=2026-10-04",
      "/lectionary/readings?date=2026-10-18",
    ]);
  });

  it("never replaces typed fields", async () => {
    const { lookups } = renderSync(lectionaryRoute(byDate), testDraft((d) => editOccasion(d, "Harvest Sunday")));
    await waitFor(() => expect(lookups()).toHaveLength(1));
    await act(async () => {});
    expect(screen.getByText("Occasion: Harvest Sunday")).toBeInTheDocument();
    expect(screen.getByText("Filled for: nothing")).toBeInTheDocument();
  });

  it("leaves an older date's lectionary fields alone when the lookup fails or finds nothing", async () => {
    // Filled for October 4, then moved to Tuesday, September 29.
    const stale = setDate(applyReadingSet(testDraft(), lectionary("2026-10-04"), 0), "2026-09-29");
    for (const answer of [
      fakeError(502, "upstream_error", "The lectionary couldn't be reached. Enter readings yourself, or try again in a few minutes."),
      lectionaryRoute(),
    ]) {
      const { lookups, unmount } = renderSync(answer, stale);
      await waitFor(() => expect(lookups()).toHaveLength(1));
      await act(async () => {});
      expect(screen.getByText("Occasion: Nineteenth Sunday after Pentecost")).toBeInTheDocument();
      expect(screen.getByText("Filled for: 2026-10-04")).toBeInTheDocument();
      unmount();
    }
  });

  it("fills only in the visible tab: a hidden tab waits until it is shown", async () => {
    let state: DocumentVisibilityState = "hidden";
    vi.spyOn(document, "visibilityState", "get").mockImplementation(() => state);
    const { lookups } = renderSync(lectionaryRoute(byDate));
    await waitFor(() => expect(lookups()).toHaveLength(1));
    await act(async () => {});
    expect(screen.getByText("Occasion: none")).toBeInTheDocument();

    state = "visible";
    act(() => {
      document.dispatchEvent(new Event("visibilitychange"));
    });
    expect(await screen.findByText("Occasion: Nineteenth Sunday after Pentecost")).toBeInTheDocument();
  });

  it("a tab shown again first takes another tab's newer draft, so its fill never overwrites that tab's typing", async () => {
    let state: DocumentVisibilityState = "hidden";
    vi.spyOn(document, "visibilityState", "get").mockImplementation(() => state);
    const { lookups } = renderSync(lectionaryRoute(byDate));
    await waitFor(() => expect(lookups()).toHaveLength(1));
    await waitFor(() => expect(window.localStorage.getItem(KEY)).not.toBeNull()); // this tab's first write
    expect(screen.getByText("Occasion: none")).toBeInTheDocument();

    // The other tab typed an occasion and wrote it as it was hidden; its storage event comes
    // only after this tab's visibilitychange. This tab's clock is later, so a fill here would win.
    const theirs = JSON.stringify({
      ...editOccasion(testDraft(), "Harvest Sunday"),
      updated_at: new Date(DRAFT_NOW.getTime() + 1_000).toISOString(),
    });
    window.localStorage.setItem(KEY, theirs);
    vi.setSystemTime(DRAFT_NOW.getTime() + 2_000);
    state = "visible";
    act(() => {
      document.dispatchEvent(new Event("visibilitychange"));
    });
    act(() => {
      window.dispatchEvent(new StorageEvent("storage", { key: KEY, newValue: theirs }));
    });
    expect(await screen.findByText("Occasion: Harvest Sunday")).toBeInTheDocument();
    expect(screen.getByText("Filled for: nothing")).toBeInTheDocument();
    expect(JSON.parse(window.localStorage.getItem(KEY) ?? "{}").readings.occasion).toBe("Harvest Sunday");
  });
});

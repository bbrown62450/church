/**
 * `useLectionarySync()` in the shell (S "useLectionarySync", Testing
 * `readings-step.test.tsx` fill and debounce cases; AC14). Only `Date` is
 * faked (Tuesday, September 29, 2026), so a fresh draft is dated Sunday,
 * October 4, and the 400 ms debounce runs on real timers.
 */
import { act, screen, waitFor, within } from "@testing-library/react";
import { useEffect, type ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import type { Lectionary } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import { applyReadingSet, editOccasion, setDate } from "@/lib/draft/readings";
import { draftKey, type DraftV1 } from "@/lib/draft/schema";
import { WRITE_DELAY_MS } from "@/lib/draft/store";
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
      <button type="button" onClick={() => update((d) => editOccasion(d, "Harvest Sunday"))}>
        Type Harvest Sunday
      </button>
    </div>
  );
}

/** One builder tab; two calls in one test are two tabs sharing `localStorage`. */
function renderTab(extra?: ReactNode) {
  return renderWithProviders(
    <BuilderLayout>
      <Probe />
      {extra}
    </BuilderLayout>,
    { me: me(), church: church(), path: "/builder/readings" },
  );
}

function renderSync(lookup: FakeHandler, seed?: DraftV1, extra?: ReactNode) {
  if (seed) window.localStorage.setItem(KEY, JSON.stringify(seed));
  const api = installFakeApi({ "GET /church": churchProfile(), "GET /lectionary/readings": lookup });
  const view = renderTab(extra);
  const lookups = () => api.requests.filter((r) => r.path.startsWith("/lectionary/"));
  return { ...view, api, lookups };
}

/** The browser's `storage` event for what is stored now; jsdom sends none within one window, so the test delivers it, late. */
function deliverStorageEvent() {
  const newValue = window.localStorage.getItem(KEY);
  act(() => {
    window.dispatchEvent(new StorageEvent("storage", { key: KEY, newValue }));
  });
}

function storedOccasion(): string {
  return (JSON.parse(window.localStorage.getItem(KEY) ?? "{}") as DraftV1).readings.occasion;
}

const afterWriteDelay = () => act(() => new Promise((resolve) => setTimeout(resolve, WRITE_DELAY_MS + 50)));

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

  it("a fill made as the tab is shown never outranks the other tab's typing whose write lands just after", async () => {
    let state: DocumentVisibilityState = "hidden";
    vi.spyOn(document, "visibilityState", "get").mockImplementation(() => state);
    const { lookups } = renderSync(lectionaryRoute(byDate));
    await waitFor(() => expect(lookups()).toHaveLength(1));
    await waitFor(() => expect(window.localStorage.getItem(KEY)).not.toBeNull()); // this tab's first write

    // Shown: the direct read finds nothing newer, so this tab fills its copy (its clock is later).
    vi.setSystemTime(DRAFT_NOW.getTime() + 2_000);
    state = "visible";
    act(() => {
      document.dispatchEvent(new Event("visibilitychange"));
    });
    expect(await screen.findByText("Occasion: Nineteenth Sunday after Pentecost")).toBeInTheDocument();

    // Only now does the other tab's flush-on-hide write (typed a second after the stored draft) land.
    window.localStorage.setItem(
      KEY,
      JSON.stringify({
        ...editOccasion(testDraft(), "Harvest Sunday"),
        updated_at: new Date(DRAFT_NOW.getTime() + 1_000).toISOString(),
      }),
    );
    deliverStorageEvent();
    expect(await screen.findByText("Occasion: Harvest Sunday")).toBeInTheDocument();
    await afterWriteDelay();
    expect(storedOccasion()).toBe("Harvest Sunday");
  });

  it("two visible tabs: a lookup landing later on the other tab's stale copy never undoes typing after the first fill", async () => {
    window.localStorage.setItem(KEY, JSON.stringify(testDraft()));
    let releaseB = () => {};
    const bLands = new Promise<void>((resolve) => (releaseB = resolve));
    let calls = 0;
    installFakeApi({
      "GET /church": churchProfile(),
      "GET /lectionary/readings": async () => {
        if (++calls > 1) await bLands; // tab B's lookup lands later
        return byDate("2026-10-04");
      },
    });
    vi.setSystemTime(DRAFT_NOW.getTime() + 1_000);
    const a = renderTab();
    const b = renderTab();
    const tabA = within(a.container);
    const tabB = within(b.container);

    // Tab A fills, the user types an occasion in it, and A writes.
    expect(await tabA.findByText("Occasion: Nineteenth Sunday after Pentecost")).toBeInTheDocument();
    vi.setSystemTime(DRAFT_NOW.getTime() + 2_000);
    await a.user.click(tabA.getByRole("button", { name: "Type Harvest Sunday" }));
    await waitFor(() => expect(storedOccasion()).toBe("Harvest Sunday"));

    // Tab B's lookup lands before A's storage event: B fills its stale copy, with a later clock.
    vi.setSystemTime(DRAFT_NOW.getTime() + 3_000);
    releaseB();
    expect(await tabB.findByText("Occasion: Nineteenth Sunday after Pentecost")).toBeInTheDocument();
    deliverStorageEvent(); // A's write reaches B
    await afterWriteDelay();
    deliverStorageEvent(); // and whatever B wrote reaches A

    expect(tabA.getByText("Occasion: Harvest Sunday")).toBeInTheDocument();
    expect(tabB.getByText("Occasion: Harvest Sunday")).toBeInTheDocument();
    expect(storedOccasion()).toBe("Harvest Sunday");
  });

  it("an occasion typed on the render where the lookup first answers survives the fill that render asked for", async () => {
    // A child's effect runs before the sync's (its ancestor's) in the same commit, so the sync
    // decided to fill from the untyped draft; the check inside its recipe sees the typing.
    function TypesWhenTheLookupAnswers() {
      const { update } = useDraft();
      const answered = useLectionaryLookup().query.data !== undefined;
      useEffect(() => {
        if (answered) update((d) => (d.readings.occasion ? d : editOccasion(d, "Harvest Sunday")));
      }, [answered, update]);
      return null;
    }
    const { lookups } = renderSync(lectionaryRoute(byDate), undefined, <TypesWhenTheLookupAnswers />);
    await waitFor(() => expect(lookups()).toHaveLength(1));
    expect(await screen.findByText("Occasion: Harvest Sunday")).toBeInTheDocument();
    await act(async () => {});
    expect(screen.getByText("Occasion: Harvest Sunday")).toBeInTheDocument();
    expect(screen.getByText("Filled for: nothing")).toBeInTheDocument();
  });
});

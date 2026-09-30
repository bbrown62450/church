/**
 * The Hymns step (S "User experience", Testing `hymns-step.test.tsx`; F §4.6,
 * §4.8). The step runs inside the real builder layout against the fake API.
 * The clock is Tuesday, September 29, 2026 (only `Date` is faked), so a fresh
 * draft is dated Sunday, October 4, 2026, and the lectionary answers "no
 * readings", so the readings stay as each test seeds them.
 */
import { act, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import { Toaster } from "@/components/ui/sonner";
import type { ChurchProfile, HymnSuggestionBody } from "@/lib/api/types";
import { ChurchProvider } from "@/lib/church-context";
import { useDraft } from "@/lib/draft/context";
import { editOccasion, setDate } from "@/lib/draft/readings";
import { draftKey, type DraftV1, type HymnPick } from "@/lib/draft/schema";
import { pickFromHymn } from "@/lib/hymns/picks";
import { keys } from "@/lib/queries/keys";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import {
  church,
  CHURCH_IDS,
  churchProfile,
  DRAFT_NOW,
  gg2013,
  hymnals,
  hymnListRoute,
  hymnMatch,
  hymnSuggestions,
  lectionaryRoute,
  me,
  scriptureMatches,
  testDraft,
  twoHymnals,
  USER_ID,
} from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { HymnsStep } from "./hymns-step";

const KEY = draftKey(USER_ID, church().id);
const [HOLY, PRAISE, COME, GRACE, , FAITHFUL, HERE, , SENT] = gg2013();
/** Grace's recent use around October 4, 2026: sung September 6, planned October 18. */
const RECENT = { "Great Is Thy Faithfulness": "2026-09-06", "Praise, My Soul, the King of Heaven": "2026-10-18" };

const pick = pickFromHymn;

function draftWith(hymns: Partial<DraftV1["hymns"]> = {}, readings: Partial<DraftV1["readings"]> = {}): DraftV1 {
  return testDraft((d) => ({ ...d, readings: { ...d.readings, ...readings }, hymns: { ...d.hymns, ...hymns } }));
}

function slots(opening: HymnPick | null, response: HymnPick | null = null, closing: HymnPick | null = null) {
  return { slots: { opening, response, closing } };
}

function stored(key = KEY): DraftV1 {
  return JSON.parse(window.localStorage.getItem(key) ?? "null") as DraftV1;
}

/** The step in the builder layout, with a Toaster for toast text; `routes` replace the defaults. */
function renderStep(draft: DraftV1 = testDraft(), routes: Record<string, FakeHandler> = {}, extra: ReactNode = null) {
  window.localStorage.setItem(KEY, JSON.stringify(draft));
  const api = installFakeApi({
    "GET /church": churchProfile(),
    "GET /lectionary/readings": lectionaryRoute(),
    "GET /hymnals": hymnals(),
    "GET /hymns": hymnListRoute(undefined, RECENT),
    "POST /hymns/scripture-matches": scriptureMatches(),
    ...routes,
  });
  const view = renderWithProviders(
    <>
      <BuilderLayout>
        <HymnsStep />
        {extra}
      </BuilderLayout>
      <Toaster />
    </>,
    { me: me(), church: church(), path: "/builder/hymns" },
  );
  return { ...view, api };
}

function card(slot: "Opening" | "Response" | "Closing") {
  return screen.getByRole("region", { name: `${slot} hymn` });
}

/** The slot's picker once its hymnal has loaded. */
async function readyPicker(slot: "Opening" | "Response" | "Closing") {
  const input = await within(await screen.findByRole("region", { name: `${slot} hymn` })).findByRole("combobox", {
    name: `${slot} hymn`,
  });
  await waitFor(() => expect(input).toBeEnabled());
  return input;
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("the Hymns step (S User experience)", () => {
  it("shows the draft's picks before the hymnal loads, with the pickers waiting, then the live hymn", async () => {
    let release!: () => void;
    const loaded = new Promise<void>((resolve) => (release = resolve));
    const listRoute = hymnListRoute(undefined, RECENT);
    const snapshot = { ...pick(COME), title: "Come, Thou Almighty King (old title)" };
    renderStep(draftWith(slots(snapshot)), {
      "GET /hymns": async (req: RecordedRequest) => {
        await loaded;
        return listRoute(req);
      },
    });
    expect(await screen.findByRole("heading", { level: 2, name: "Hymns" })).toBeInTheDocument();
    expect(screen.getByText("Choose an opening, response and closing hymn.")).toBeInTheDocument();
    const opening = card("Opening");
    expect(within(opening).getByText("Gathering / call to worship")).toBeInTheDocument();
    expect(within(opening).getByText("#403 Come, Thou Almighty King (old title)")).toBeInTheDocument();
    const response = within(card("Response")).getByRole("combobox", { name: "Response hymn" });
    expect(response).toBeDisabled();
    expect(response).toHaveAttribute("placeholder", "Loading hymnal…");
    expect(within(card("Response")).getByText("After the sermon — responds to the scripture (NT reading)")).toBeInTheDocument();
    expect(within(card("Closing")).getByText("Joyful / sending")).toBeInTheDocument();
    expect(within(opening).getByRole("button", { name: "Change" })).toBeDisabled(); // no disabled field to focus
    release();
    // The live title shows; the draft keeps its snapshot (a rename never marks it dirty).
    expect(await within(opening).findByText("#403 Come, Thou Almighty King")).toBeInTheDocument();
    await waitFor(() => expect(response).toHaveAttribute("placeholder", "Search by title or number"));
    expect(within(opening).getByRole("button", { name: "Change" })).toBeEnabled();
    expect(stored().hymns.slots.opening?.title).toBe("Come, Thou Almighty King (old title)");
    expect(within(opening).getByRole("link", { name: "Listen to Come, Thou Almighty King on Hymnary.org" })).toHaveAttribute(
      "href",
      "https://hymnary.org/hymn/GG2013/403",
    );
    expect(
      screen.getByText(
        "Hymn information and links courtesy of Hymnary.org. Individual hymns may carry their own copyright — see each hymn's page.",
      ),
    ).toBeInTheDocument();
  });

  it("writes the chosen hymn to the draft, and every request names the church", async () => {
    const { user, api } = renderStep();
    const input = await readyPicker("Opening");
    await user.type(input, "403");
    await user.click(await screen.findByRole("option", { name: /#403 Come, Thou Almighty King/ }));
    expect(await within(card("Opening")).findByText("#403 Come, Thou Almighty King")).toBeInTheDocument();
    await waitFor(() => expect(stored().hymns.slots.opening).toEqual(pick(COME)));
    const churchCalls = api.requests.filter((r) => !r.path.startsWith("/lectionary"));
    expect(churchCalls.map((r) => r.path)).toEqual(
      expect.arrayContaining(["/church", "/hymnals", "/hymns?hymnal=GG2013&limit=2000&recent_for_date=2026-10-04"]),
    );
    expect(churchCalls.every((r) => r.headers["X-Church-Id"] === church().id)).toBe(true);
  });

  it("shows the empty-hymnal state instead of the pickers; a pick still shows, as not in the hymnal", async () => {
    const { api } = renderStep(draftWith(slots(pick(COME))), { "GET /hymnals": hymnals({ items: [], effective_hymnal: null }) });
    expect(await screen.findByRole("heading", { name: "This church's hymnal is empty" })).toBeInTheDocument();
    expect(screen.getByText("Add hymns in the current app under Settings → Hymns.")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Settings/ })).toBeNull(); // Settings → Hymns ships in 6a
    expect(screen.queryByRole("combobox")).toBeNull();
    expect(within(card("Opening")).getByText("#403 Come, Thou Almighty King")).toBeInTheDocument();
    expect(within(card("Opening")).getByText("Not in your hymnal. Choose a replacement.")).toBeInTheDocument();
    expect(api.requests.some((r) => r.path.startsWith("/hymns"))).toBe(false);
  });

  it("shows Couldn't load this church's hymnal with Retry when the list fails, never the empty state", async () => {
    let fail = true;
    const listRoute = hymnListRoute(undefined, RECENT);
    const { user } = renderStep(draftWith(slots(pick(COME))), {
      "GET /hymns": (req: RecordedRequest) => (fail ? fakeError(500, "internal_error", "Something went wrong.") : listRoute(req)),
    });
    expect(await screen.findByText("Couldn't load this church's hymnal.")).toBeInTheDocument();
    expect(screen.queryByText("This church's hymnal is empty")).toBeNull();
    expect(screen.queryByRole("combobox")).toBeNull();
    expect(within(card("Opening")).getByText("#403 Come, Thou Almighty King")).toBeInTheDocument(); // the snapshot stays
    fail = false;
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await readyPicker("Response")).toBeInTheDocument();
    expect(screen.queryByText("Couldn't load this church's hymnal.")).toBeNull();
  });

  it("keeps the pickers, the toolbar and a pending Suggest when a background refetch fails after loading", async () => {
    let fail = false;
    const listRoute = hymnListRoute(undefined, RECENT);
    const failing = () => fakeError(500, "internal_error", "Something went wrong.");
    const answer = held(THREE_EACH);
    const { user, queryClient } = renderStep(draftWith(slots(pick(COME))), {
      "GET /hymnals": () => (fail ? failing() : hymnals()),
      "GET /hymns": (req: RecordedRequest) => (fail ? failing() : listRoute(req)),
      "POST /hymns/suggestions": answer.handler,
    });
    const input = await readyPicker("Response");
    await user.click(await suggestButton());
    await screen.findByRole("button", { name: "Suggesting…" });
    fail = true;
    await act(() => queryClient.refetchQueries({ type: "active" }));
    expect(queryClient.getQueryState(keys.hymnals(church().id))?.status).toBe("error");
    const listKey = keys.hymns(church().id, { hymnal: "GG2013", limit: 2000, recent_for_date: "2026-10-04" });
    expect(queryClient.getQueryState(listKey)?.status).toBe("error");
    // TanStack Query v5 keeps the loaded data with the error: the picker still works afterwards.
    await user.type(input, "650");
    await user.click(await screen.findByRole("option", { name: /#650 Amazing Grace/ }));
    expect(await within(card("Response")).findByText("#650 Amazing Grace")).toBeInTheDocument();
    expect(screen.queryByText("Couldn't load this church's hymnal.")).toBeNull();
    expect(within(card("Opening")).getByRole("button", { name: "Change" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Suggesting…" })).toBeInTheDocument(); // the toolbar stayed mounted
    answer.release();
    expect(await screen.findByText(/^Suggestions ready/)).toBeInTheDocument();
  });
});

describe("slot cards (S Slot cards, Notices)", () => {
  it("marks a deleted or unresolved pick Not in your hymnal, without crashing or dropping it", async () => {
    const gone = { ...pick(COME), hymn_id: "00000000-0000-4000-8000-000000009998" };
    const archived = { hymn_id: null, title: "Be Thou My Vision", number: 339, hymnal: "GG2013" };
    renderStep(draftWith(slots(gone, archived)));
    const opening = await screen.findByRole("region", { name: "Opening hymn" });
    expect(await within(opening).findByText("Not in your hymnal. Choose a replacement.")).toBeInTheDocument();
    expect(within(opening).getByText("#403 Come, Thou Almighty King")).toBeInTheDocument(); // the snapshot
    expect(within(card("Response")).getByText("#339 Be Thou My Vision")).toBeInTheDocument();
    expect(within(card("Response")).getByText("Not in your hymnal. Choose a replacement.")).toBeInTheDocument();
    expect(stored().hymns.slots).toEqual(slots(gone, archived).slots);
  });

  it("notes a hymn used before or planned after the service, and the same hymn in two slots", async () => {
    renderStep(draftWith(slots(pick(PRAISE), pick(FAITHFUL), pick(PRAISE))));
    const opening = await screen.findByRole("region", { name: "Opening hymn" });
    expect(
      await within(opening).findByText("Also planned for October 18, 2026 — within 12 weeks of this service."),
    ).toBeInTheDocument();
    expect(within(opening).getByText("Also chosen as the Closing hymn.")).toBeInTheDocument();
    expect(within(card("Closing")).getByText("Also chosen as the Opening hymn.")).toBeInTheDocument();
    expect(
      within(card("Response")).getByText("Used on September 6, 2026 — within 12 weeks of this service."),
    ).toBeInTheDocument();
    expect(within(card("Response")).queryByText(/Also chosen/)).toBeNull();
  });

  it("Change puts a focused picker in the row until Escape; choosing replaces the hymn, and same titles are told apart", async () => {
    const { user } = renderStep(draftWith(slots(pick(COME))));
    const opening = await screen.findByRole("region", { name: "Opening hymn" });
    await readyPicker("Response");
    await user.click(within(opening).getByRole("button", { name: "Change" }));
    const input = within(opening).getByRole("combobox", { name: "Opening hymn" });
    await waitFor(() => expect(input).toHaveFocus());
    await user.keyboard("{Escape}");
    expect(await within(opening).findByText("#403 Come, Thou Almighty King")).toBeInTheDocument();
    await user.click(within(opening).getByRole("button", { name: "Change" }));
    await user.type(within(opening).getByRole("combobox", { name: "Opening hymn" }), "amazing");
    const options = await screen.findAllByRole("option", { name: /Amazing Grace/ });
    expect(options.map((o) => o.textContent)).toEqual(["#649 Amazing Grace", "#650 Amazing Grace"]);
    await user.click(options[1]);
    expect(await within(opening).findByText("#650 Amazing Grace")).toBeInTheDocument();
    await waitFor(() => expect(within(opening).getByRole("button", { name: "Change" })).toHaveFocus());
    await waitFor(() => expect(stored().hymns.slots.opening?.number).toBe(650));
    // #650's link is not https, so it has no Listen link.
    expect(within(opening).queryByRole("link")).toBeNull();
  });

  it("✕ removes the hymn with a Removed toast whose Undo puts it back", async () => {
    const { user } = renderStep(draftWith(slots(pick(GRACE))));
    const opening = await screen.findByRole("region", { name: "Opening hymn" });
    await user.click(await within(opening).findByRole("button", { name: "Remove Amazing Grace" }));
    await waitFor(() => expect(within(opening).getByRole("combobox", { name: "Opening hymn" })).toHaveFocus());
    await waitFor(() => expect(stored().hymns.slots.opening).toBeNull());
    expect(await screen.findByText("Removed Amazing Grace.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Undo" }));
    expect(await within(opening).findByText("#649 Amazing Grace")).toBeInTheDocument();
    await waitFor(() => expect(stored().hymns.slots.opening).toEqual(pick(GRACE)));
  });

  it("Undo does nothing once another hymn fills the slot", async () => {
    function Typist() {
      const { update } = useDraft();
      return (
        <button type="button" onClick={() => update((d) => editOccasion(d, "Harvest"))}>
          Type an occasion
        </button>
      );
    }
    const { user } = renderStep(draftWith(slots(pick(GRACE))), {}, <Typist />);
    const opening = await screen.findByRole("region", { name: "Opening hymn" });
    await user.click(await within(opening).findByRole("button", { name: "Remove Amazing Grace" }));
    await user.type(await readyPicker("Opening"), "403");
    await user.click(await screen.findByRole("option", { name: /#403 Come, Thou Almighty King/ }));
    expect(await within(opening).findByText("#403 Come, Thou Almighty King")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Undo" }));
    // A later write lands after any write the Undo could have caused (the same 400 ms delay).
    await user.click(screen.getByRole("button", { name: "Type an occasion" }));
    await waitFor(() => expect(stored().readings.occasion).toBe("Harvest"));
    expect(stored().hymns.slots.opening).toEqual(pick(COME));
    expect(within(opening).getByText("#403 Come, Thou Almighty King")).toBeInTheDocument();
  });

  it("Undo after a church switch: the toast is dismissed and its handler changes no draft", async () => {
    const shown = vi.spyOn(toast, "message");
    const dismissed = vi.spyOn(toast, "dismiss");
    const hope: ChurchProfile = churchProfile({ id: CHURCH_IDS.hope, name: "Hope" });
    const hopeKey = draftKey(USER_ID, hope.id);
    window.localStorage.setItem(KEY, JSON.stringify(draftWith(slots(pick(HOLY)))));
    installFakeApi({
      "GET /church": (req: RecordedRequest) => (req.headers["X-Church-Id"] === hope.id ? hope : churchProfile()),
      "GET /lectionary/readings": lectionaryRoute(),
      "GET /hymnals": hymnals(),
      "GET /hymns": hymnListRoute(undefined, RECENT),
    });
    function Typist() {
      const { update } = useDraft();
      return (
        <button type="button" onClick={() => update((d) => editOccasion(d, "Harvest at Hope"))}>
          Type an occasion
        </button>
      );
    }
    const tree = (c: ChurchProfile) => (
      <ChurchProvider key={c.id} value={c}>
        <BuilderLayout>
          <HymnsStep />
          <Typist />
        </BuilderLayout>
      </ChurchProvider>
    );
    const { user, rerender } = renderWithProviders(tree(churchProfile()), { me: me(), path: "/builder/hymns" });
    const opening = await screen.findByRole("region", { name: "Opening hymn" });
    await user.click(await within(opening).findByRole("button", { name: "Remove Holy, Holy, Holy! Lord God Almighty" }));
    await waitFor(() => expect(stored().hymns.slots.opening).toBeNull());
    const [, options] = shown.mock.calls[0];
    const undo = (options?.action as unknown as { onClick: () => void }).onClick;
    const id = shown.mock.results[0].value;

    rerender(tree(hope)); // the (church) layout remounts under the other church
    await screen.findByRole("region", { name: "Opening hymn" });
    expect(dismissed).toHaveBeenCalledWith(id);
    act(() => undo());
    // A later write in Hope lands after any write the Undo could have caused (the same 400 ms delay).
    await user.click(screen.getByRole("button", { name: "Type an occasion" }));
    await waitFor(() => expect(stored(hopeKey)?.readings.occasion).toBe("Harvest at Hope"));
    expect(stored(hopeKey).hymns.slots.opening).toBeNull();
    expect(stored().hymns.slots.opening).toBeNull(); // Grace's draft is not written either
  });
});

describe("the toolbar (S Toolbar)", () => {
  it("switches hymnals from the select, keeping the picks, and notes a hymnal with no scripture references", async () => {
    // One hymnal (production today): no select.
    const one = renderStep(draftWith(slots(pick(COME))));
    await screen.findByRole("switch", { name: "Exclude hymns used within 12 weeks" });
    expect(screen.queryByRole("combobox", { name: "Hymnal" })).toBeNull();
    expect(within(card("Opening")).queryByText("GG2013")).toBeNull();
    one.unmount();

    const { user, api } = renderStep(draftWith(slots(pick(COME))), { "GET /hymnals": twoHymnals() });
    const select = await screen.findByRole("combobox", { name: "Hymnal" });
    expect(select).toHaveTextContent("GG2013 · 853 hymns");
    expect(screen.getByText("Which hymnal to choose hymns from for this service.")).toBeInTheDocument();
    expect(within(card("Opening")).getByText("GG2013")).toBeInTheDocument(); // 2+ hymnals: each pick shows its hymnal
    await user.click(select);
    await user.click(await screen.findByRole("option", { name: "PH1990 · 605 hymns" }));
    await waitFor(() => expect(stored().hymns.hymnal).toBe("PH1990"));
    expect(stored().hymns.slots.opening).toEqual(pick(COME)); // picks keep their own hymnal
    await waitFor(() =>
      expect(api.requests.map((r) => r.path)).toContain("/hymns?hymnal=PH1990&limit=2000&recent_for_date=2026-10-04"),
    );
    expect(
      await screen.findByText("PH1990 has no scripture references, so scripture matches and AI response picks will be weaker."),
    ).toBeInTheDocument();
    const input = await readyPicker("Response");
    await user.type(input, "long");
    expect(await screen.findByRole("option", { name: /#1 Come, Thou Long-Expected Jesus/ })).toBeInTheDocument();
    // Choosing the effective hymnal again stores null, so it is not unsaved work (owner answer 1).
    await user.keyboard("{Escape}");
    await user.click(screen.getByRole("combobox", { name: "Hymnal" }));
    await user.click(await screen.findByRole("option", { name: "GG2013 · 853 hymns" }));
    await waitFor(() => expect(stored().hymns.hymnal).toBeNull());
  });

  it("keeps a vanished stored hymnal in the draft and shows the effective one, writing nothing, also while GET /hymnals fails", async () => {
    const saved = draftWith({ hymnal: "HYMNAL1982" });
    const first = renderStep(saved, { "GET /hymnals": fakeError(500, "internal_error", "Something went wrong.") });
    expect(await screen.findByText("Couldn't load this church's hymnal.")).toBeInTheDocument();
    expect(first.api.requests.some((r) => r.path.startsWith("/hymns"))).toBe(false);
    first.unmount();
    expect(stored().hymns).toEqual(saved.hymns);
    expect(stored().updated_at).toBe(saved.updated_at);

    const { api } = renderStep(saved);
    expect(
      await screen.findByText("HYMNAL1982 is no longer in your church's hymnals. Showing GG2013 instead."),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(api.requests.map((r) => r.path)).toContain("/hymns?hymnal=GG2013&limit=2000&recent_for_date=2026-10-04"),
    );
    expect(stored().hymns.hymnal).toBe("HYMNAL1982");
    expect(stored().updated_at).toBe(saved.updated_at); // no write, so not dirty
  });

  it("the Exclude switch counts the hidden hymns, and is off without a valid date", async () => {
    const { user, unmount } = renderStep();
    const exclude = await screen.findByRole("switch", { name: "Exclude hymns used within 12 weeks" });
    expect(exclude).toBeChecked();
    expect(
      screen.getByText("Hides hymns sung in the 12 weeks before this service or planned in the 12 weeks after it. 2 hymns are hidden."),
    ).toBeInTheDocument();
    await user.click(exclude);
    await waitFor(() => expect(stored().hymns.exclude_recent).toBe(false));
    expect(screen.queryByText(/hymns are hidden/)).toBeNull();
    unmount();

    const { api } = renderStep(setDate(testDraft(), ""));
    const off = await screen.findByRole("switch", { name: "Exclude hymns used within 12 weeks" });
    expect(off).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByText("Pick a valid date in step 1 to check recent use.")).toBeInTheDocument();
    expect(api.requests.map((r) => r.path)).toContain("/hymns?hymnal=GG2013&limit=2000"); // no recent_for_date
  });

  it("exclusion never clears a pick: the switch hides recent hymns from the picker and keeps a recent pick with its notice", async () => {
    const { user } = renderStep(draftWith(slots(pick(FAITHFUL))));
    const opening = await screen.findByRole("region", { name: "Opening hymn" });
    expect(
      await within(opening).findByText("Used on September 6, 2026 — within 12 weeks of this service."),
    ).toBeInTheDocument();
    const input = await readyPicker("Response");
    await user.type(input, "great");
    expect(await screen.findByText("No hymns match “great”.")).toBeInTheDocument();
    expect(screen.getByText("1 more used within 12 weeks is hidden.")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    const exclude = screen.getByRole("switch", { name: "Exclude hymns used within 12 weeks" });
    await user.click(exclude);
    await waitFor(() => expect(stored().hymns.exclude_recent).toBe(false));
    await user.clear(input);
    await user.type(input, "great");
    const option = await screen.findByRole("option", { name: /#700 Great Is Thy Faithfulness/ });
    expect(within(option).getByText("Used Sep 6")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    await user.click(exclude);
    await waitFor(() => expect(stored().hymns.exclude_recent).toBe(true));
    expect(stored().hymns.slots).toEqual(slots(pick(FAITHFUL)).slots); // AC12: toggling never touched a slot
    expect(within(opening).getByText("#700 Great Is Thy Faithfulness")).toBeInTheDocument();
    expect(within(opening).getByText("Used on September 6, 2026 — within 12 weeks of this service.")).toBeInTheDocument();
  });
});

// --- AI suggestions (S "AI suggestion flow"; owner decision 4, F D16) -----------------------

/** A button that moves the draft's date, as step 1 would. */
function DateProbe() {
  const { update } = useDraft();
  return (
    <button type="button" onClick={() => update((d) => setDate(d, "2026-10-11"))}>
      Move to October 11
    </button>
  );
}

/** A route that answers only when `release` is called. */
function held(answer: () => unknown) {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => (release = resolve));
  return {
    handler: async () => {
      await gate;
      return answer();
    },
    release: () => release(),
  };
}

/** Three hymns for each slot, 4 recently used ones left out. */
const THREE_EACH = () =>
  hymnSuggestions(
    { opening: [HOLY, COME, HERE], response: [FAITHFUL, COME, HOLY], closing: [PRAISE, HERE, SENT] },
    { excluded_recent_count: 4 },
  );

function ideaNames(slot: "Opening" | "Response" | "Closing"): string[] {
  const group = within(card(slot)).queryByRole("group", { name: `Other ideas for the ${slot.toLowerCase()} hymn` });
  return group ? within(group).getAllByRole("button").map((b) => b.getAttribute("aria-label") ?? "") : [];
}

async function suggestButton() {
  const button = await screen.findByRole("button", { name: "Suggest hymns" });
  await waitFor(() => expect(button).toBeEnabled());
  return button;
}

describe("Suggest hymns (S AI suggestion flow)", () => {
  it("fills only the empty slots, keeps the member's pick, and shows at least 2 ideas under every slot", async () => {
    const readings = {
      scriptures: ["Isaiah 5:1-7", "Philippians 3:4b-14"],
      occasion: "Nineteenth Sunday after Pentecost",
      selected_nt_ref: "Philippians 3:4b-14",
    };
    const { user, api, queryClient } = renderStep(draftWith(slots(null, pick(GRACE)), readings), {
      "POST /hymns/suggestions": THREE_EACH(),
    });
    queryClient.setQueryData(keys.passage("web", "Philippians 3:4b-14"), {
      reference: "Philippians 3:4b-14",
      status: "ok",
      sections: [{ reference: "Philippians 3:4b-14", status: "ok", text: "I press on toward the goal." }],
    });
    expect(await screen.findByText("Fills empty slots and shows other ideas under each hymn.")).toBeInTheDocument();
    expect(screen.queryByText(/^Tip:/)).toBeNull();
    await user.click(await suggestButton());
    expect(
      await screen.findByText("Suggestions ready. Tap an idea under a hymn to swap it in. 4 recently used hymns were left out."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Suggestions favor older and familiar hymns. Newer hymns show the year their words were written."),
    ).toBeInTheDocument();
    const body = api.requests.find((r) => r.path === "/hymns/suggestions")?.body as HymnSuggestionBody;
    expect(body).toEqual({
      service_date_iso: "2026-10-04",
      occasion: "Nineteenth Sunday after Pentecost",
      scriptures: ["Isaiah 5:1-7", "Philippians 3:4b-14"],
      selected_nt_ref: "Philippians 3:4b-14",
      hymnal: "GG2013",
      exclude_recent: true,
      current_picks: { opening: null, response: GRACE.id, closing: null },
      nt_text: "I press on toward the goal.",
    });
    await waitFor(() => expect(stored().hymns.slots).toEqual(slots(pick(HOLY), pick(GRACE), pick(PRAISE)).slots));
    expect(stored().hymns.alternatives?.for_date_iso).toBe("2026-10-04");
    expect(ideaNames("Opening")).toEqual([
      "Use Come, Thou Almighty King as the opening hymn",
      "Use Here I Am, Lord, written 1981, as the opening hymn",
    ]);
    expect(ideaNames("Response")).toHaveLength(3); // a filled slot: 3 ideas, its own pick left out
    expect(ideaNames("Closing")).toEqual([
      "Use Here I Am, Lord, written 1981, as the closing hymn",
      "Use Sent Forth by God's Blessing as the closing hymn",
    ]);
    expect(within(card("Response")).getByText("#649 Amazing Grace")).toBeInTheDocument();
    expect(within(card("Response")).getByText("Used Sep 6")).toBeInTheDocument(); // a recently used idea
    expect(within(card("Opening")).getAllByText("Written 1981")).toHaveLength(1);
  });

  it("a tap swaps an idea with the pick and a second tap swaps back; the ideas hide when the date changes", async () => {
    const { user } = renderStep(testDraft(), { "POST /hymns/suggestions": THREE_EACH() }, <DateProbe />);
    await user.click(await suggestButton());
    await screen.findByText(/^Suggestions ready/);
    const opening = card("Opening");
    await user.click(within(opening).getByRole("button", { name: "Use Come, Thou Almighty King as the opening hymn" }));
    expect(await within(opening).findByText("#403 Come, Thou Almighty King")).toBeInTheDocument();
    expect(ideaNames("Opening")).toEqual([
      "Use Holy, Holy, Holy! Lord God Almighty as the opening hymn",
      "Use Here I Am, Lord, written 1981, as the opening hymn",
    ]);
    await user.click(
      within(opening).getByRole("button", { name: "Use Holy, Holy, Holy! Lord God Almighty as the opening hymn" }),
    );
    expect(await within(opening).findByText("#1 Holy, Holy, Holy! Lord God Almighty")).toBeInTheDocument();
    expect(ideaNames("Opening")).toEqual([
      "Use Come, Thou Almighty King as the opening hymn",
      "Use Here I Am, Lord, written 1981, as the opening hymn",
    ]);
    await user.click(screen.getByRole("button", { name: "Move to October 11" }));
    await waitFor(() => expect(ideaNames("Opening")).toEqual([]));
    expect(within(opening).getByText("#1 Holy, Holy, Holy! Lord God Almighty")).toBeInTheDocument(); // the pick stays
  });

  it("a pick made while the request runs is kept and gets ideas", async () => {
    const answer = held(THREE_EACH);
    const { user } = renderStep(testDraft(), { "POST /hymns/suggestions": answer.handler });
    await user.click(await suggestButton());
    expect(await screen.findByRole("button", { name: "Suggesting…" })).toBeDisabled();
    const input = await readyPicker("Response");
    await user.type(input, "650");
    await user.click(await screen.findByRole("option", { name: /#650 Amazing Grace/ }));
    await waitFor(() => expect(stored().hymns.slots.response?.number).toBe(650));
    answer.release();
    await screen.findByText(/^Suggestions ready/);
    await waitFor(() => expect(stored().hymns.slots.opening?.title).toBe("Holy, Holy, Holy! Lord God Almighty"));
    expect(stored().hymns.slots.response?.number).toBe(650);
    expect(ideaNames("Response")).toHaveLength(3);
  });

  it("drops the answer when the date changed during the wait", async () => {
    const answer = held(THREE_EACH);
    const { user } = renderStep(testDraft(), { "POST /hymns/suggestions": answer.handler }, <DateProbe />);
    await user.click(await suggestButton());
    await screen.findByRole("button", { name: "Suggesting…" });
    await user.click(screen.getByRole("button", { name: "Move to October 11" }));
    await waitFor(() => expect(stored().readings.date_iso).toBe("2026-10-11"));
    answer.release();
    expect(await screen.findByText("The date changed while suggestions were loading. Try again.")).toBeInTheDocument();
    expect(stored().hymns.slots).toEqual(testDraft().hymns.slots);
    expect(stored().hymns.alternatives).toBeNull();
  });

  it("Cancel stops waiting and returns to idle; after 8 s it says it is still working", async () => {
    vi.useRealTimers(); // a second useFakeTimers call would keep beforeEach's Date-only fake
    vi.useFakeTimers({ toFake: ["Date", "setTimeout", "clearTimeout"], shouldAdvanceTime: true });
    vi.setSystemTime(DRAFT_NOW);
    const answer = held(THREE_EACH);
    const { user, api } = renderStep(testDraft(), { "POST /hymns/suggestions": answer.handler });
    await user.click(await suggestButton());
    await screen.findByRole("button", { name: "Suggesting…" });
    expect(screen.queryByText("Still working — this can take up to a minute.")).toBeNull();
    act(() => {
      vi.advanceTimersByTime(8_000);
    });
    expect(screen.getByText("Still working — this can take up to a minute.")).toHaveAttribute("aria-live", "polite");
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(await screen.findByRole("button", { name: "Suggest hymns" })).toBeEnabled();
    expect(api.requests.filter((r) => r.path === "/hymns/suggestions")).toHaveLength(1);
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.queryByText(/^Suggestions ready/)).toBeNull();
    answer.release();
  });

  it("shows each failure's own copy under the button, and a server error as a toast", async () => {
    const cases: [ReturnType<typeof fakeError>, string][] = [
      [
        fakeError(503, "ai_not_configured", "AI suggestions aren't set up on this app yet."),
        "AI suggestions aren't set up on this app yet. You can still choose hymns yourself.",
      ],
      [fakeError(503, "ai_busy", "The AI service is busy. Try again in a minute."), "The AI service is busy. Try again in a minute."],
      [fakeError(504, "ai_timeout", "The AI took too long to answer. Try again."), "The AI took too long to answer. Try again."],
      [
        fakeError(502, "ai_upstream_error", "The AI service had a problem. Try again."),
        "The AI service had a problem. Try again in a moment.",
      ],
      [
        fakeError(422, "invalid_request", "This hymnal has no hymns to suggest from."),
        "This hymnal has no hymns to suggest from.",
      ],
    ];
    for (const [response, copy] of cases) {
      const { user, unmount } = renderStep(testDraft(), { "POST /hymns/suggestions": response });
      await user.click(await suggestButton());
      expect(await screen.findByRole("alert")).toHaveTextContent(copy);
      expect(stored().hymns.slots).toEqual(testDraft().hymns.slots); // nothing stored
      unmount();
    }
    const limited = renderStep(testDraft(), {
      "POST /hymns/suggestions": {
        ...fakeError(429, "rate_limited", "Too many requests.", { details: { retry_after_seconds: 1 } }),
        headers: { "Retry-After": "1" },
      },
    });
    await limited.user.click(await suggestButton());
    expect(await screen.findByRole("alert")).toHaveTextContent("Too many requests — try again in 1 s.");
    expect(await screen.findByText("Try again now.", {}, { timeout: 3_000 })).toBeInTheDocument();
    limited.unmount();

    const { user } = renderStep(testDraft(), {
      "POST /hymns/suggestions": fakeError(500, "internal_error", "Something went wrong."),
    });
    await user.click(await suggestButton());
    expect(await screen.findByText("Something went wrong. (Ref: 4f9a2c1e)")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("says when a slot or every slot got nothing, and waits for a valid date; the tip asks for readings first", async () => {
    const partly = hymnSuggestions({ opening: [HOLY, COME, GRACE], response: [], closing: [PRAISE, GRACE, SENT] });
    const one = renderStep(testDraft(), { "POST /hymns/suggestions": partly });
    expect(await screen.findByText("Tip: add the readings in step 1 first — suggestions use them.")).toBeInTheDocument();
    await one.user.click(await suggestButton());
    expect(await within(card("Response")).findByText("No suggestion for this slot.")).toBeInTheDocument();
    expect(within(card("Opening")).queryByText("No suggestion for this slot.")).toBeNull();
    expect(screen.queryByText(/Suggestions favor older/)).toBeNull(); // no flagged hymn returned
    one.unmount();

    const none = renderStep(testDraft(), {
      "POST /hymns/suggestions": hymnSuggestions({ opening: [], response: [], closing: [] }),
    });
    await none.user.click(await suggestButton());
    expect(
      await screen.findByText("The AI didn't pick any hymns from this hymnal. Try again, or choose hymns yourself."),
    ).toBeInTheDocument();
    none.unmount();

    renderStep(setDate(testDraft(), ""));
    await screen.findByRole("switch", { name: "Exclude hymns used within 12 weeks" });
    expect(screen.getByRole("button", { name: "Suggest hymns" })).toBeDisabled();
  });
});

// --- Hymns for the readings (S "Hymns for the readings") ------------------------------------

const LINES = ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"];

/** The section, opened (it starts closed below md, and jsdom's window is narrow). */
async function openMatches(user: { click: (el: Element) => Promise<void> }) {
  const trigger = await screen.findByRole("button", { name: /^Hymns for the readings/ });
  await user.click(trigger);
  return trigger.closest("[data-slot=collapsible]") as HTMLElement;
}

describe("Hymns for the readings (S ScriptureMatches)", () => {
  it("asks for the draft's readings in the selected hymnal; Add → Response hymn sets the slot and Undo restores it until the slot changes again", async () => {
    const { user, api } = renderStep(draftWith(slots(null, pick(GRACE)), { scriptures: LINES }));
    const trigger = await screen.findByRole("button", { name: "Hymns for the readings 4" }); // the count, while closed
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    const matchCalls = api.requests.filter((r) => r.path === "/hymns/scripture-matches");
    expect(matchCalls.map((r) => r.body)).toEqual([
      { refs: LINES, hymnal: "GG2013", recent_for_date: "2026-10-04", max_results: 30 },
    ]);
    const section = await openMatches(user);
    const passage = within(section).getByRole("heading", { name: "Matches the readings" }).nextElementSibling as HTMLElement;
    expect(within(passage).getByText("#710 Here I Am, Lord")).toBeInTheDocument();
    expect(within(passage).getByText("Written 1981")).toBeInTheDocument();
    expect(within(passage).getByText("Matches Isaiah 5:1-7")).toBeInTheDocument();
    const chapter = within(section).getByRole("heading", { name: "Same chapter" }).nextElementSibling as HTMLElement;
    expect(within(chapter).getAllByRole("listitem")).toHaveLength(3);
    await user.click(within(section).getByRole("button", { name: "Add Holy, Holy, Holy! Lord God Almighty" }));
    await user.click(await screen.findByRole("menuitem", { name: "Response hymn" }));
    expect(await within(card("Response")).findByText("#1 Holy, Holy, Holy! Lord God Almighty")).toBeInTheDocument();
    await waitFor(() => expect(stored().hymns.slots.response).toEqual(pick(HOLY)));
    expect(await screen.findByText("Response hymn changed to Holy, Holy, Holy! Lord God Almighty.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Undo" }));
    await waitFor(() => expect(stored().hymns.slots.response).toEqual(pick(GRACE)));
    // Undo does nothing once another hymn fills the slot.
    act(() => toast.dismiss());
    await waitFor(() => expect(screen.queryByRole("button", { name: "Undo" })).toBeNull());
    await user.click(within(section).getByRole("button", { name: "Add Holy, Holy, Holy! Lord God Almighty" }));
    await user.click(await screen.findByRole("menuitem", { name: "Response hymn" }));
    await waitFor(() => expect(stored().hymns.slots.response).toEqual(pick(HOLY)));
    await user.click(within(card("Response")).getByRole("button", { name: "Change" }));
    await user.type(within(card("Response")).getByRole("combobox", { name: "Response hymn" }), "403");
    await user.click(await screen.findByRole("option", { name: /#403 Come, Thou Almighty King/ }));
    await user.click(await screen.findByRole("button", { name: "Undo" }));
    // Into an empty slot: no toast.
    await user.click(within(section).getByRole("button", { name: "Add Here I Am, Lord" }));
    await user.click(await screen.findByRole("menuitem", { name: "Closing hymn" }));
    await waitFor(() => expect(stored().hymns.slots.closing).toEqual(pick(HERE)));
    expect(stored().hymns.slots.response).toEqual(pick(COME)); // the Undo after Change did nothing
    expect(screen.queryByText(/^Closing hymn changed/)).toBeNull();
  });

  it("searches an extra reference with the readings, and says when one can't be read or nothing matches", async () => {
    const { user, api } = renderStep(draftWith({}, { scriptures: LINES }), {
      "POST /hymns/scripture-matches": (req: RecordedRequest) => {
        const refs = (req.body as { refs: string[] }).refs;
        return refs.includes("Transfiguration")
          ? scriptureMatches({ refs_used: refs, unparsed_refs: ["Transfiguration"], total_matched: 0, items: [] })
          : scriptureMatches();
      },
    });
    const section = await openMatches(user);
    const extra = within(section).getByLabelText("Additional scripture");
    expect(extra).toHaveAttribute("placeholder", "e.g. Matthew 17");
    expect(extra).toHaveAttribute("maxLength", "200");
    await user.type(extra, "Transfiguration{Enter}");
    expect(
      await within(section).findByText("Couldn't read “Transfiguration” as a scripture reference."),
    ).toBeInTheDocument();
    expect(
      within(section).getByText("No hymns in GG2013 match these readings. Try a shorter reference, such as “Matthew 17”."),
    ).toBeInTheDocument();
    const last = api.requests.filter((r) => r.path === "/hymns/scripture-matches").at(-1);
    expect((last?.body as { refs: string[] }).refs).toEqual([...LINES, "Transfiguration"]);
  });

  it("links to step 1 without references, and never searches a hymnal with no scripture references", async () => {
    const first = renderStep();
    const section = await openMatches(first.user);
    expect(within(section).getByText(/^Add the readings in step 1, or type a scripture reference here\./)).toBeInTheDocument();
    const readings = within(section).getByRole("link", { name: "Go to readings" });
    expect(readings).toHaveAttribute("href", "/builder/readings");
    expect(readings).toHaveClass("min-h-11"); // a 44 px touch target
    first.unmount();

    const { user, api } = renderStep(draftWith({ hymnal: "PH1990" }, { scriptures: LINES }), { "GET /hymnals": twoHymnals() });
    const ph = await openMatches(user);
    expect(within(ph).getByText("PH1990 has no scripture references, so it can't be searched by scripture.")).toBeInTheDocument();
    expect(api.requests.some((r) => r.path === "/hymns/scripture-matches")).toBe(false);
    expect(first.api.requests.some((r) => r.path === "/hymns/scripture-matches")).toBe(false);
  });

  it("shows Couldn't search the hymnal with Retry when the search fails", async () => {
    let fail = true;
    const { user } = renderStep(draftWith({}, { scriptures: LINES }), {
      "POST /hymns/scripture-matches": () => (fail ? fakeError(500, "internal_error", "Something went wrong.") : scriptureMatches()),
    });
    const section = await openMatches(user);
    expect(await within(section).findByText("Couldn't search the hymnal.")).toBeInTheDocument();
    fail = false;
    await user.click(within(section).getByRole("button", { name: "Retry" }));
    expect(await within(section).findByRole("heading", { name: "Matches the readings" })).toBeInTheDocument();
  });

  it("with Exclude on hides recently used matches behind Show them; shown, they carry their badge; Hide them hides them again", async () => {
    const [holy, , come] = gg2013();
    const recentMatches = scriptureMatches({
      items: [
        hymnMatch({ ...holy, recent_use_on: "2026-09-06" }, "passage", ["Isaiah 5:1-7"]),
        hymnMatch(come, "chapter", ["Isaiah 5:1-7"]),
        hymnMatch({ ...FAITHFUL, recent_use_on: "2026-10-18" }, "chapter", ["Matthew 21:33-46"]),
      ],
    });
    const { user } = renderStep(draftWith({}, { scriptures: LINES }), { "POST /hymns/scripture-matches": recentMatches });
    const section = await openMatches(user);
    expect(await within(section).findByText("2 recently used matches are hidden.")).toBeInTheDocument();
    expect(within(section).getAllByRole("listitem")).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Hymns for the readings 1" })).toBeInTheDocument();
    await user.click(within(section).getByRole("button", { name: "Show them" }));
    expect(within(section).getAllByRole("listitem")).toHaveLength(3);
    expect(within(section).getByText("Used Sep 6")).toBeInTheDocument();
    expect(within(section).getByText("Planned Oct 18")).toBeInTheDocument();
    expect(within(section).queryByText(/recently used matches are hidden/)).toBeNull();
    expect(within(section).getByText(/^2 recently used matches are shown\./)).toBeInTheDocument();
    await user.click(within(section).getByRole("button", { name: "Hide them" }));
    expect(within(section).getAllByRole("listitem")).toHaveLength(1);
    expect(within(section).getByText(/^2 recently used matches are hidden\./)).toBeInTheDocument();
    expect(within(section).getByRole("button", { name: "Show them" })).toBeInTheDocument();
  });
});

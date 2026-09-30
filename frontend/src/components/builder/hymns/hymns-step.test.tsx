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
import type { ChurchProfile } from "@/lib/api/types";
import { ChurchProvider } from "@/lib/church-context";
import { useDraft } from "@/lib/draft/context";
import { editOccasion } from "@/lib/draft/readings";
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
  lectionaryRoute,
  me,
  testDraft,
  USER_ID,
} from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { HymnsStep } from "./hymns-step";

const KEY = draftKey(USER_ID, church().id);
const [HOLY, PRAISE, COME, GRACE, , FAITHFUL] = gg2013();
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

  it("keeps the pickers when a background refetch fails after loading", async () => {
    let fail = false;
    const listRoute = hymnListRoute(undefined, RECENT);
    const failing = () => fakeError(500, "internal_error", "Something went wrong.");
    const { user, queryClient } = renderStep(draftWith(slots(pick(COME))), {
      "GET /hymnals": () => (fail ? failing() : hymnals()),
      "GET /hymns": (req: RecordedRequest) => (fail ? failing() : listRoute(req)),
    });
    const input = await readyPicker("Response");
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

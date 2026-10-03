/**
 * The Bulletin step (printed bulletin PR 2b; spec "The Bulletin step"; PR 2
 * planning answers 4-7). The step renders inside the builder layout; the
 * clock is fixed at Tuesday, September 29, 2026, so a fresh draft is dated
 * Sunday, October 4, 2026. Last week's bulletin (`GET
 * /services/previous-bulletin`) is empty unless a test says otherwise.
 */
import type { QueryClient } from "@tanstack/react-query";
import { screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import BulletinStepPage from "@/app/(signed-in)/(church)/builder/bulletin/page";
import { editScriptureLines } from "@/lib/draft/readings";
import { draftKey, type DraftV1 } from "@/lib/draft/schema";
import { makeQueryClient } from "@/lib/queries/client";
import { keys } from "@/lib/queries/keys";
import { fakeError, installFakeApi, type FakeHandler } from "@/test/fake-api";
import {
  church,
  churchProfile,
  DRAFT_NOW,
  filledBulletinSettings,
  lectionaryRoute,
  me,
  previousBulletin,
  serviceBulletin,
  testDraft,
  USER_ID,
} from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { FROM_LAST_WEEK } from "./bulletin-step";

const KEY = draftKey(USER_ID, church().id);

/** Last week's service (invented): the prelude, the ushers and the coffee hour. */
const LAST_WEEK = previousBulletin({
  service_id: "s-last",
  service_date_iso: "2026-09-27",
  bulletin: serviceBulletin({
    prelude: { title: "Morning Voluntary", composer: "Pat Example" },
    announcements: { ...serviceBulletin().announcements, ushers: "Sam Sample", coffee_hour: "The Example family" },
  }),
});

function stored(): DraftV1 {
  return JSON.parse(window.localStorage.getItem(KEY) ?? "null") as DraftV1;
}

function renderStep(
  draft: DraftV1 = testDraft(),
  routes: Record<string, FakeHandler> = {},
  queryClient: QueryClient = makeQueryClient({ queries: { retry: false } }),
) {
  window.localStorage.setItem(KEY, JSON.stringify(draft));
  const api = installFakeApi({
    "GET /church": churchProfile(),
    "GET /lectionary/readings": lectionaryRoute(),
    "GET /church/bulletin-settings": filledBulletinSettings(),
    "GET /services/previous-bulletin": previousBulletin(),
    ...routes,
  });
  const view = renderWithProviders(
    <BuilderLayout>
      <BulletinStepPage />
    </BuilderLayout>,
    { me: me(), church: church(), path: "/builder/bulletin", queryClient },
  );
  return { ...view, api };
}

function carryRequests(api: { requests: { path: string }[] }) {
  return api.requests.filter((r) => r.path.startsWith("/services/previous-bulletin"));
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("the Bulletin step (printed bulletin PR 2b)", () => {
  it("shows the music, who leads, the announcements and the reading text, all optional, and stores what is typed", async () => {
    const { user } = renderStep();
    const step = await screen.findByRole("region", { name: "Bulletin" });
    expect(within(step).getByText(/^Optional\. What this week's printed bulletin adds/)).toBeInTheDocument();
    expect(within(step).getAllByRole("group").map((g) => g.querySelector("legend")?.textContent)).toEqual([
      "Music",
      "Who leads",
      "Announcements",
      "Reading text",
    ]);
    for (const name of ["Prelude title", "Prelude composer", "Postlude title", "Postlude composer", "Ushers and counters",
      "Deacon of the week", "Coffee hour"]) {
      expect(within(step).getByRole("textbox", { name })).toHaveClass("h-11"); // 44 px on a phone
    }
    expect(within(step).getByRole("textbox", { name: "Prayers and concerns" }).tagName).toBe("TEXTAREA");
    expect(within(step).getByText("Choose the readings on step 1 to paste their text.")).toBeInTheDocument();
    expect(within(step).getByRole("link", { name: "Bulletin settings" })).toHaveAttribute("href", "/bulletin-settings");

    await user.type(within(step).getByRole("textbox", { name: "Postlude title" }), "Festive Postlude");
    await user.type(within(step).getByRole("textbox", { name: "Other announcements" }), "The office is closed.");
    await waitFor(() => expect(stored().bulletin.announcements.other).toBe("The office is closed."));
    expect(stored().bulletin.postlude.title).toBe("Festive Postlude");
  });

  it("carries last week's music and announcements into a new draft, each marked until it is edited or kept", async () => {
    const { user, api } = renderStep(testDraft(), { "GET /services/previous-bulletin": LAST_WEEK });
    const step = await screen.findByRole("region", { name: "Bulletin" });
    const coffee = within(step).getByRole("textbox", { name: "Coffee hour" });
    await waitFor(() => expect(coffee).toHaveValue("The Example family"));
    expect(carryRequests(api).map((r) => r.path)).toEqual(["/services/previous-bulletin?before=2026-10-04"]);
    expect(within(step).getByRole("textbox", { name: "Prelude title" })).toHaveValue("Morning Voluntary");
    expect(within(step).getAllByText(FROM_LAST_WEEK)).toHaveLength(3);
    expect(coffee).toHaveAccessibleDescription(FROM_LAST_WEEK);

    await user.clear(coffee);
    await user.type(coffee, "The Sample family");
    const keep = within(step).getByRole("button", { name: "Keep as is: ushers and counters" }); // its visible words first (M3)
    expect(keep).toHaveTextContent("Keep as is");
    await user.click(keep);
    // The button goes; focus stays on the box it kept (2b-2 build review M2).
    expect(within(step).getByRole("textbox", { name: "Ushers and counters" })).toHaveFocus();
    expect(within(step).getAllByText(FROM_LAST_WEEK)).toHaveLength(1); // the prelude's, still to check
    await waitFor(() => expect(stored().bulletin.carried).toEqual(["prelude"]));
    expect(stored().bulletin.announcements).toMatchObject({ ushers: "Sam Sample", coffee_hour: "The Sample family" });
    expect(screen.getAllByRole("link").find((a) => a.getAttribute("href") === "/builder/bulletin")).toHaveTextContent(
      "4 Bulletin 1 to check",
    );
  });

  it("never carries into a saved service, and says so with Try again when last week's cannot be loaded", async () => {
    const saved = testDraft((d) => ({ ...d, editing: { service_id: "s1", saved_at: "2026-10-01T14:42:00+00:00", date_iso: "2026-10-04" } }));
    const first = renderStep(saved, { "GET /services/previous-bulletin": LAST_WEEK });
    await screen.findByRole("region", { name: "Bulletin" });
    expect(screen.getByRole("textbox", { name: "Coffee hour" })).toHaveValue("");
    expect(carryRequests(first.api)).toEqual([]);
    first.unmount();

    let fail = true;
    const { user, api } = renderStep(testDraft(), {
      "GET /services/previous-bulletin": () => (fail ? fakeError(503, "unavailable", "Try again later.") : LAST_WEEK),
    });
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Last week's announcements could not be loaded.");
    // Typing in one box keeps the message and Try again; the other boxes still carry (plan review fix M1).
    await user.type(screen.getByRole("textbox", { name: "Other announcements" }), "Typed first.");
    expect(screen.getByRole("alert")).toBe(alert);
    // A retry that fails again keeps the alert and focus on Try again (2b-2 build review M2).
    const again = within(alert).getByRole("button", { name: "Try again" });
    const requests = carryRequests(api).length;
    await user.click(again);
    await waitFor(() => expect(carryRequests(api).length).toBeGreaterThan(requests));
    await waitFor(() => expect(screen.getByRole("alert")).toBe(alert));
    expect(again).toHaveFocus();
    fail = false;
    await user.click(again);
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Coffee hour" })).toHaveValue("The Example family"));
    expect(screen.getByRole("textbox", { name: "Other announcements" })).toHaveValue("Typed first.");
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.getByRole("heading", { name: "Bulletin" })).toHaveFocus(); // not the page
  });

  it("never carries a cached answer from before it opened: a fix saved to last week's service carries (2b-2 build review I1)", async () => {
    const old = previousBulletin({
      ...LAST_WEEK,
      bulletin: { ...LAST_WEEK.bulletin, announcements: { ...LAST_WEEK.bulletin.announcements, coffee_hour: "Old coffee hour" } },
    });
    for (const invalidated of [true, false]) {
      // Cached on an earlier visit; then last week's service was saved again (here, or within 30 s on another device).
      const queryClient = makeQueryClient({ queries: { retry: false } });
      queryClient.setQueryData(keys.previousBulletin(church().id, "2026-10-04"), old);
      if (invalidated) await queryClient.invalidateQueries({ queryKey: ["church", church().id, "services"] });
      const view = renderStep(testDraft(), { "GET /services/previous-bulletin": LAST_WEEK }, queryClient);
      const coffee = await screen.findByRole("textbox", { name: "Coffee hour" });
      await waitFor(() => expect(stored().bulletin.carried_for).toBe("2026-10-04"));
      expect(coffee).toHaveValue("The Example family");
      expect(stored().bulletin.announcements.coffee_hour).toBe("The Example family");
      expect(carryRequests(view.api)).toHaveLength(1);
      view.unmount();
      window.localStorage.clear();
    }
  });

  it("shows the three people from the bulletin settings, changeable for this week, and a part's leader behind a button", async () => {
    const { user } = renderStep();
    const group = await screen.findByRole("group", { name: "Who leads" });
    const organist = await within(group).findByRole("textbox", { name: "Organist" });
    expect(organist).toHaveValue("Jordan Doe");
    expect(within(group).getByRole("textbox", { name: "Worship leader" })).toHaveValue("Rev. Alex Example");
    await user.clear(organist);
    await user.type(organist, "Lee Sample");
    expect(within(group).getByText("Changed for this week.")).toBeInTheDocument();
    await waitFor(() => expect(stored().bulletin.people.organist).toBe("Lee Sample"));
    await user.click(within(group).getByRole("button", { name: "Undo the change to Organist" }));
    expect(organist).toHaveValue("Jordan Doe");
    expect(organist).toHaveFocus(); // the button went with the change (2b-2 build review M2)
    await waitFor(() => expect(stored().bulletin.people.organist).toBeNull());

    // A guest this week: the parts still say who usually leads them (plan review fix M6).
    const leader = within(group).getByRole("textbox", { name: "Worship leader" });
    await user.clear(leader);
    await user.type(leader, "Rev. Guest");
    const toggle = within(group).getByRole("button", { name: "Change who leads a part" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(toggle).not.toHaveAttribute("aria-controls"); // nothing to point at while closed (plan review fix M7)
    expect(within(group).queryByRole("textbox", { name: "Sermon" })).toBeNull();
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(document.getElementById(toggle.getAttribute("aria-controls") ?? "")).not.toBeNull();
    const sermon = within(group).getByRole("textbox", { name: "Sermon" });
    expect(sermon).toHaveAccessibleDescription("Usually Rev. Alex Example");
    expect(within(group).getByRole("textbox", { name: "Offering" })).toHaveAccessibleDescription("Usually no one");
    await user.type(sermon, "Rev. Guest");
    await waitFor(() => expect(stored().bulletin.leaders).toEqual({ sermon: "Rev. Guest" }));
  });

  it("says so with Try again when the bulletin settings cannot be loaded, and shows no field for who leads", async () => {
    let fail = true;
    const { user } = renderStep(testDraft(), {
      "GET /church/bulletin-settings": () => (fail ? fakeError(503, "unavailable", "Try again later.") : filledBulletinSettings()),
    });
    const group = await screen.findByRole("group", { name: "Who leads" });
    const alert = await within(group).findByRole("alert");
    expect(alert).toHaveTextContent("Bulletin settings could not be loaded.");
    expect(within(group).queryByRole("textbox")).toBeNull();
    const again = within(alert).getByRole("button", { name: "Try again" });
    await user.click(again); // fails again: the alert and focus stay (2b-2 build review M2)
    await waitFor(() => expect(within(group).getByRole("alert")).toBe(alert));
    expect(again).toHaveFocus();
    fail = false;
    await user.click(again);
    expect(await within(group).findByRole("textbox", { name: "Organist" })).toHaveValue("Jordan Doe");
    expect(within(group).getByRole("textbox", { name: "Worship leader" })).toHaveFocus();
  });

  it("marks a saved service's music and announcements to check on another date, and starts this week's people empty", async () => {
    const saved = testDraft((d) => ({
      ...d,
      editing: { service_id: "s1", saved_at: "2026-09-27T12:00:00+00:00", date_iso: "2026-09-27" },
      bulletin: {
        ...d.bulletin,
        prelude: { title: "Morning Voluntary", composer: "" },
        people: { worship_leader: "Rev. Guest", liturgist: null, organist: null },
        announcements: { ...d.bulletin.announcements, coffee_hour: "The Example family" },
      },
    }));
    const { api } = renderStep(saved);
    const step = await screen.findByRole("region", { name: "Bulletin" });
    await waitFor(() => expect(within(step).getAllByText(FROM_LAST_WEEK)).toHaveLength(2));
    expect(within(step).getByRole("textbox", { name: "Coffee hour" })).toHaveAccessibleDescription(FROM_LAST_WEEK);
    expect(await within(step).findByRole("textbox", { name: "Worship leader" })).toHaveValue("Rev. Alex Example");
    await waitFor(() => expect(stored().bulletin.set_aside?.people.worship_leader).toBe("Rev. Guest"));
    expect(carryRequests(api)).toEqual([]); // a saved service never looks up last week's
  });

  it("has a box per reading the files print, and keeps the pasted text under that reading", async () => {
    const draft = editScriptureLines(testDraft(), "Isaiah 5:1-7\nPsalm 80:7-15\nPhilippians 3:4b-14\nMatthew 21:33-46");
    const { user } = renderStep(draft);
    const group = await screen.findByRole("group", { name: "Reading text" });
    expect(within(group).getAllByRole("textbox")).toHaveLength(2);
    const nt = within(group).getByRole("textbox", { name: "New Testament Reading: Philippians 3:4b-14" });
    expect(within(group).getByRole("textbox", { name: "First Reading: Isaiah 5:1-7" })).toHaveValue("");
    await user.type(nt, "Pasted text.");
    await waitFor(() => expect(stored().bulletin.pasted).toEqual({ "Philippians 3:4b-14": "Pasted text." }));
  });
});

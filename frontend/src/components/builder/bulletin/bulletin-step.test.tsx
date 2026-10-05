/**
 * The Bulletin step (printed bulletin PR 2b; spec "The Bulletin step"; PR 2
 * planning answers 4-7). The step renders inside the builder layout; the
 * clock is fixed at Tuesday, September 29, 2026, so a fresh draft is dated
 * Sunday, October 4, 2026. Last week's bulletin (`GET
 * /services/previous-bulletin`) is empty unless a test says otherwise.
 */
import type { QueryClient } from "@tanstack/react-query";
import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { StrictMode } from "react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import BulletinStepPage from "@/app/(signed-in)/(church)/builder/bulletin/page";
import { formatServiceDate } from "@/lib/dates";
import { setCover } from "@/lib/draft/bulletin";
import { useDraft } from "@/lib/draft/context";
import { editOccasion, editScriptureLines, setDate } from "@/lib/draft/readings";
import { draftKey, freshDraft, type DraftV1 } from "@/lib/draft/schema";
import { makeQueryClient } from "@/lib/queries/client";
import { keys } from "@/lib/queries/keys";
import { fakeError, installFakeApi, type FakeHandler } from "@/test/fake-api";
import {
  bulletinImage,
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

import { FROM_LAST_WEEK, PICTURE_ALT, PICTURE_OTHER_SERVICE, PICTURE_OTHER_WEEK, PICTURE_SMALL } from "./bulletin-step";

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

/** Changes the draft's date as step 1 would. */
function DateProbe() {
  const { update } = useDraft();
  return (
    <button type="button" onClick={() => update((d) => setDate(d, "2026-10-11"))}>
      Probe date
    </button>
  );
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
      "Cover picture",
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


describe("the cover picture (printed bulletin PR 3b; PR 3 planning answers 5-8)", () => {
  const PICTURE = bulletinImage().id;
  const OTHER_PICTURE = "0b4c2b0e-7777-4888-9999-aaaabbbbcccc";
  const jpeg = () => new File([new Uint8Array([0xff, 0xd8, 0xff])], "church.jpg", { type: "image/jpeg" });
  const pictureRoute = () => new Response(new Blob([new Uint8Array([0xff, 0xd8])], { type: "image/jpeg" }), { headers: { "Content-Type": "image/jpeg" } });

  beforeEach(() => {
    let n = 0;
    Object.assign(URL, { createObjectURL: vi.fn(() => `blob:test/${(n += 1)}`), revokeObjectURL: vi.fn() }); // jsdom has neither
  });

  it("uploads a chosen picture, shows it trimmed as the front page prints it, and Remove takes it off", async () => {
    const readings = editScriptureLines(testDraft(), "Isaiah 5:1-7\nPsalm 80:7-15\nPhilippians 3:4b-14\nMatthew 21:33-46");
    const { user, api } = renderStep(readings, {
      "POST /bulletin-images": () => ({ status: 201, body: bulletinImage() }),
      [`GET /bulletin-images/${PICTURE}`]: pictureRoute,
    });
    const group = await screen.findByRole("group", { name: "Cover picture" });
    expect(within(group).getByText(/^A JPEG or PNG picture for the front page/)).toBeInTheDocument();
    const choose = within(group).getByRole("button", { name: "Choose a picture" });
    expect(choose).toHaveClass("h-11"); // 44 px on a phone
    expect(within(group).queryByRole("button", { name: "Remove the cover picture" })).toBeNull();
    const file = jpeg();
    await user.upload(document.getElementById("bulletin-cover-file") as HTMLInputElement, file);
    const shown = await within(group).findByRole("img", { name: PICTURE_ALT });
    expect(shown).toHaveAttribute("src", "blob:test/1");
    expect(shown).toHaveClass("object-cover", "aspect-[372/300]");
    // The band as it prints over the picture: the New Testament reading the files print (here the epistle) and the date.
    expect(screen.getByTestId("cover-band")).toHaveTextContent(`Philippians 3:4b-14${formatServiceDate(readings.readings.date_iso)}`);
    const [post] = api.requests.filter((r) => r.method === "POST");
    expect(post).toMatchObject({ path: "/bulletin-images", body: file });
    expect(post.headers["content-type"]).toBe("image/jpeg");
    await waitFor(() => expect(stored().bulletin).toMatchObject({ cover_image_id: PICTURE, edited: ["cover"] }));
    expect(within(group).getByRole("button", { name: "Choose another picture" })).toBeInTheDocument();

    await user.click(within(group).getByRole("button", { name: "Remove the cover picture" }));
    await waitFor(() => expect(stored().bulletin.cover_image_id).toBeNull());
    expect(within(group).queryByRole("img")).toBeNull();
    expect(within(group).getByRole("button", { name: "Choose a picture" })).toHaveFocus();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:test/1");
  });

  it("says a file the server would refuse before uploading it, and the server's own refusal after", async () => {
    const { api } = renderStep(testDraft(), {
      "POST /bulletin-images": () =>
        fakeError(422, "invalid_request", "The picture has too many pixels. Choose a smaller one.", {
          fields: { image: "The picture has too many pixels. Choose a smaller one." },
        }),
    });
    const group = await screen.findByRole("group", { name: "Cover picture" });
    const input = document.getElementById("bulletin-cover-file") as HTMLInputElement;
    expect(input).toHaveAttribute("accept", "image/jpeg,image/png,.jpg,.jpeg,.png");
    fireEvent.change(input, { target: { files: [new File(["x"], "photo.heic", { type: "image/heic" })] } });
    expect(await within(group).findByRole("alert")).toHaveTextContent("Choose a JPEG or PNG picture.");
    expect(api.requests.filter((r) => r.method === "POST")).toEqual([]);
    fireEvent.change(input, { target: { files: [jpeg()] } });
    await waitFor(() =>
      expect(within(group).getByRole("alert")).toHaveTextContent("The picture has too many pixels. Choose a smaller one."),
    );
    expect(stored().bulletin.cover_image_id).toBeNull();
  });

  it("uploads a JPEG whose type the phone left blank, as bytes the server reads (PR 3b build review M7)", async () => {
    const { api } = renderStep(testDraft(), {
      "POST /bulletin-images": () => ({ status: 201, body: bulletinImage() }),
      [`GET /bulletin-images/${PICTURE}`]: pictureRoute,
    });
    await screen.findByRole("group", { name: "Cover picture" });
    const blank = new File([new Uint8Array([0xff, 0xd8, 0xff])], "IMG_0001.JPG", { type: "" });
    fireEvent.change(document.getElementById("bulletin-cover-file") as HTMLInputElement, { target: { files: [blank] } });
    await waitFor(() => expect(stored().bulletin.cover_image_id).toBe(PICTURE));
    const [post] = api.requests.filter((r) => r.method === "POST");
    expect(post.headers["content-type"]).toBe("application/octet-stream");
  });

  it("carries last week's picture with its note until it is kept, and says when a picture cannot be loaded", async () => {
    const lastWeek = previousBulletin({ service_id: "s-last", service_date_iso: "2026-09-27", bulletin: serviceBulletin({ cover_image_id: PICTURE }) });
    const { user } = renderStep(testDraft(), {
      "GET /services/previous-bulletin": lastWeek,
      [`GET /bulletin-images/${PICTURE}`]: pictureRoute,
    });
    const group = await screen.findByRole("group", { name: "Cover picture" });
    expect(await within(group).findByRole("img", { name: PICTURE_ALT })).toBeInTheDocument();
    expect(within(group).getByText(FROM_LAST_WEEK)).toBeInTheDocument();
    expect(within(group).getByRole("button", { name: "Choose another picture" })).toHaveAccessibleDescription(FROM_LAST_WEEK);
    await user.click(within(group).getByRole("button", { name: "Keep as is: cover picture" }));
    expect(within(group).queryByText(FROM_LAST_WEEK)).toBeNull();
    expect(within(group).getByRole("button", { name: "Choose another picture" })).toHaveFocus();
    await waitFor(() => expect(stored().bulletin).toMatchObject({ cover_image_id: PICTURE, carried: [], edited: ["cover"] }));
  });

  it("says when the picture can no longer be loaded, and Remove still works", async () => {
    const gone = setCover(testDraft(), PICTURE); // chosen on an earlier visit
    const { user } = renderStep(gone, {
      [`GET /bulletin-images/${PICTURE}`]: () => fakeError(404, "not_found", "That picture is no longer available."),
    });
    const group = await screen.findByRole("group", { name: "Cover picture" });
    expect(await within(group).findByText("The picture could not be loaded.")).toBeInTheDocument();
    await user.click(within(group).getByRole("button", { name: "Remove the cover picture" }));
    await waitFor(() => expect(stored().bulletin.cover_image_id).toBeNull());
  });
  it("offers Try again beside Remove when the picture could not be loaded, and focus goes on to Choose once it shows (PR 3b build review M6)", async () => {
    let loads = 0;
    const { user } = renderStep(setCover(testDraft(), PICTURE), {
      [`GET /bulletin-images/${PICTURE}`]: () => {
        if ((loads += 1) === 1) throw new TypeError("Failed to fetch"); // a dropped connection
        return pictureRoute();
      },
    });
    const group = await screen.findByRole("group", { name: "Cover picture" });
    expect(await within(group).findByText("The picture could not be loaded.")).toBeInTheDocument();
    const retry = within(group).getByRole("button", { name: "Try again: cover picture" });
    expect(within(group).getByRole("button", { name: "Remove the cover picture" })).toBeEnabled();
    await user.click(retry);
    expect(await within(group).findByRole("img", { name: PICTURE_ALT })).toBeInTheDocument();
    expect(loads).toBe(2);
    expect(within(group).queryByRole("button", { name: "Try again: cover picture" })).toBeNull();
    await waitFor(() => expect(within(group).getByRole("button", { name: "Choose another picture" })).toHaveFocus());
  });

  it("keeps the picture when the step is left while it uploads (plan review I1)", async () => {
    let answer: (value: unknown) => void = () => {};
    const view = renderStep(testDraft(), {
      "POST /bulletin-images": () => new Promise((resolve) => (answer = resolve)),
      [`GET /bulletin-images/${PICTURE}`]: pictureRoute,
    });
    await screen.findByRole("group", { name: "Cover picture" });
    fireEvent.change(document.getElementById("bulletin-cover-file") as HTMLInputElement, { target: { files: [jpeg()] } });
    expect(await screen.findByRole("button", { name: "Uploading…" })).toBeInTheDocument();
    view.rerender(
      <BuilderLayout>
        <p>Another step</p>
      </BuilderLayout>,
    );
    expect(screen.queryByRole("group", { name: "Cover picture" })).toBeNull();
    await act(async () => answer({ status: 201, body: bulletinImage() }));
    await waitFor(() => expect(stored().bulletin).toMatchObject({ cover_image_id: PICTURE, edited: ["cover"] }));
  });

  it("never writes the draft it had over a newer one when the upload lands after the builder was left (PR 3b build review C1)", async () => {
    const info = vi.spyOn(toast, "info");
    let answer: (value: unknown) => void = () => {};
    const view = renderStep(editOccasion(testDraft(), "Old week"), {
      "POST /bulletin-images": () => new Promise((resolve) => (answer = resolve)),
    });
    await screen.findByRole("group", { name: "Cover picture" });
    fireEvent.change(document.getElementById("bulletin-cover-file") as HTMLInputElement, { target: { files: [jpeg()] } });
    expect(await screen.findByRole("button", { name: "Uploading…" })).toBeInTheDocument();
    view.rerender(<p>Services</p>); // the builder unmounts (its provider flushes)
    // Services: New service, then typing in it (another provider in this tab wrote it).
    vi.setSystemTime(new Date(DRAFT_NOW.getTime() + 5_000));
    const newer = editOccasion(freshDraft({ church: churchProfile(), user: { id: USER_ID }, now: new Date() }), "New week typing");
    window.localStorage.setItem(KEY, JSON.stringify(newer));
    vi.setSystemTime(new Date(DRAFT_NOW.getTime() + 10_000));
    await act(async () => answer({ status: 201, body: bulletinImage() }));
    await act(async () => {});
    expect(stored()).toEqual(newer);
    expect(info).toHaveBeenCalledWith(PICTURE_OTHER_SERVICE, expect.anything()); // build review M5
  });

  it("still says Uploading… when the step is left and opened again, with Choose and Remove waiting (PR 3b build review I1)", async () => {
    let answer: (value: unknown) => void = () => {};
    const view = renderStep(setCover(testDraft(), PICTURE), {
      "POST /bulletin-images": () => new Promise((resolve) => (answer = resolve)),
      [`GET /bulletin-images/${PICTURE}`]: pictureRoute,
      [`GET /bulletin-images/${OTHER_PICTURE}`]: pictureRoute,
    });
    await screen.findByRole("img", { name: PICTURE_ALT });
    fireEvent.change(document.getElementById("bulletin-cover-file") as HTMLInputElement, { target: { files: [jpeg()] } });
    expect(await screen.findByRole("button", { name: "Uploading…" })).toBeInTheDocument();
    view.rerender(
      <BuilderLayout>
        <p>Another step</p>
      </BuilderLayout>,
    );
    view.rerender(
      <BuilderLayout>
        <BulletinStepPage />
      </BuilderLayout>,
    );
    const group = await screen.findByRole("group", { name: "Cover picture" });
    expect(within(group).getByRole("button", { name: "Uploading…" })).toHaveAttribute("aria-disabled", "true");
    expect(within(group).getByRole("button", { name: "Remove the cover picture" })).toBeDisabled();
    expect(within(group).getByRole("status", { name: "" })).toHaveTextContent("Uploading the picture…");

    await act(async () => answer({ status: 201, body: bulletinImage({ id: OTHER_PICTURE }) }));
    await waitFor(() => expect(stored().bulletin.cover_image_id).toBe(OTHER_PICTURE));
    expect(within(group).getByRole("button", { name: "Choose another picture" })).toBeEnabled();
    expect(within(group).getByRole("button", { name: "Remove the cover picture" })).toBeEnabled();
  });

  it("applies only the latest choice: an earlier upload that answers last never replaces it (PR 3b build review I1)", async () => {
    const answers: ((value: unknown) => void)[] = [];
    renderStep(testDraft(), {
      "POST /bulletin-images": () => new Promise((resolve) => answers.push(resolve)),
      [`GET /bulletin-images/${PICTURE}`]: pictureRoute,
      [`GET /bulletin-images/${OTHER_PICTURE}`]: pictureRoute,
    });
    await screen.findByRole("group", { name: "Cover picture" });
    const input = document.getElementById("bulletin-cover-file") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [jpeg()] } }); // A
    await waitFor(() => expect(answers).toHaveLength(1));
    fireEvent.change(input, { target: { files: [jpeg()] } }); // B, chosen later
    await waitFor(() => expect(answers).toHaveLength(2));
    await act(async () => answers[1]({ status: 201, body: bulletinImage({ id: OTHER_PICTURE }) }));
    await waitFor(() => expect(stored().bulletin.cover_image_id).toBe(OTHER_PICTURE));
    await act(async () => answers[0]({ status: 201, body: bulletinImage() }));
    await act(async () => {});
    expect(stored().bulletin.cover_image_id).toBe(OTHER_PICTURE);
    expect(await screen.findByRole("button", { name: "Choose another picture" })).toBeEnabled();
  });

  it("says so when an upload answers after the date changed, and leaves the picture out (PR 3b build review M5)", async () => {
    const info = vi.spyOn(toast, "info");
    let answer: (value: unknown) => void = () => {};
    const view = renderStep(testDraft(), {
      "POST /bulletin-images": () => new Promise((resolve) => (answer = resolve)),
    });
    await screen.findByRole("group", { name: "Cover picture" });
    fireEvent.change(document.getElementById("bulletin-cover-file") as HTMLInputElement, { target: { files: [jpeg()] } });
    expect(await screen.findByRole("button", { name: "Uploading…" })).toBeInTheDocument();
    view.rerender(
      <BuilderLayout>
        <DateProbe />
      </BuilderLayout>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Probe date" }));
    await waitFor(() => expect(stored().readings.date_iso).toBe("2026-10-11"));
    await act(async () => answer({ status: 201, body: bulletinImage() }));
    await waitFor(() => expect(info).toHaveBeenCalledWith(PICTURE_OTHER_WEEK, expect.anything()));
    expect(stored().bulletin.cover_image_id).toBeNull();
  });

  it("says an upload's failure in a toast when the step was left meanwhile (PR 3b build review M5)", async () => {
    const error = vi.spyOn(toast, "error");
    let answer: (value: unknown) => void = () => {};
    const view = renderStep(testDraft(), {
      "POST /bulletin-images": () => new Promise((resolve) => (answer = resolve)),
    });
    await screen.findByRole("group", { name: "Cover picture" });
    fireEvent.change(document.getElementById("bulletin-cover-file") as HTMLInputElement, { target: { files: [jpeg()] } });
    expect(await screen.findByRole("button", { name: "Uploading…" })).toBeInTheDocument();
    view.rerender(
      <BuilderLayout>
        <p>Another step</p>
      </BuilderLayout>,
    );
    await act(async () => answer(fakeError(422, "invalid_request", "The picture has too many pixels. Choose a smaller one.")));
    await waitFor(() => expect(error).toHaveBeenCalledWith("The picture has too many pixels. Choose a smaller one."));
    expect(stored().bulletin.cover_image_id).toBeNull();
  });

  it("never shows a preview whose URL was released, under StrictMode (plan review I2)", async () => {
    window.localStorage.setItem(KEY, JSON.stringify(setCover(testDraft(), PICTURE)));
    installFakeApi({
      "GET /church": churchProfile(),
      "GET /lectionary/readings": lectionaryRoute(),
      "GET /church/bulletin-settings": filledBulletinSettings(),
      "GET /services/previous-bulletin": previousBulletin(),
      [`GET /bulletin-images/${PICTURE}`]: pictureRoute,
    });
    renderWithProviders(
      <StrictMode>
        <BuilderLayout>
          <BulletinStepPage />
        </BuilderLayout>
      </StrictMode>,
      { me: me(), church: church(), path: "/builder/bulletin" },
    );
    const shown = await screen.findByRole("img", { name: PICTURE_ALT });
    const released = vi.mocked(URL.revokeObjectURL).mock.calls.map(([url]) => url);
    expect(released).not.toContain(shown.getAttribute("src"));
    expect(vi.mocked(URL.createObjectURL).mock.calls.length - released.length).toBe(1); // only the one shown is held
  });

  it("says a small picture may print blurry", async () => {
    renderStep(setCover(testDraft(), PICTURE), { [`GET /bulletin-images/${PICTURE}`]: pictureRoute });
    const shown = await screen.findByRole("img", { name: PICTURE_ALT });
    expect(screen.queryByText(PICTURE_SMALL)).toBeNull();
    Object.defineProperties(shown, { naturalWidth: { value: 640, configurable: true }, naturalHeight: { value: 480, configurable: true } });
    fireEvent.load(shown);
    expect(await screen.findByText(PICTURE_SMALL)).toBeInTheDocument();
    Object.defineProperties(shown, { naturalWidth: { value: 1600, configurable: true }, naturalHeight: { value: 1200, configurable: true } });
    fireEvent.load(shown);
    await waitFor(() => expect(screen.queryByText(PICTURE_SMALL)).toBeNull());
  });
});

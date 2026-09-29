/**
 * The Date & readings step (S UX "Step 1", Testing `readings-step.test.tsx`;
 * AC14-AC16). The step renders inside the real builder layout against the fake
 * API. Only `Date` is faked (Tuesday, September 29, 2026 at noon in New York),
 * so a fresh draft is dated Sunday, October 4, and the 400 ms lookup delay and
 * the draft's writes run on real timers.
 */
import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import { useLectionaryLookup } from "@/components/builder/lectionary-sync";
import { useDraft } from "@/lib/draft/context";
import { applyReadingSet, editOccasion, setDate, setPick } from "@/lib/draft/readings";
import { draftKey, type DraftV1 } from "@/lib/draft/schema";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import {
  church,
  churchProfile,
  DRAFT_NOW,
  lectionary,
  lectionaryRoute,
  me,
  noReadings,
  testDraft,
  translations,
  USER_ID,
} from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { occasionCaption } from "./occasion-field";
import { ReadingsStep } from "./readings-step";
const KEY = draftKey(USER_ID, church().id);
const ISAIAH = ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"];

/** The draft's picks and origins, and the date the lookup has settled on, which the step does not print. */
function DraftProbe() {
  const { draft } = useDraft();
  const { lookupDate } = useLectionaryLookup();
  const r = draft.readings;
  return (
    <>
      <p data-testid="probe">
        {r.date_origin}/{r.fields_origin}/ot={r.selected_ot_ref || "auto"}/nt={r.selected_nt_ref || "auto"}/t=
        {r.translation ?? "church"}
      </p>
      <p data-testid="lookup-date">{lookupDate}</p>
    </>
  );
}

type Routes = { lookup?: FakeHandler; translations?: FakeHandler; passages?: FakeHandler };

function renderStep(
  { lookup = lectionaryRoute(), translations: list = translations(), passages }: Routes = {},
  seed?: DraftV1,
) {
  if (seed) window.localStorage.setItem(KEY, JSON.stringify(seed));
  const handlers: Record<string, FakeHandler> = {
    "GET /church": churchProfile(),
    "GET /lectionary/readings": lookup,
    "GET /translations": list,
  };
  if (passages !== undefined) handlers["POST /scripture/passages"] = passages;
  const api = installFakeApi(handlers);
  const view = renderWithProviders(
    <BuilderLayout>
      <ReadingsStep />
      <DraftProbe />
    </BuilderLayout>,
    { me: me(), church: church(), path: "/builder/readings" },
  );
  const lookups = () => api.requests.filter((r) => r.path.startsWith("/lectionary/")).map((r) => r.path);
  return { ...view, api, lookups };
}

/** Queries inside the step, away from the summary (which also shows the date and readings). */
function step() {
  return within(screen.getByRole("region", { name: "Date & readings" }));
}

function probe(): string {
  return screen.getByTestId("probe").textContent ?? "";
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("service date (S UX item 1)", () => {
  it("shows next Sunday; a weekday says it looks for that day's readings; Use next Sunday puts the default back", async () => {
    const { lookups } = renderStep();
    const input = await screen.findByLabelText("Service date");
    expect(input).toHaveValue("2026-10-04");
    expect(step().getByText("Sunday, October 4, 2026")).toBeInTheDocument();
    expect(screen.getByText("Readings and the occasion load automatically for this date.")).toBeInTheDocument();
    expect(screen.queryByText(/^Not a Sunday\./)).toBeNull();
    expect(screen.queryByRole("button", { name: /^Use next Sunday/ })).toBeNull();

    fireEvent.change(input, { target: { value: "2026-09-27" } });
    expect(step().getByText("Sunday, September 27, 2026")).toBeInTheDocument();
    expect(screen.getByText("This date has passed.")).toBeInTheDocument();
    expect(probe()).toMatch(/^user\//);

    fireEvent.change(input, { target: { value: "2026-09-29" } });
    expect(step().getByText("Tuesday, September 29, 2026")).toBeInTheDocument();
    expect(screen.queryByText("This date has passed.")).toBeNull(); // today is not past
    expect(
      screen.getByText(
        "Not a Sunday. We'll look for this day's own readings, such as Ash Wednesday, Christmas Eve or Good Friday.",
      ),
    ).toBeInTheDocument();

    screen.getByRole("button", { name: "Use next Sunday (October 4)" }).click();
    await waitFor(() => expect(input).toHaveValue("2026-10-04"));
    expect(probe()).toMatch(/^default\//);
    await waitFor(() => expect(lookups()).toContain("/lectionary/readings?date=2026-10-04"));
  });

  it("asks for a date when it is empty, and looks nothing up for it or for a year outside 1900-2199", async () => {
    const { lookups } = renderStep();
    const input = await screen.findByLabelText("Service date");
    await waitFor(() => expect(lookups()).toEqual(["/lectionary/readings?date=2026-10-04"]));

    fireEvent.change(input, { target: { value: "" } });
    expect(screen.getByText("Choose a service date.")).toBeInTheDocument();
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("button", { name: "Use next Sunday (October 4)" })).toBeInTheDocument();

    // A fifth year digit stays on screen and is stored as no date (owner answer F).
    fireEvent.change(input, { target: { value: "20261-10-04" } });
    expect(input).toHaveValue("20261-10-04");
    expect(screen.getByText("Choose a service date.")).toBeInTheDocument();

    fireEvent.change(input, { target: { value: "1850-06-02" } });
    expect(step().getByText("Sunday, June 2, 1850")).toBeInTheDocument();
    expect(screen.queryByText("Enter a date between 1900 and 2199.")).toBeNull(); // not while it may still be typed
    // The lookup settles on 1850 and sends nothing; the next date's lookup is the next request.
    await waitFor(() => expect(screen.getByTestId("lookup-date")).toHaveTextContent("1850-06-02"));
    expect(screen.getByText("Enter a date between 1900 and 2199.")).toBeInTheDocument();
    expect(input).toHaveAttribute("aria-invalid", "true");
    fireEvent.change(input, { target: { value: "2026-10-11" } });
    await waitFor(() =>
      expect(lookups()).toEqual(["/lectionary/readings?date=2026-10-04", "/lectionary/readings?date=2026-10-11"]),
    );
  });
});

describe("occasion and scripture lines (S UX items 4 and 5)", () => {
  it("captions the occasion by where it came from", async () => {
    const { user } = renderStep({ lookup: lectionaryRoute(lectionary) });
    const occasion = await screen.findByLabelText("Occasion");
    await waitFor(() => expect(occasion).toHaveValue("Nineteenth Sunday after Pentecost"));
    expect(screen.getByText("From the Revised Common Lectionary: Nineteenth Sunday after Pentecost")).toBeInTheDocument();
    expect(screen.getByLabelText("Scripture readings")).toHaveValue(ISAIAH.join("\n"));

    await user.type(occasion, " (Harvest)");
    expect(occasion).toHaveValue("Nineteenth Sunday after Pentecost (Harvest)");
    expect(screen.getByText("Edited from the lectionary (Nineteenth Sunday after Pentecost)")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Service date"), { target: { value: "2026-10-11" } });
    expect(screen.getByText("Entered by you")).toBeInTheDocument();

    // After a refetch that lists the sets in another order, the caption follows the lines, not the stored index.
    const october4 = lectionary("2026-10-04");
    const reordered = { ...october4, reading_sets: [...october4.reading_sets].reverse() };
    const edited = editOccasion(applyReadingSet(testDraft(), october4, 0), "Harvest");
    expect(occasionCaption(edited, reordered)).toBe("Edited from the lectionary (Nineteenth Sunday after Pentecost)");
    expect(occasionCaption(applyReadingSet(testDraft(), october4, 1), reordered)).toBe(
      "From the Revised Common Lectionary: Resurrection of the Lord",
    );
  });

  it("says where archived fields came from, and shows no caption for empty ones", async () => {
    const archived = testDraft((d) => ({
      ...d,
      readings: { ...d.readings, fields_origin: "archive", occasion: "Harvest", scriptures: ["Joel 2:21-27"] },
    }));
    const { unmount } = renderStep({}, archived);
    expect(await screen.findByText("From the saved service")).toBeInTheDocument();
    unmount();
    window.localStorage.clear();
    renderStep();
    await screen.findByLabelText("Occasion");
    expect(screen.queryByText(/^From the|^Entered by you|^Edited from/)).toBeNull();
  });

  it("marks typed fields as the user's, shows the limits, and drops a stale pick only when the lines lose focus", async () => {
    const filled = setPick(applyReadingSet(testDraft(), lectionary("2026-10-04"), 0), "ot", "Isaiah 5:1-7");
    const { user } = renderStep({}, filled);
    const occasion = await screen.findByLabelText("Occasion");
    fireEvent.change(occasion, { target: { value: "x".repeat(301) } });
    expect(screen.getByText("Too long (max 300 characters).")).toBeInTheDocument();
    expect(occasion).toHaveAttribute("aria-invalid", "true");
    fireEvent.change(occasion, { target: { value: "Harvest Sunday" } });
    expect(screen.queryByText("Too long (max 300 characters).")).toBeNull();

    const lines = screen.getByLabelText("Scripture readings");
    fireEvent.change(lines, { target: { value: `Isaiah 5:1-7\n${"y".repeat(201)}` } });
    expect(screen.getByText("Line 2 is too long (max 200 characters).")).toBeInTheDocument();
    fireEvent.change(lines, { target: { value: Array.from({ length: 21 }, (_, i) => `Psalm ${i + 1}`).join("\n\n") } });
    expect(screen.getByText("Up to 20 readings.")).toBeInTheDocument();

    // Typing keeps the pick (retyping the line restores it); leaving the field drops it when it is no longer a line.
    await user.clear(lines);
    await user.type(lines, "Psalm 80:7-15");
    expect(probe()).toContain("/user/ot=Isaiah 5:1-7/");
    await user.click(occasion);
    expect(probe()).toContain("/user/ot=auto/");
  });
});

// --- lectionary status (S UX item 2; AC14) ---------------------------------------

const UNAVAILABLE = "The lectionary couldn't be reached. Enter readings yourself, or try again in a few minutes.";

/** Filled from October 4's lectionary, then moved to Tuesday, September 29. */
function staleDraft(): DraftV1 {
  return setDate(applyReadingSet(testDraft(), lectionary("2026-10-04"), 0), "2026-09-29");
}

/** A handler that gives each answer in turn, then repeats the last. */
function inTurn(...answers: FakeHandler[]): FakeHandler {
  let n = 0;
  return (req: RecordedRequest) => {
    const answer = answers[Math.min(n, answers.length - 1)];
    n += 1;
    return typeof answer === "function" ? (answer as (r: RecordedRequest) => unknown)(req) : answer;
  };
}

describe("lectionary status (S UX item 2)", () => {
  it("no readings: names the day, never moves focus, and Enter readings focuses Occasion", async () => {
    const { user } = renderStep({ lookup: lectionaryRoute(noReadings) });
    const date = await screen.findByLabelText("Service date");
    date.focus();
    fireEvent.change(date, { target: { value: "2026-09-29" } });
    const none = await screen.findByText("No lectionary readings for Tuesday, September 29, 2026.");
    expect(none.closest("[role=status]")).not.toBeNull(); // information, not an alert
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.getByText("Enter the occasion and readings below.")).toBeInTheDocument();
    expect(date).toHaveFocus();
    await user.click(screen.getByRole("button", { name: "Enter readings" }));
    expect(screen.getByLabelText("Occasion")).toHaveFocus();
  });

  it("unavailable: the lectionary's own copy, the stale note, and Try again refetches", async () => {
    const { user, lookups } = renderStep(
      {
        lookup: inTurn(
          fakeError(502, "upstream_error", UNAVAILABLE),
          lectionaryRoute((date) => lectionary(date, { partial: true })),
        ),
      },
      staleDraft(),
    );
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(UNAVAILABLE);
    expect(
      screen.getByText("These readings are from Nineteenth Sunday after Pentecost (October 4, 2026), not September 29, 2026."),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Occasion")).toHaveValue("Nineteenth Sunday after Pentecost"); // untouched

    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(
      await screen.findByText("One lectionary source didn't respond, so other reading options for this date may be missing."),
    ).toBeInTheDocument();
    expect(lookups()).toEqual(["/lectionary/readings?date=2026-09-29", "/lectionary/readings?date=2026-09-29"]);
    await waitFor(() => expect(screen.getByLabelText("Occasion")).toHaveValue("Nineteenth Sunday after Pentecost"));
    expect(screen.queryByText(/^These readings are from/)).toBeNull(); // refilled for September 29
  });

  it("rate limited: Try again waits for Retry-After, and typing still works meanwhile", async () => {
    const limited = fakeError(429, "rate_limited", "Too many requests. Try again in 1 seconds.", {
      details: { retry_after_seconds: 1 },
    });
    const { user, lookups } = renderStep(
      {
        lookup: inTurn({ ...limited, headers: { ...limited.headers, "Retry-After": "1" } }, lectionaryRoute(lectionary)),
      },
      staleDraft(),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("Too many requests — try again in 1 s.");
    expect(
      screen.getByText("These readings are from Nineteenth Sunday after Pentecost (October 4, 2026), not September 29, 2026."),
    ).toBeInTheDocument(); // the stale note shows while rate limited too
    const retry = screen.getByRole("button", { name: "Try again" });
    expect(retry).toBeDisabled();
    await user.clear(screen.getByLabelText("Occasion"));
    await user.type(screen.getByLabelText("Occasion"), "Harvest");
    expect(screen.getByLabelText("Occasion")).toHaveValue("Harvest");
    await waitFor(() => expect(retry).toBeEnabled(), { timeout: 3_000 });
    expect(screen.getByRole("alert")).toHaveTextContent("Try again now."); // owner answer D
    expect(screen.queryByText(/^Too many requests/)).toBeNull();
    await user.click(retry);
    await waitFor(() => expect(lookups()).toHaveLength(2));
    await waitFor(() => expect(screen.queryByText(/^Too many requests/)).toBeNull());
    expect(screen.getByLabelText("Occasion")).toHaveValue("Harvest"); // typed fields are never replaced
  });

  it("stale fields stay until Clear readings empties them", async () => {
    const { user } = renderStep({ lookup: lectionaryRoute(noReadings) }, staleDraft());
    const note = await screen.findByText(
      "These readings are from Nineteenth Sunday after Pentecost (October 4, 2026), not September 29, 2026.",
    );
    expect(screen.getByLabelText("Scripture readings")).toHaveValue(ISAIAH.join("\n"));
    // The note stays without a date, or with one the lookup refuses.
    const date = screen.getByLabelText("Service date");
    fireEvent.change(date, { target: { value: "" } });
    expect(
      screen.getByText("These readings are from Nineteenth Sunday after Pentecost (October 4, 2026)."),
    ).toBeInTheDocument();
    fireEvent.change(date, { target: { value: "1850-06-02" } });
    expect(
      screen.getByText("These readings are from Nineteenth Sunday after Pentecost (October 4, 2026), not June 2, 1850."),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Clear readings" }));
    expect(screen.queryByText(/^These readings are from/)).toBeNull();
    expect(note).not.toBeInTheDocument();
    expect(screen.getByLabelText("Occasion")).toHaveValue("");
    expect(screen.getByLabelText("Scripture readings")).toHaveValue("");
    expect(probe()).toContain("/empty/");
  });

  it("shows Loading while the date settles and the lookup runs, and Still working after 8 s", async () => {
    vi.useRealTimers(); // a second useFakeTimers call would keep beforeEach's Date-only fake
    vi.useFakeTimers({ toFake: ["Date", "setTimeout", "clearTimeout"], shouldAdvanceTime: true });
    vi.setSystemTime(DRAFT_NOW);
    renderStep({ lookup: () => new Promise(() => {}) });
    expect(await screen.findByText("Looking up the lectionary…")).toBeInTheDocument();
    expect(screen.queryByText("Still working — this can take up to a minute.")).toBeNull();
    act(() => {
      vi.advanceTimersByTime(8_000);
    });
    expect(screen.getByText("Still working — this can take up to a minute.")).toBeInTheDocument();
  });
});

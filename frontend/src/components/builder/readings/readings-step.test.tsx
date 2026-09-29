/**
 * The Date & readings step (S UX "Step 1", Testing `readings-step.test.tsx`;
 * AC14-AC16). The step renders inside the real builder layout against the fake
 * API. Only `Date` is faked (Tuesday, September 29, 2026 at noon in New York),
 * so a fresh draft is dated Sunday, October 4, and the 400 ms lookup delay and
 * the draft's writes run on real timers.
 */
import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { focusManager, onlineManager } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import { useLectionaryLookup } from "@/components/builder/lectionary-sync";
import type { Lectionary } from "@/lib/api/types";
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

    fireEvent.change(input, { target: { value: "0020-06-02" } }); // a year half typed
    fireEvent.change(input, { target: { value: "1850-06-02" } });
    // Neither the message nor the long date while it may still be typed (no "…, 0020" flashing by).
    expect(screen.queryByText("Enter a date between 1900 and 2199.")).toBeNull();
    expect(step().queryByText("Sunday, June 2, 1850")).toBeNull();
    // The lookup settles on 1850 and sends nothing; the next date's lookup is the next request.
    await waitFor(() => expect(screen.getByTestId("lookup-date")).toHaveTextContent("1850-06-02"));
    expect(screen.getByText("Enter a date between 1900 and 2199.")).toBeInTheDocument();
    expect(step().getByText("Sunday, June 2, 1850")).toBeInTheDocument();
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
    fireEvent.change(lines, { target: { value: `Isaiah 5:1-7\n  ${"y".repeat(200)}  ` } }); // the trimmed line counts
    expect(screen.queryByText(/is too long/)).toBeNull();
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
    const partial = await screen.findByText(
      "One lectionary source didn't respond, so other reading options for this date may be missing.",
    );
    // The button is gone, so focus moves to the answer rather than dropping to the page.
    await waitFor(() => expect(document.activeElement).toHaveAttribute("tabindex", "-1"));
    expect(document.activeElement).toContainElement(partial);
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

  it("a 429 is a rate limit whatever its code, for the lookup and for passage text", async () => {
    const base = fakeError(429, "too_many_requests", "Slow down.");
    const limited = { ...base, headers: { ...base.headers, "Retry-After": "1" } };
    const { user } = renderStep({ lookup: limited, passages: passagesRoute(() => limited) }, typedLines(["Romans 8:1"]));
    expect(await screen.findByRole("alert")).toHaveTextContent("Too many requests — try again in 1 s.");
    const romans = await findRow("Romans 8:1");
    await user.click(romans.getByRole("button", { name: "Show text: Romans 8:1" }));
    expect(await romans.findByText("Too many requests — try again in 1 s.")).toBeInTheDocument();
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
    expect(screen.getByLabelText("Occasion")).toHaveFocus(); // not dropped to the page with the button
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

// --- reading sets and the available banner (S UX items 2 and 3; AC14, AC15) ------

const EASTER = ["Acts 10:34-43", "Psalm 118:1-2, 14-24", "Colossians 3:1-4", "John 20:1-18"];

/** Two sets with the same name: only their index tells them apart. */
function twins(date: string): Lectionary {
  const answer = lectionary(date);
  return { ...answer, reading_sets: answer.reading_sets.map((set) => ({ ...set, name: "Nativity of the Lord" })) };
}

const OCT_11 = ["Isaiah 25:1-9", "Psalm 23", "Philippians 4:1-9", "Matthew 22:1-14"];

/** October 4 has the two fixture sets; October 11 and 18 have one set each, with their own lines. */
function october(date: string): Lectionary {
  const own: Record<string, [string, string[]]> = {
    "2026-10-11": ["Twentieth Sunday after Pentecost", OCT_11],
    "2026-10-18": ["Twenty-First Sunday after Pentecost", ["Isaiah 45:1-7", "Psalm 96:1-9", "1 Thessalonians 1:1-10", "Matthew 22:15-22"]],
  };
  const answer = lectionary(date);
  if (!own[date]) return answer;
  const [name, scriptures] = own[date];
  return { ...answer, reading_sets: [{ name, scriptures, source: "merged" }], default_index: 0 };
}

describe("reading sets and the available banner (S UX items 2 and 3)", () => {
  it("shows one card per set, keyed by index, and choosing another applies it and makes the date the user's", async () => {
    const { user } = renderStep({ lookup: lectionaryRoute(twins) });
    const group = await screen.findByRole("radiogroup", { name: "This date has more than one set of readings" });
    const cards = within(group).getAllByRole("radio");
    expect(cards).toHaveLength(2);
    await waitFor(() => expect(cards[0]).toBeChecked());
    expect(within(group).getByText(ISAIAH.join(" · "))).toBeInTheDocument();
    expect(within(group).getByText(EASTER.join(" · "))).toBeInTheDocument();
    expect(probe()).toMatch(/^default\/lectionary\//);
    // The whole card is the tap target (44 px), not only the 16 px radio.
    const easterCard = within(group).getByText(EASTER.join(" · ")).closest("label");
    expect(easterCard).toContainElement(cards[1]);
    expect(easterCard).toHaveClass("flex", "min-h-11", "cursor-pointer", "p-3");
    expect(within(group).getByText(EASTER.join(" · "))).toHaveClass("wrap-anywhere"); // never widens the page

    await user.click(easterCard as HTMLLabelElement);
    expect(screen.queryByRole("alertdialog")).toBeNull(); // lectionary fields: no question
    await waitFor(() => expect(cards[1]).toBeChecked());
    expect(screen.getByLabelText("Scripture readings")).toHaveValue(EASTER.join("\n"));
    expect(probe()).toMatch(/^user\/lectionary\//);
  });

  it("asks before a set replaces typed readings: Keep mine keeps them, Replace readings replaces them", async () => {
    const { user } = renderStep({ lookup: lectionaryRoute(october) }, testDraft((d) => editOccasion(d, "Harvest")));
    const group = await screen.findByRole("radiogroup", { name: "This date has more than one set of readings" });
    await user.click(within(group).getByText(EASTER.join(" · ")));
    let dialog = await screen.findByRole("alertdialog", { name: "Replace your readings?" });
    expect(dialog).toHaveAccessibleDescription(
      "Your occasion and scripture list will be replaced with “Resurrection of the Lord” from the lectionary.",
    );
    await user.click(within(dialog).getByRole("button", { name: "Keep mine" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(screen.getByLabelText("Occasion")).toHaveValue("Harvest");
    // The switcher's Keep mine only closes its question; the banner stays (owner answer C).
    expect(screen.getByText("Readings for October 4, 2026 are available.")).toBeInTheDocument();

    await user.click(within(group).getByText(EASTER.join(" · ")));
    dialog = await screen.findByRole("alertdialog", { name: "Replace your readings?" });
    await user.click(within(dialog).getByRole("button", { name: "Replace readings" }));
    await waitFor(() => expect(screen.getByLabelText("Occasion")).toHaveValue("Resurrection of the Lord"));
    expect(probe()).toMatch(/^user\/lectionary\//);
  });

  it("after typing, a new date shows the banner instead of replacing; Use them asks, then replaces", async () => {
    const { user } = renderStep({ lookup: lectionaryRoute(october) });
    const occasion = await screen.findByLabelText("Occasion");
    await waitFor(() => expect(occasion).toHaveValue("Nineteenth Sunday after Pentecost"));
    await user.clear(occasion);
    await user.type(occasion, "Harvest");
    fireEvent.change(screen.getByLabelText("Service date"), { target: { value: "2026-10-11" } });
    const banner = await screen.findByText("Readings for October 11, 2026 are available.");
    expect(banner.closest("[role=status]")).not.toBeNull(); // an offer, not an alert
    expect(occasion).toHaveValue("Harvest");

    await user.click(screen.getByRole("button", { name: "Use them" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Replace your readings?" });
    expect(dialog).toHaveAccessibleDescription(
      "Your occasion and scripture list will be replaced with “Twentieth Sunday after Pentecost” from the lectionary.",
    );
    await user.click(within(dialog).getByRole("button", { name: "Replace readings" }));
    await waitFor(() => expect(occasion).toHaveValue("Twentieth Sunday after Pentecost"));
    expect(screen.queryByText("Readings for October 11, 2026 are available.")).toBeNull();
  });

  it("deleting the Psalm line of this date's set raises no banner; Keep mine hides it for that date for the session", async () => {
    const { user } = renderStep({ lookup: lectionaryRoute(october) });
    const lines = await screen.findByLabelText("Scripture readings");
    await waitFor(() => expect(lines).toHaveValue(ISAIAH.join("\n")));
    fireEvent.change(lines, { target: { value: [ISAIAH[0], ISAIAH[2], ISAIAH[3]].join("\n") } });
    expect(probe()).toMatch(/\/user\//);
    // Once the edit is written (400 ms later), still no banner.
    await waitFor(() => expect(JSON.parse(window.localStorage.getItem(KEY) ?? "{}").readings.scriptures).toHaveLength(3));
    expect(screen.queryByText(/are available\.$/)).toBeNull();

    fireEvent.change(screen.getByLabelText("Service date"), { target: { value: "2026-10-11" } });
    await user.click(await screen.findByRole("button", { name: "Use them" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Replace your readings?" });
    await user.click(within(dialog).getByRole("button", { name: "Keep mine" }));
    await waitFor(() => expect(screen.queryByText("Readings for October 11, 2026 are available.")).toBeNull());

    fireEvent.change(screen.getByLabelText("Service date"), { target: { value: "2026-10-18" } });
    expect(await screen.findByText("Readings for October 18, 2026 are available.")).toBeInTheDocument();

    // Back on October 11 the banner stays hidden: remembered for the tab's session (owner answer C).
    fireEvent.change(screen.getByLabelText("Service date"), { target: { value: "2026-10-11" } });
    await waitFor(() => expect(screen.getByTestId("lookup-date")).toHaveTextContent("2026-10-11"));
    expect(screen.queryByText(/are available\.$/)).toBeNull();
    expect(JSON.parse(window.sessionStorage.getItem(`wsb:readingsKeptMine:${church().id}`) ?? "[]")).toEqual([
      "2026-10-11",
    ]);
  });

  it("on a one-set date, edited readings can go back to the lectionary's, asking first (owner answer B)", async () => {
    const { user } = renderStep({ lookup: lectionaryRoute(october) }, setDate(testDraft(), "2026-10-11"));
    const lines = await screen.findByLabelText("Scripture readings");
    await waitFor(() => expect(lines).toHaveValue(OCT_11.join("\n")));
    expect(screen.queryByRole("button", { name: "Use the lectionary's readings" })).toBeNull(); // the set's own lines

    fireEvent.change(lines, { target: { value: "Isaiah 25:1-9\nPsalm 23" } });
    await user.click(await screen.findByRole("button", { name: "Use the lectionary's readings" }));
    let dialog = await screen.findByRole("alertdialog", { name: "Replace your readings?" });
    await user.click(within(dialog).getByRole("button", { name: "Keep mine" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(lines).toHaveValue("Isaiah 25:1-9\nPsalm 23");

    await user.click(screen.getByRole("button", { name: "Use the lectionary's readings" }));
    dialog = await screen.findByRole("alertdialog", { name: "Replace your readings?" });
    await user.click(within(dialog).getByRole("button", { name: "Replace readings" }));
    await waitFor(() => expect(lines).toHaveValue(OCT_11.join("\n")));
    expect(screen.queryByRole("button", { name: "Use the lectionary's readings" })).toBeNull();
    expect(probe()).toMatch(/\/lectionary\//);
  });

  it("only the banner's Keep mine remembers the date, and it hides the lectionary link too; Escape just closes (owner answers 1, 2)", async () => {
    const { user } = renderStep({ lookup: lectionaryRoute(october) });
    const occasion = await screen.findByLabelText("Occasion");
    await waitFor(() => expect(occasion).toHaveValue("Nineteenth Sunday after Pentecost"));
    fireEvent.change(screen.getByLabelText("Scripture readings"), { target: { value: "Joel 2:21-27" } });
    fireEvent.change(screen.getByLabelText("Service date"), { target: { value: "2026-10-11" } });
    await user.click(await screen.findByRole("button", { name: "Use them" }));
    await screen.findByRole("alertdialog", { name: "Replace your readings?" });
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(screen.getByText("Readings for October 11, 2026 are available.")).toBeInTheDocument();
    expect(window.sessionStorage.getItem(`wsb:readingsKeptMine:${church().id}`)).toBeNull();
    await waitFor(() => expect(screen.getByRole("button", { name: "Use them" })).toHaveFocus());

    await user.click(screen.getByRole("button", { name: "Use them" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Replace your readings?" });
    await user.click(within(dialog).getByRole("button", { name: "Keep mine" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(screen.queryByText(/are available\.$/)).toBeNull();
    expect(screen.queryByRole("button", { name: "Use the lectionary's readings" })).toBeNull();
    expect(screen.getByLabelText("Scripture readings")).toHaveValue("Joel 2:21-27");
    // The banner went with its button; focus lands on the status area, not the page.
    await waitFor(() => expect(document.activeElement).toHaveAttribute("tabindex", "-1"));
    expect(JSON.parse(window.sessionStorage.getItem(`wsb:readingsKeptMine:${church().id}`) ?? "[]")).toEqual([
      "2026-10-11",
    ]);
  });

  it("on a date with several sets, lines edited away from the chosen set can go back to it, asking first (owner answer 3)", async () => {
    const { user } = renderStep({ lookup: lectionaryRoute(october) });
    const lines = await screen.findByLabelText("Scripture readings");
    await waitFor(() => expect(lines).toHaveValue(ISAIAH.join("\n")));
    expect(screen.queryByRole("button", { name: "Use the lectionary's readings" })).toBeNull();
    const group = screen.getByRole("radiogroup", { name: "This date has more than one set of readings" });
    await user.click(within(group).getByText(EASTER.join(" · ")));
    await waitFor(() => expect(lines).toHaveValue(EASTER.join("\n")));

    fireEvent.change(lines, { target: { value: EASTER.slice(0, 2).join("\n") } });
    await user.click(await screen.findByRole("button", { name: "Use the lectionary's readings" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Replace your readings?" });
    expect(dialog).toHaveAccessibleDescription(
      "Your occasion and scripture list will be replaced with “Resurrection of the Lord” from the lectionary.",
    );
    await user.click(within(dialog).getByRole("button", { name: "Replace readings" }));
    await waitFor(() => expect(lines).toHaveValue(EASTER.join("\n")));
    expect(screen.queryByRole("button", { name: "Use the lectionary's readings" })).toBeNull();
    // The link went with the question; focus lands in the status area (here its checked set), not the page.
    await waitFor(() => expect(document.activeElement).toHaveAttribute("aria-checked", "true"));
  });

  it("offers no lectionary link over empty fields, which the automatic fill handles", async () => {
    // A hidden tab never fills, so the empty fields stay empty for the check.
    vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden");
    const { lookups } = renderStep({ lookup: lectionaryRoute(october) }, setDate(testDraft(), "2026-10-11"));
    await waitFor(() => expect(lookups()).toEqual(["/lectionary/readings?date=2026-10-11"]));
    await waitFor(() => expect(screen.queryByText("Looking up the lectionary…")).toBeNull());
    expect(probe()).toContain("/empty/");
    expect(screen.queryByRole("button", { name: "Use the lectionary's readings" })).toBeNull();
  });

  it("an archived service keeps its fields on its own date, and is offered the readings after a date change", async () => {
    const archived = testDraft((d) => ({
      ...d,
      readings: {
        ...d.readings,
        date_origin: "archive",
        fields_origin: "archive",
        reading_set: null,
        occasion: "Harvest",
        scriptures: ["Joel 2:21-27"],
      },
    }));
    const { lookups } = renderStep({ lookup: lectionaryRoute(october) }, archived);
    const group = await screen.findByRole("radiogroup", { name: "This date has more than one set of readings" });
    for (const radio of within(group).getAllByRole("radio")) expect(radio).not.toBeChecked(); // neither set is these lines
    expect(lookups()).toEqual(["/lectionary/readings?date=2026-10-04"]);
    expect(screen.getByLabelText("Occasion")).toHaveValue("Harvest");
    expect(screen.queryByText(/are available\.$/)).toBeNull();

    fireEvent.change(screen.getByLabelText("Service date"), { target: { value: "2026-10-11" } });
    expect(await screen.findByText("Readings for October 11, 2026 are available.")).toBeInTheDocument();
    expect(screen.getByLabelText("Occasion")).toHaveValue("Harvest");
  });
});

// --- readings list and passage text (S UX item 6; AC16) -----------------------------

type Status = "ok" | "not_found" | "unavailable";
type PassageAnswer = { status: Status; sections: { reference: string; status: Status; text: string | null }[] };

/** One section per " or " alternative, all loaded. */
function okPassage(reference: string, translation = "web"): PassageAnswer {
  return {
    status: "ok",
    sections: reference.split(/\s+or\s+/i).map((alt) => ({ reference: alt, status: "ok", text: `${alt} (${translation}) text.` })),
  };
}

/** `POST /scripture/passages` answering each ref with `answer(ref, translation)` (or a `FakeResponse`). */
function passagesRoute(answer: (ref: string, translation: string) => PassageAnswer | ReturnType<typeof fakeError> = okPassage) {
  return (req: RecordedRequest) => {
    const { refs, translation } = req.body as { refs: string[]; translation: string };
    const result = answer(refs[0], translation);
    if ("status" in result && typeof result.status === "number") return result;
    return {
      translation,
      translation_label: translations().items.find((item) => item.id === translation)?.label ?? translation,
      passages: [{ reference: refs[0], ...(result as PassageAnswer) }],
    };
  };
}

function typedLines(lines: string[]): DraftV1 {
  return testDraft((d) => ({ ...d, readings: { ...d.readings, fields_origin: "user", occasion: "Harvest", scriptures: lines } }));
}

/** The row for `reference` in the Readings list. */
function row(reference: string) {
  const list = screen.getByRole("region", { name: "Readings" });
  const item = within(list)
    .getAllByRole("listitem")
    .find((li) => li.firstElementChild?.firstElementChild?.textContent === reference);
  if (!item) throw new Error(`no row for ${reference}`);
  return within(item);
}

async function findRow(reference: string) {
  await waitFor(() => row(reference));
  return row(reference);
}

describe("readings list and passage text (S UX item 6)", () => {
  it("fetches a passage only when its row opens: one reference, in the church's translation", async () => {
    const { user, api } = renderStep({ passages: passagesRoute() }, applyReadingSet(testDraft(), lectionary("2026-10-04"), 0));
    const isaiah = await findRow("Isaiah 5:1-7");
    expect(isaiah.getByText("OT")).toBeInTheDocument();
    expect(row("Psalm 80:7-15").getByText("Psalm")).toBeInTheDocument();
    expect(row("Matthew 21:33-46").getByText("NT")).toBeInTheDocument();
    expect(screen.getByText("Passage text shown in World English Bible (WEB).")).toBeInTheDocument();
    expect(api.requests.filter((r) => r.method === "POST")).toEqual([]);

    await user.click(isaiah.getByRole("button", { name: "Show text: Isaiah 5:1-7" }));
    expect(await isaiah.findByText("Isaiah 5:1-7 (web) text.")).toBeInTheDocument();
    expect(api.requests.filter((r) => r.method === "POST").map((r) => [r.path, r.body, r.headers["X-Church-Id"]])).toEqual([
      ["/scripture/passages", { refs: ["Isaiah 5:1-7"], translation: "web" }, undefined],
    ]);
    await user.click(isaiah.getByRole("button", { name: "Hide text: Isaiah 5:1-7" }));
    expect(isaiah.queryByText("Isaiah 5:1-7 (web) text.")).toBeNull();
  });

  it("shows not found, unavailable and partial answers with their copy, and Try again refetches", async () => {
    const PASSION = "Matthew 26:14-27:66 or Matthew 27:11-54";
    let isaiahCalls = 0;
    let passionCalls = 0;
    const { user, api } = renderStep(
      {
        passages: passagesRoute((ref, translation) => {
          if (ref === "Hezekiah 1:1") return { status: "not_found", sections: [{ reference: ref, status: "not_found", text: null }] };
          if (ref === "Isaiah 50:4-9a") {
            isaiahCalls += 1;
            return isaiahCalls === 1
              ? { status: "unavailable", sections: [{ reference: ref, status: "unavailable", text: null }] }
              : okPassage(ref, translation);
          }
          passionCalls += 1;
          if (passionCalls === 2) return fakeError(500, "internal_error", "Something went wrong.");
          return {
            status: "unavailable",
            sections: [
              { reference: "Matthew 26:14-27:66", status: "unavailable", text: null },
              { reference: "Matthew 27:11-54", status: "ok", text: "Jesus stood before the governor." },
            ],
          };
        }),
      },
      typedLines(["Hezekiah 1:1", "Isaiah 50:4-9a", PASSION]),
    );
    const hezekiah = await findRow("Hezekiah 1:1");
    const unknown = hezekiah.getByRole("button", { name: "Book not recognized" });
    expect(unknown).toHaveTextContent("?");
    expect(unknown).toHaveClass("h-6", "min-w-6"); // a 24 px target on phones
    expect(row(PASSION).getAllByText("NT")).toHaveLength(2);

    await user.click(hezekiah.getByRole("button", { name: "Show text: Hezekiah 1:1" }));
    expect(
      await hezekiah.findByText("Couldn't find this passage. Check the reference, for example “Matthew 17:1-9”."),
    ).toBeInTheDocument();

    const isaiah = row("Isaiah 50:4-9a");
    await user.click(isaiah.getByRole("button", { name: "Show text: Isaiah 50:4-9a" }));
    expect(await isaiah.findByText("Passage text isn't available right now.")).toBeInTheDocument();
    await user.click(isaiah.getByRole("button", { name: "Try again: Isaiah 50:4-9a" }));
    expect(await isaiah.findByText("Isaiah 50:4-9a (web) text.")).toBeInTheDocument();

    const passion = row(PASSION);
    await user.click(passion.getByRole("button", { name: `Show text: ${PASSION}` }));
    expect(await passion.findByText("Jesus stood before the governor.")).toBeInTheDocument();
    expect(passion.getByText("Matthew 27:11-54")).toBeInTheDocument(); // each alternative under its own heading
    expect(passion.getByText("Couldn't load Matthew 26:14-27:66.")).toBeInTheDocument();
    expect(passion.getByText("Part of this passage couldn't be loaded.")).toBeInTheDocument();
    const before = api.requests.filter((r) => r.method === "POST").length;
    await user.click(passion.getByRole("button", { name: `Try again: ${PASSION}` }));
    await waitFor(() => expect(api.requests.filter((r) => r.method === "POST").length).toBe(before + 1));
    // That retry fails; the text already loaded stays, with Try again.
    await waitFor(() => expect(passion.getByRole("button", { name: `Try again: ${PASSION}` })).toBeEnabled());
    expect(passion.getByText("Jesus stood before the governor.")).toBeInTheDocument();
    expect(passion.queryByText("Passage text isn't available right now.")).toBeNull();
  });

  it("a failed request says the text isn't available, a 429 waits for Retry-After, and a 422 shows the server's message", async () => {
    const limited = fakeError(429, "rate_limited", "Too many requests. Try again in 1 seconds.", {
      details: { retry_after_seconds: 1 },
    });
    let limitedCalls = 0;
    const { user } = renderStep(
      {
        passages: passagesRoute((ref, translation) => {
          if (ref === "John 3:16") return fakeError(500, "internal_error", "Something went wrong.");
          if (ref === "Romans 8:1") {
            limitedCalls += 1;
            return limitedCalls === 1 ? limited : okPassage(ref, translation);
          }
          return fakeError(422, "invalid_request", "Too many passages in one request.", {
            fields: { refs: "Too many passages in one request." },
          });
        }),
      },
      typedLines(["John 3:16", "Romans 8:1", "Psalm 1; Psalm 2; Psalm 3"]),
    );
    const john = await findRow("John 3:16");
    await user.click(john.getByRole("button", { name: "Show text: John 3:16" }));
    expect(await john.findByText("Passage text isn't available right now.")).toBeInTheDocument();
    expect(john.getByRole("button", { name: "Try again: John 3:16" })).toBeEnabled();

    const romans = row("Romans 8:1");
    await user.click(romans.getByRole("button", { name: "Show text: Romans 8:1" }));
    expect(await romans.findByText("Too many requests — try again in 1 s.")).toBeInTheDocument();
    expect(romans.getByRole("button", { name: "Try again: Romans 8:1" })).toBeDisabled();
    // Until Retry-After passes, reopening the row, coming back to the tab or reconnecting asks nothing.
    await user.click(romans.getByRole("button", { name: "Hide text: Romans 8:1" }));
    await user.click(romans.getByRole("button", { name: "Show text: Romans 8:1" }));
    expect(await romans.findByText("Too many requests — try again in 1 s.")).toBeInTheDocument();
    act(() => {
      focusManager.setFocused(true);
      onlineManager.setOnline(false);
      onlineManager.setOnline(true);
    });
    focusManager.setFocused(undefined);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(limitedCalls).toBe(1);
    const retry = romans.getByRole("button", { name: "Try again: Romans 8:1" });
    expect(retry).toBeDisabled();
    await waitFor(() => expect(retry).toBeEnabled(), { timeout: 3_000 });
    expect(romans.getByText("Try again now.")).toBeInTheDocument(); // owner answer D
    await user.click(retry);
    expect(await romans.findByText("Romans 8:1 (web) text.")).toBeInTheDocument();

    const psalms = row("Psalm 1; Psalm 2; Psalm 3");
    await user.click(psalms.getByRole("button", { name: "Show text: Psalm 1; Psalm 2; Psalm 3" }));
    expect(await psalms.findByText("Too many passages in one request.")).toBeInTheDocument();
  });

  it("never opens or sends a line over 200 characters, and editing a line closes its row", async () => {
    const long = `Genesis 1:1 ${"x".repeat(200)}`;
    const { user, api } = renderStep({ passages: passagesRoute() }, typedLines(["Mark 1:1-8", long]));
    const longRow = await findRow(long);
    // Base UI keeps a disabled trigger focusable, so it is aria-disabled rather than disabled.
    // A long unbroken line wraps anywhere rather than widening the page.
    expect(longRow.getByText(long)).toHaveClass("wrap-anywhere");
    expect(within(screen.getByRole("complementary")).getByText(long)).toHaveClass("wrap-anywhere"); // the summary too
    const longToggle = longRow.getByRole("button", { name: `Show text: ${long}` });
    expect(longToggle).toHaveAttribute("aria-disabled", "true");
    await user.click(longToggle);

    const mark = row("Mark 1:1-8");
    await user.click(mark.getByRole("button", { name: "Show text: Mark 1:1-8" }));
    await mark.findByText("Mark 1:1-8 (web) text.");
    fireEvent.change(screen.getByLabelText("Scripture readings"), { target: { value: `Mark 1:1-11\n${long}` } });
    const edited = await findRow("Mark 1:1-11");
    expect(edited.getByRole("button", { name: "Show text: Mark 1:1-11" })).toBeInTheDocument();
    // Typed back, the line's row stays closed: the edit forgot it was open.
    fireEvent.change(screen.getByLabelText("Scripture readings"), { target: { value: `Mark 1:1-8\n${long}` } });
    const retyped = await findRow("Mark 1:1-8");
    expect(retyped.getByRole("button", { name: "Show text: Mark 1:1-8" })).toBeInTheDocument();
    expect(retyped.queryByText("Mark 1:1-8 (web) text.")).toBeNull();
    expect(api.requests.filter((r) => r.method === "POST").map((r) => (r.body as { refs: string[] }).refs[0])).toEqual([
      "Mark 1:1-8",
    ]);
  });

  it("Show all text opens every row with at most 3 requests in flight", async () => {
    let inFlight = 0;
    let most = 0;
    const lines = ["Genesis 1:1", "Exodus 3:1", "Psalm 23", "Romans 8:1", "John 1:1"];
    const { user, api } = renderStep(
      {
        passages: async (req: RecordedRequest) => {
          inFlight += 1;
          most = Math.max(most, inFlight);
          await new Promise((resolve) => setTimeout(resolve, 60));
          inFlight -= 1;
          return passagesRoute()(req);
        },
      },
      typedLines(lines),
    );
    await findRow("John 1:1");
    await user.click(screen.getByRole("button", { name: "Show all text" }));
    for (const line of lines) expect(await row(line).findByText(`${line} (web) text.`)).toBeInTheDocument();
    expect(api.requests.filter((r) => r.method === "POST")).toHaveLength(5);
    expect(most).toBe(3);
  });

  it("changing the translation refetches open rows in it and stores the choice", async () => {
    const { user, api } = renderStep({ passages: passagesRoute() }, typedLines(["Mark 1:1-8"]));
    const mark = await findRow("Mark 1:1-8");
    await user.click(mark.getByRole("button", { name: "Show text: Mark 1:1-8" }));
    await mark.findByText("Mark 1:1-8 (web) text.");

    await user.click(screen.getByRole("combobox", { name: "Bible translation" }));
    await user.click(await screen.findByRole("option", { name: "King James Version (KJV)" }));
    expect(await mark.findByText("Mark 1:1-8 (kjv) text.")).toBeInTheDocument();
    expect(screen.getByText("Passage text shown in King James Version (KJV).")).toBeInTheDocument();
    expect(api.requests.filter((r) => r.method === "POST").map((r) => (r.body as { translation: string }).translation)).toEqual([
      "web",
      "kjv",
    ]);
    expect(probe()).toMatch(/\/t=kjv$/);
  });

  it("with no readings it says what to do, and a failed translation list shows the church's translation", async () => {
    renderStep({ translations: fakeError(500, "internal_error", "Something went wrong.") });
    expect(await screen.findByText("Add a reading above to see its text and choose the bulletin readings.")).toBeInTheDocument();
    const select = screen.getByRole("combobox", { name: "Bible translation" });
    await waitFor(() => expect(select).toHaveAttribute("data-disabled"));
    expect(select).toHaveTextContent("World English Bible (WEB)");
    expect(screen.getByText("Passage text shown in World English Bible (WEB).")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Show all text" })).toBeDisabled();
  });
});

// --- bulletin readings (S UX item 7; AC8 on screen) ----------------------------------

describe("bulletin readings (S UX item 7)", () => {
  it("offers only NT lines for NT, and the automatic NT is the epistle, never the Psalm", async () => {
    const { user } = renderStep({}, applyReadingSet(testDraft(), lectionary("2026-10-04"), 0));
    const ot = await screen.findByRole("combobox", { name: "Old Testament reading" });
    const nt = screen.getByRole("combobox", { name: "New Testament reading" });
    expect(ot).toHaveTextContent("Automatic: Isaiah 5:1-7");
    expect(nt).toHaveTextContent("Automatic: Philippians 3:4b-14");
    expect(screen.queryByRole("button", { name: /^Use automatic/ })).toBeNull();

    await user.click(nt);
    const options = await screen.findAllByRole("option");
    expect(options.map((option) => option.textContent)).toEqual(["Philippians 3:4b-14", "Matthew 21:33-46"]);
    await user.click(screen.getByRole("option", { name: "Matthew 21:33-46" }));
    await waitFor(() => expect(nt).toHaveTextContent("Matthew 21:33-46"));
    expect(probe()).toContain("/nt=Matthew 21:33-46/");
    expect(ot).toHaveTextContent("Automatic: Isaiah 5:1-7");
  });

  it("with the Easter lines, picking Psalm 118 as the OT makes the automatic NT Acts; Use automatic clears the pick", async () => {
    const { user } = renderStep({}, applyReadingSet(testDraft(), lectionary("2026-10-04"), 1));
    const ot = await screen.findByRole("combobox", { name: "Old Testament reading" });
    const nt = screen.getByRole("combobox", { name: "New Testament reading" });
    expect(ot).toHaveTextContent("Automatic: Acts 10:34-43");
    expect(nt).toHaveTextContent("Automatic: Colossians 3:1-4");

    await user.click(ot);
    await user.click(await screen.findByRole("option", { name: "Psalm 118:1-2, 14-24" }));
    await waitFor(() => expect(nt).toHaveTextContent("Automatic: Acts 10:34-43"));
    expect(ot).toHaveTextContent("Psalm 118:1-2, 14-24");
    expect(probe()).toContain("/ot=Psalm 118:1-2, 14-24/");

    await user.click(screen.getByRole("button", { name: "Use automatic Old Testament reading" }));
    await waitFor(() => expect(ot).toHaveTextContent("Automatic: Acts 10:34-43"));
    expect(nt).toHaveTextContent("Automatic: Colossians 3:1-4");
    expect(probe()).toContain("/ot=auto/");
  });

  it("says None — choose one when a side has no reading", async () => {
    renderStep({}, typedLines(["Isaiah 9:2-7", "Psalm 96"]));
    const nt = await screen.findByRole("combobox", { name: "New Testament reading" });
    expect(nt).toHaveTextContent("None — choose one");
    expect(screen.getByRole("combobox", { name: "Old Testament reading" })).toHaveTextContent("Automatic: Isaiah 9:2-7");
  });
});

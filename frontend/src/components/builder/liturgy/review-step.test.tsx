/**
 * The service reviewer on the Liturgy step (reviewer spec, "User experience"
 * and Testing "Frontend"; slice 4 spec, reviewer amendment "UI hooks" and
 * Testing). The step runs inside the real builder layout against the fake
 * API. The clock is Tuesday, September 29, 2026 (only `Date` is faked).
 */
import { act, screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import { Toaster } from "@/components/ui/sonner";
import type { ReviewBody, ReviseBody } from "@/lib/api/types";
import { draftKey, type DraftV1, type SectionKey } from "@/lib/draft/schema";
import { fakeError, installFakeApi, type FakeHandler } from "@/test/fake-api";
import {
  church,
  churchProfile,
  DRAFT_NOW,
  generateRoute,
  lectionaryRoute,
  liturgyConfig,
  me,
  reviewNote,
  reviewResult,
  reviewRoute,
  reviseRoute,
  testDraft,
  USER_ID,
} from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { LiturgyStep } from "./liturgy-step";
import { STILL_WORKING } from "./use-still-working";

const KEY = draftKey(USER_ID, church().id);
const STOCK = 'Stock phrase "as we journey". Say it more naturally.';
const QUICK = "Only quick checks ran. The full review isn't available right now.";
const STALE = "From before your last edit.";

type Origin = DraftV1["liturgy"]["cards"]["benediction"]["origin"];

function withCard(d: DraftV1, key: SectionKey, text: string, origin: Origin, enabled = true): DraftV1 {
  return { ...d, liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, [key]: { enabled, text, origin } } } };
}

/** A typed Call to Worship, an AI Opening Prayer and Assurance, an archived Confession, the default Benediction. */
function seeded(): DraftV1 {
  let d = withCard(testDraft(), "call_to_worship", "Leader: As we journey, come.", "typed");
  d = withCard(d, "opening_prayer", "Gracious God, as we journey, hear us.", "ai");
  d = withCard(d, "prayer_of_confession", "Merciful God, we confess.", "archive");
  d = withCard(d, "assurance", "Leader: In Christ we are forgiven.", "ai");
  return {
    ...d,
    liturgy: { ...d.liturgy, custom_elements: [{ id: "c1", label: "Children's Moment", text: "As we journey", insert_after: "opening_prayer" }] },
  };
}

const ANSWER = reviewResult({
  cards: [
    { section: "call_to_worship", notes: [reviewNote("rules", STOCK, "code")] },
    {
      section: "opening_prayer",
      notes: [reviewNote("rules", STOCK, "code"), reviewNote("read_aloud", "The second clause is hard to say aloud.")],
    },
    { section: "prayer_of_confession", notes: [reviewNote("theology", "Confession comes before any word of grace.")] },
    { section: "assurance", notes: [reviewNote("checklist", "Name Christ as the source of pardon.")] },
    { section: "benediction", notes: [] },
  ],
  service_notes: [reviewNote("repetition", 'Several prayers open with "Gracious God".', "code")],
});

function stored(): DraftV1 {
  return JSON.parse(window.localStorage.getItem(KEY) ?? "null") as DraftV1;
}

function renderStep(draft: DraftV1 = seeded(), routes: Record<string, FakeHandler> = {}) {
  window.localStorage.setItem(KEY, JSON.stringify(draft));
  const api = installFakeApi({
    "GET /church": churchProfile(),
    "GET /lectionary/readings": lectionaryRoute(),
    "GET /liturgy/config": liturgyConfig(),
    "POST /liturgy/review": reviewRoute(() => ANSWER),
    ...routes,
  });
  const view = renderWithProviders(
    <>
      <BuilderLayout>
        <LiturgyStep />
      </BuilderLayout>
      <Toaster />
    </>,
    { me: me(), church: church(), path: "/builder/liturgy" },
  );
  return { ...view, api };
}

function card(label: string) {
  return screen.getByRole("region", { name: label });
}

function reviewButton() {
  return screen.getByRole("button", { name: "Review service" });
}

async function review(user: ReturnType<typeof renderStep>["user"]) {
  await user.click(await screen.findByRole("button", { name: "Review service" }));
  await screen.findByText("Review finished. 6 notes.");
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
  toast.dismiss(); // sonner replays a toast still showing to the next Toaster
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("Review service (R User experience)", () => {
  it("is off until a switched-on card has text, then shows each card's notes, Looks good. and Across the service", async () => {
    const empty = renderStep(testDraft((d) => withCard(d, "benediction", "Halverson", "default", false)));
    const off = await screen.findByRole("button", { name: "Review service" });
    expect(off).toHaveAttribute("aria-disabled", "true");
    await empty.user.click(off);
    expect(empty.api.requests.some((r) => r.path === "/liturgy/review")).toBe(false);
    empty.unmount();

    const { user, api } = renderStep();
    await review(user);
    // Every switched-on card with text, in order; never a custom element, hymn or reading.
    const sent = api.requests.find((r) => r.path === "/liturgy/review")?.body as ReviewBody;
    expect(sent.cards.map((c) => [c.section, c.origin])).toEqual([
      ["call_to_worship", "typed"],
      ["opening_prayer", "ai"],
      ["prayer_of_confession", "archive"],
      ["assurance", "ai"],
      ["benediction", "default"],
    ]);
    expect(JSON.stringify(sent)).not.toContain("Children's Moment");
    const opening = within(card("Opening Prayer")).getByRole("list", { name: "Notes on Opening Prayer" });
    expect(within(opening).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      `Rules${STOCK}`,
      "Read aloudThe second clause is hard to say aloud.",
    ]);
    expect(within(card("Benediction")).getByText("Looks good.")).toBeInTheDocument();
    expect(within(card("Offertory Prayer")).queryByText("Looks good.")).toBeNull(); // empty: not reviewed
    const box = screen.getByRole("region", { name: "Across the service" });
    expect(within(box).getByText('Several prayers open with "Gracious God".')).toBeInTheDocument();
    expect(within(box).getByText("Repetition")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Benediction" })).toHaveAccessibleDescription(
      "Your church's default benediction. Admins can change it in Settings. Looks good.",
    );
    expect(screen.queryByText(QUICK)).toBeNull();
    expect(reviewButton()).toHaveFocus(); // focus stays on the one button
  });

  it("dismisses one note at a time, moving focus to the next, then to the card; the box goes with its last note", async () => {
    const { user } = renderStep();
    await review(user);
    const opening = card("Opening Prayer");
    await user.click(within(opening).getByRole("button", { name: `Dismiss note: ${STOCK}` }));
    expect(within(opening).queryByText(STOCK)).toBeNull();
    expect(within(opening).getByRole("button", { name: "Dismiss note: The second clause is hard to say aloud." })).toHaveFocus();
    await user.click(within(opening).getByRole("button", { name: "Dismiss note: The second clause is hard to say aloud." }));
    expect(within(opening).queryByRole("list", { name: "Notes on Opening Prayer" })).toBeNull();
    expect(within(opening).queryByText("Looks good.")).toBeNull(); // dismissed, not "good"
    expect(within(opening).getByRole("heading", { name: "Opening Prayer" })).toHaveFocus();
    const box = screen.getByRole("region", { name: "Across the service" });
    await user.click(within(box).getByRole("button", { name: /^Dismiss note: Several prayers/ }));
    expect(screen.queryByRole("region", { name: "Across the service" })).toBeNull();
    expect(reviewButton()).toHaveFocus();
    expect(within(card("Call to Worship")).getByText(STOCK)).toBeInTheDocument(); // the others stay
  });

  it("fades a card's notes when it is typed in or set to the church default, and drops them when it is regenerated or cleared", async () => {
    const draft = withCard(seeded(), "benediction", "Go in peace.", "typed");
    const { user } = renderStep(draft, {
      "POST /liturgy/review": reviewRoute((body) =>
        reviewResult({ cards: body.cards.map((c) => ({ section: c.section, notes: [reviewNote("theology", `About ${c.section}.`)] })) }),
      ),
      "POST /liturgy/generate": generateRoute(),
    });
    await user.click(await screen.findByRole("button", { name: "Review service" }));
    await screen.findByText("Review finished. 5 notes.");
    // Typing: the notes stay, dimmed, under "From before your last edit.".
    await user.type(screen.getByRole("textbox", { name: "Call to Worship" }), "!");
    expect(within(card("Call to Worship")).getByText(STALE)).toBeInTheDocument();
    expect(within(card("Call to Worship")).getByText("About call_to_worship.")).toHaveClass("text-muted-foreground");
    // Regenerate on an AI card (no confirm): its notes go once its new draft lands.
    await user.click(within(card("Assurance of Pardon")).getByRole("button", { name: "Regenerate" }));
    await within(card("Assurance of Pardon")).findByText("Replaced with a new AI draft.");
    expect(within(card("Assurance of Pardon")).queryByText("About assurance.")).toBeNull();
    // Clear text: a blank card shows no notes.
    await user.click(within(card("Prayer of Confession")).getByRole("button", { name: "More actions for Prayer of Confession" }));
    await user.click(await screen.findByRole("menuitem", { name: "Clear text" }));
    expect(within(card("Prayer of Confession")).queryByText("About prayer_of_confession.")).toBeNull();
    // Use church default: the notes fade.
    await user.click(within(card("Benediction")).getByRole("button", { name: "More actions for Benediction" }));
    await user.click(await screen.findByRole("menuitem", { name: "Use church default" }));
    expect(within(card("Benediction")).getByText("About benediction.")).toBeInTheDocument();
    expect(within(card("Benediction")).getByText(STALE)).toBeInTheDocument();
    expect(within(card("Opening Prayer")).getByText("About opening_prayer.")).toBeInTheDocument(); // untouched
    expect(within(card("Opening Prayer")).queryByText(STALE)).toBeNull();
  });

  it("keeps faded notes readable and dismissable, drops Looks good. after an edit, and a new review replaces them", async () => {
    const { user } = renderStep();
    await review(user);
    const opening = card("Opening Prayer");
    await user.type(screen.getByRole("textbox", { name: "Opening Prayer" }), " Amen.");
    expect(within(opening).getByText(STALE)).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Opening Prayer" })).toHaveAccessibleDescription(expect.stringContaining(STALE));
    expect(within(opening).getByRole("list", { name: "Notes on Opening Prayer" })).toHaveAccessibleDescription(STALE);
    expect(within(opening).getByText(STOCK)).toHaveClass("text-muted-foreground");
    await user.click(within(opening).getByRole("button", { name: `Dismiss note: ${STOCK}` }));
    expect(within(opening).getByRole("button", { name: "Dismiss note: The second clause is hard to say aloud." })).toHaveFocus();
    expect(within(opening).getByText(STALE)).toBeInTheDocument();
    // "Looks good." goes after any edit, and the card shows nothing until the next review.
    await user.type(screen.getByRole("textbox", { name: "Benediction" }), "!");
    expect(within(card("Benediction")).queryByText("Looks good.")).toBeNull();
    expect(within(card("Benediction")).queryByText(STALE)).toBeNull();
    // "Across the service" stays until the next review.
    expect(screen.getByRole("region", { name: "Across the service" })).toBeInTheDocument();
    // The second review announces the same words as the first, so wait for the faded notes to go.
    await user.click(reviewButton());
    await waitFor(() => expect(screen.queryByText(STALE)).toBeNull());
    expect(within(opening).getByText(STOCK)).not.toHaveClass("text-muted-foreground");
    expect(within(card("Benediction")).getByText("Looks good.")).toBeInTheDocument();
  });

  it("drops the notes of a card edited while the review ran, and of every card after New service", async () => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => (release = resolve));
    const { user, api } = renderStep(seeded(), {
      "POST /liturgy/review": reviewRoute(async () => {
        await gate;
        return ANSWER;
      }),
    });
    await user.click(await screen.findByRole("button", { name: "Review service" }));
    await waitFor(() => expect(api.requests.some((r) => r.path === "/liturgy/review")).toBe(true));
    await user.type(screen.getByRole("textbox", { name: "Call to Worship" }), " Now.");
    release();
    expect(await screen.findByText("Review finished. 5 notes.")).toBeInTheDocument();
    expect(within(card("Call to Worship")).queryByText(STOCK)).toBeNull();
    expect(within(card("Opening Prayer")).getByText(STOCK)).toBeInTheDocument();
    // New service: no notes are left.
    vi.setSystemTime(new Date(DRAFT_NOW.getTime() + 60_000));
    await user.click(screen.getByRole("button", { name: "More actions" }));
    await user.click(await screen.findByRole("menuitem", { name: "New service" }));
    await user.click(await screen.findByRole("button", { name: "Start new service" }));
    await waitFor(() => expect(screen.queryByRole("region", { name: "Across the service" })).toBeNull());
    expect(screen.queryByText("Looks good.")).toBeNull();
  });

  it("shows the quick checks with a quiet line when the AI part is missing, and a failed review's message", async () => {
    const { user, api } = renderStep(seeded(), {
      "POST /liturgy/review": reviewRoute(() =>
        reviewResult({
          cards: [{ section: "opening_prayer", notes: [reviewNote("rules", STOCK, "code")] }],
          service_notes: [],
          ai_status: "not_configured",
        }),
      ),
    });
    await user.click(await screen.findByRole("button", { name: "Review service" }));
    expect(await screen.findByText(QUICK)).toBeInTheDocument();
    expect(screen.getByText("Review finished. 1 note. Only quick checks ran.")).toBeInTheDocument(); // read out too
    expect(within(card("Opening Prayer")).getByText(STOCK)).toBeInTheDocument();
    const reviews = () => api.requests.filter((r) => r.path === "/liturgy/review").length;
    for (const status of ["busy", "timeout", "rate_limited", "error"] as const) {
      api.set("POST /liturgy/review", reviewRoute(() => reviewResult({ ai_status: status })));
      const before = reviews();
      await user.click(reviewButton());
      await waitFor(() => expect(reviews()).toBe(before + 1));
      expect(await screen.findByText("Review finished. No notes. Only quick checks ran.")).toBeInTheDocument();
      expect(screen.getByText(QUICK)).toBeInTheDocument();
    }
    api.set("POST /liturgy/review", reviewRoute(() => ANSWER));
    await review(user);
    expect(screen.queryByText(QUICK)).toBeNull();
    api.set("POST /liturgy/review", fakeError(500, "internal_error", "Something went wrong."));
    await user.click(reviewButton());
    expect(await screen.findByRole("alert")).toHaveTextContent("Something went wrong. (Ref: 4f9a2c1e)");
    expect(within(card("Opening Prayer")).getByText(STOCK)).toBeInTheDocument(); // the last notes stay
  });

  it("says Still working after 8 s, and Cancel stops the wait and keeps focus on the button", async () => {
    vi.useRealTimers(); // a second useFakeTimers call would keep beforeEach's Date-only fake
    vi.useFakeTimers({ toFake: ["Date", "setTimeout", "clearTimeout"], shouldAdvanceTime: true });
    vi.setSystemTime(DRAFT_NOW);
    const { user, api } = renderStep(seeded(), { "POST /liturgy/review": () => new Promise<never>(() => {}) });
    await user.click(await screen.findByRole("button", { name: "Review service" }));
    const cancel = await screen.findByRole("button", { name: "Cancel review" });
    expect(cancel).toHaveTextContent("Cancel");
    expect(cancel).toHaveFocus();
    expect(screen.getByText("Reviewing…")).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(8_000);
    });
    expect(screen.getByText(`Reviewing… ${STILL_WORKING}`)).toBeInTheDocument();
    await user.click(cancel);
    expect(reviewButton()).toHaveFocus();
    expect(screen.queryByText(/Reviewing…/)).toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
    expect(api.requests.filter((r) => r.path === "/liturgy/review")).toHaveLength(1);
  });
});

describe("Revise with these notes (R Revise)", () => {
  it("is offered on AI, typed and archived cards with a note left; the Benediction only once it no longer follows the default", async () => {
    const answer = reviewResult({
      cards: [
        ...ANSWER.cards.filter((c) => c.section !== "benediction"),
        { section: "benediction", notes: [reviewNote("read_aloud", "The last line is long.")] },
      ],
      service_notes: ANSWER.service_notes,
    });
    const { user } = renderStep(seeded(), { "POST /liturgy/review": reviewRoute(() => answer) });
    await user.click(await screen.findByRole("button", { name: "Review service" }));
    await screen.findByText("Review finished. 7 notes.");
    for (const label of ["Opening Prayer", "Call to Worship", "Prayer of Confession"]) {
      expect(within(card(label)).getByRole("button", { name: "Revise with these notes" }), label).toBeInTheDocument();
    }
    expect(within(card("Assurance of Pardon")).getByRole("button", { name: "Revise with these notes" })).toHaveAccessibleDescription(
      "Assurance of Pardon",
    );
    const benediction = card("Benediction");
    expect(within(benediction).getByText("The last line is long.")).toBeInTheDocument();
    expect(within(benediction).queryByRole("button", { name: "Revise with these notes" })).toBeNull(); // follows the church default
    await user.type(screen.getByRole("textbox", { name: "Benediction" }), " Amen.");
    expect(within(benediction).getByText(STALE)).toBeInTheDocument();
    expect(within(benediction).getByRole("button", { name: "Revise with these notes" })).toBeInTheDocument(); // now your text
    // Its last note dismissed, a card has nothing to revise with.
    await user.click(within(card("Assurance of Pardon")).getByRole("button", { name: /^Dismiss note:/ }));
    expect(within(card("Assurance of Pardon")).queryByRole("button", { name: "Revise with these notes" })).toBeNull();
  });

  it("sends the card's text and remaining notes, replaces it as an AI draft with Undo, and Undo brings the draft back", async () => {
    const { user, api } = renderStep(seeded(), {
      "POST /liturgy/revise": reviseRoute(() => ({ text: "Gracious God, hear us now." })),
    });
    await review(user);
    const opening = card("Opening Prayer");
    await user.click(within(opening).getByRole("button", { name: "Dismiss note: The second clause is hard to say aloud." }));
    await user.click(within(opening).getByRole("button", { name: "Revise with these notes" }));
    expect(await within(opening).findByText("Revised with these notes.")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Opening Prayer" })).toHaveValue("Gracious God, hear us now.");
    expect(within(opening).getByText("AI draft")).toBeInTheDocument();
    expect(within(opening).queryByRole("list", { name: "Notes on Opening Prayer" })).toBeNull(); // the notes went with the text
    expect(within(opening).getByRole("button", { name: "Undo" })).toHaveFocus();
    const sent = api.requests.find((r) => r.path === "/liturgy/revise")?.body as ReviseBody;
    expect(sent).toMatchObject({ section: "opening_prayer", text: "Gracious God, as we journey, hear us.", notes: [STOCK] });
    await waitFor(() => expect(stored().liturgy.cards.opening_prayer).toEqual({ enabled: true, text: "Gracious God, hear us now.", origin: "ai" }));
    await user.click(within(opening).getByRole("button", { name: "Undo" }));
    expect(screen.getByRole("textbox", { name: "Opening Prayer" })).toHaveValue("Gracious God, as we journey, hear us.");
    expect(within(opening).queryByText("Revised with these notes.")).toBeNull();
    expect(within(card("Call to Worship")).getByText(STOCK)).toBeInTheDocument(); // other cards keep theirs
  });

  it("asks before revising typed or saved text: Keep my text sends nothing; Revise text revises the current text, with Undo", async () => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => (release = resolve));
    const { user, api } = renderStep(seeded(), {
      "POST /liturgy/revise": reviseRoute(async () => {
        await gate;
        return { text: "Leader: Come, all.\nPeople: We come." };
      }),
    });
    await review(user);
    const call = card("Call to Worship");
    const box = screen.getByRole("textbox", { name: "Call to Worship" });
    await user.type(box, " Now.");
    const revise = within(call).getByRole("button", { name: "Revise with these notes" }); // faded notes: still offered
    await user.click(revise);
    const dialog = await screen.findByRole("alertdialog", { name: "Replace your text?" });
    expect(dialog).toHaveTextContent(
      "Revise replaces the text in Call to Worship with a version that addresses these notes. You can undo right after.",
    );
    await user.click(within(dialog).getByRole("button", { name: "Keep my text" }));
    await waitFor(() => expect(revise).toHaveFocus());
    expect(api.requests.some((r) => r.path === "/liturgy/revise")).toBe(false);
    await user.click(revise);
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Revise text" }));
    await waitFor(() => expect(within(call).getByRole("button", { name: "Cancel revising Call to Worship" })).toHaveFocus());
    const sent = api.requests.find((r) => r.path === "/liturgy/revise")?.body as ReviseBody;
    expect(sent).toMatchObject({ section: "call_to_worship", text: "Leader: As we journey, come. Now.", notes: [STOCK] });
    release();
    expect(await within(call).findByText("Revised with these notes.")).toBeInTheDocument();
    expect(box).toHaveValue("Leader: Come, all.\nPeople: We come.");
    expect(within(call).getByText("AI draft")).toBeInTheDocument();
    expect(within(call).queryByRole("list", { name: "Notes on Call to Worship" })).toBeNull(); // addressed: they go
    expect(within(call).getByRole("button", { name: "Undo" })).toHaveFocus();
    await user.click(within(call).getByRole("button", { name: "Undo" }));
    expect(box).toHaveValue("Leader: As we journey, come. Now.");
    expect(within(call).getByText("Your text")).toBeInTheDocument();
  });

  it("closes Replace your text? when the notes change meanwhile, sending nothing; focus goes to the heading once Revise is gone", async () => {
    const { user, api } = renderStep();
    await review(user);
    const call = card("Call to Worship");
    await user.click(within(call).getByRole("button", { name: "Revise with these notes" }));
    expect(await screen.findByRole("alertdialog", { name: "Replace your text?" })).toBeInTheDocument();
    // Another tab clears the card: no notes are left to revise with.
    act(() => {
      const theirs = withCard(stored(), "call_to_worship", "", "empty");
      window.dispatchEvent(
        new StorageEvent("storage", { key: KEY, newValue: JSON.stringify({ ...theirs, updated_at: "2026-09-29T17:00:00.000Z" }) }),
      );
    });
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(within(call).queryByRole("list", { name: "Notes on Call to Worship" })).toBeNull();
    await waitFor(() => expect(screen.getByRole("heading", { name: "Call to Worship" })).toHaveFocus());
    // Another tab edits another card: the review changed, so the confirm closes; Revise is still there and takes focus.
    const confession = card("Prayer of Confession");
    await user.click(within(confession).getByRole("button", { name: "Revise with these notes" }));
    expect(await screen.findByRole("alertdialog", { name: "Replace your text?" })).toBeInTheDocument();
    act(() => {
      const theirs = withCard(stored(), "opening_prayer", "Holy One, hear us.", "typed");
      window.dispatchEvent(
        new StorageEvent("storage", { key: KEY, newValue: JSON.stringify({ ...theirs, updated_at: "2026-09-29T17:01:00.000Z" }) }),
      );
    });
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    await waitFor(() => expect(within(confession).getByRole("button", { name: "Revise with these notes" })).toHaveFocus());
    expect(api.requests.some((r) => r.path === "/liturgy/revise")).toBe(false);
  });

  it("keeps the card read-only while it revises; Cancel keeps the text and notes and returns focus to Revise", async () => {
    const { user } = renderStep(seeded(), { "POST /liturgy/revise": () => new Promise<never>(() => {}) });
    await review(user);
    const opening = card("Opening Prayer");
    await user.click(within(opening).getByRole("button", { name: "Revise with these notes" }));
    const cancel = within(opening).getByRole("button", { name: "Cancel revising Opening Prayer" });
    expect(cancel).toHaveFocus();
    expect(within(opening).getByRole("button", { name: "Revising…" })).toBeDisabled();
    expect(screen.getByRole("textbox", { name: "Opening Prayer" })).toHaveAttribute("readonly");
    expect(within(opening).getByRole("button", { name: "Regenerate" })).toBeDisabled();
    expect(within(opening).getByRole("button", { name: "More actions for Opening Prayer" })).toBeDisabled();
    await user.click(cancel);
    expect(within(opening).getByRole("button", { name: "Revise with these notes" })).toHaveFocus();
    expect(screen.getByRole("textbox", { name: "Opening Prayer" })).not.toHaveAttribute("readonly");
    expect(screen.getByRole("textbox", { name: "Opening Prayer" })).toHaveValue("Gracious God, as we journey, hear us.");
    expect(within(opening).getByText(STOCK)).toBeInTheDocument();
  });

  it("shows why a revision failed under the notes, keeps the text, and Revise tries again; Undo is off while it revises", async () => {
    const { user, api } = renderStep(seeded(), {
      "POST /liturgy/revise": fakeError(422, "prompt_invalid", "This prayer is too long to revise."),
    });
    await review(user);
    const opening = card("Opening Prayer");
    await user.click(within(opening).getByRole("button", { name: "Revise with these notes" }));
    expect(await within(opening).findByRole("alert")).toHaveTextContent("This prayer is too long to revise.");
    expect(within(opening).getByRole("button", { name: "Revise with these notes" })).toHaveFocus();
    expect(screen.getByRole("textbox", { name: "Opening Prayer" })).toHaveValue("Gracious God, as we journey, hear us.");
    api.set("POST /liturgy/revise", fakeError(503, "ai_busy", "The AI service is busy. Try again in a minute."));
    await user.click(within(opening).getByRole("button", { name: "Revise with these notes" }));
    expect(await within(opening).findByText("The AI service is busy. Try again in a minute.")).toBeInTheDocument();
    api.set("POST /liturgy/revise", reviseRoute());
    await user.click(within(opening).getByRole("button", { name: "Revise with these notes" }));
    expect(await within(opening).findByText("Revised with these notes.")).toBeInTheDocument();
    expect(within(opening).queryByRole("alert")).toBeNull();
    expect(screen.getByRole("textbox", { name: "Opening Prayer" })).toHaveValue("Opening Prayer revised with the notes.");
    // Reviewed again and revised again: the Undo line's Undo is off while it runs, as Regenerate and ⋯ are.
    api.set("POST /liturgy/revise", () => new Promise<never>(() => {}));
    await review(user);
    await user.click(within(opening).getByRole("button", { name: "Revise with these notes" }));
    expect(within(opening).getByRole("button", { name: "Undo" })).toBeDisabled();
    expect(within(opening).getByRole("button", { name: "Regenerate" })).toBeDisabled();
  });

  it("waits out a 429: the card shows the wait, and no Revise sends until it ends", async () => {
    const { user, api } = renderStep(seeded(), {
      "POST /liturgy/revise": fakeError(429, "rate_limited", "Too many requests. Try again in 30 seconds.", { details: { retry_after_seconds: 30 } }),
    });
    await review(user);
    const opening = card("Opening Prayer");
    await user.click(within(opening).getByRole("button", { name: "Revise with these notes" }));
    expect(await within(opening).findByRole("alert")).toHaveTextContent("Too many requests — try again in 30 s.");
    const again = within(opening).getByRole("button", { name: "Revise with these notes" });
    expect(again).toHaveAttribute("aria-disabled", "true");
    expect(again).toHaveFocus();
    await user.click(again);
    const other = within(card("Assurance of Pardon")).getByRole("button", { name: "Revise with these notes" });
    expect(other).toHaveAttribute("aria-disabled", "true"); // one wait for every card, and for Generate
    await user.click(other);
    expect(api.requests.filter((r) => r.path === "/liturgy/revise")).toHaveLength(1);
  });

  it("switching a revising card off cancels the revision silently; switched back on, the card keeps its text", async () => {
    let answer: (value: { text: string }) => void = () => {};
    const { user } = renderStep(seeded(), {
      "POST /liturgy/revise": reviseRoute(() => new Promise<{ text: string }>((resolve) => (answer = resolve))),
    });
    await review(user);
    const opening = card("Opening Prayer");
    await user.click(within(opening).getByRole("button", { name: "Revise with these notes" }));
    expect(within(opening).getByRole("button", { name: "Revising…" })).toBeInTheDocument();
    await user.click(within(opening).getByRole("switch", { name: "Include Opening Prayer" }));
    expect(within(opening).getByText("Off — not in the service. Any text is kept.")).toBeInTheDocument();
    await act(async () => {
      answer({ text: "Gracious God, hear us now." });
      await Promise.resolve();
    });
    await user.click(within(opening).getByRole("switch", { name: "Include Opening Prayer" }));
    expect(screen.getByRole("textbox", { name: "Opening Prayer" })).toHaveValue("Gracious God, as we journey, hear us.");
    expect(screen.getByRole("textbox", { name: "Opening Prayer" })).not.toHaveAttribute("readonly");
    expect(within(opening).queryByText("Revised with these notes.")).toBeNull();
    expect(within(opening).queryByRole("button", { name: "Revising…" })).toBeNull();
    expect(within(opening).getByRole("button", { name: "Revise with these notes" })).toBeEnabled();
    expect(stored().liturgy.cards.opening_prayer.text).toBe("Gracious God, as we journey, hear us.");
  });

  it("keeps Cancel while a one-note card revises, with its × off, even when another tab's edit fades the notes", async () => {
    const { user } = renderStep(seeded(), { "POST /liturgy/revise": () => new Promise<never>(() => {}) });
    await review(user);
    const assurance = card("Assurance of Pardon");
    await user.click(within(assurance).getByRole("button", { name: "Revise with these notes" }));
    expect(within(assurance).getByRole("button", { name: "Cancel revising Assurance of Pardon" })).toHaveFocus();
    expect(within(assurance).getByRole("button", { name: "Dismiss note: Name Christ as the source of pardon." })).toBeDisabled();
    // Another tab edits the card: its notes fade, the revision's Cancel stays.
    const theirs = withCard(stored(), "assurance", "From the other tab", "typed");
    act(() => {
      window.dispatchEvent(
        new StorageEvent("storage", { key: KEY, newValue: JSON.stringify({ ...theirs, updated_at: "2026-09-29T17:00:00.000Z" }) }),
      );
    });
    expect(await within(assurance).findByText(STALE)).toBeInTheDocument();
    const cancel = within(assurance).getByRole("button", { name: "Cancel revising Assurance of Pardon" });
    await user.click(cancel);
    expect(within(assurance).queryByRole("button", { name: "Revising…" })).toBeNull();
    expect(screen.getByRole("textbox", { name: "Assurance of Pardon" })).toHaveValue("From the other tab");
    expect(within(assurance).getByRole("button", { name: "Revise with these notes" })).toHaveFocus(); // now typed text
  });

  it("turns Try again off while the card revises", async () => {
    const { user } = renderStep(seeded(), {
      "POST /liturgy/generate": fakeError(503, "ai_busy", "The AI service is busy. Try again in a minute."),
      "POST /liturgy/revise": () => new Promise<never>(() => {}),
    });
    await review(user);
    const opening = card("Opening Prayer");
    await user.click(within(opening).getByRole("button", { name: "Regenerate" }));
    expect(await within(opening).findByText("The AI service is busy. Try again in a minute.")).toBeInTheDocument();
    expect(within(opening).getByRole("button", { name: "Try again" })).toBeEnabled();
    await user.click(within(opening).getByRole("button", { name: "Revise with these notes" }));
    expect(within(opening).getByRole("button", { name: "Try again" })).toBeDisabled();
    await user.click(within(opening).getByRole("button", { name: "Cancel revising Opening Prayer" }));
    expect(within(opening).getByRole("button", { name: "Try again" })).toBeEnabled();
  });

  it("sends focus to Revise, not an older Undo line, when a revision fails", async () => {
    const { user } = renderStep(seeded(), {
      "POST /liturgy/generate": generateRoute(),
      "POST /liturgy/revise": fakeError(422, "prompt_invalid", "This prayer is too long to revise."),
    });
    await screen.findByRole("button", { name: "Review service" });
    const opening = card("Opening Prayer");
    await user.click(within(opening).getByRole("button", { name: "Regenerate" }));
    expect(await within(opening).findByText("Replaced with a new AI draft.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Review service" }));
    await screen.findByText(/^Review finished\./);
    await user.click(within(opening).getByRole("button", { name: "Revise with these notes" }));
    expect(await within(opening).findByRole("alert")).toHaveTextContent("This prayer is too long to revise.");
    expect(within(opening).getByRole("button", { name: "Undo" })).toBeEnabled();
    expect(within(opening).getByRole("button", { name: "Revise with these notes" })).toHaveFocus();
  });

  it("a Revise 429 holds Generate, and its alert goes when the wait ends", async () => {
    vi.useRealTimers(); // a second useFakeTimers call would keep beforeEach's Date-only fake
    vi.useFakeTimers({ toFake: ["Date", "setTimeout", "clearTimeout"], shouldAdvanceTime: true });
    vi.setSystemTime(DRAFT_NOW);
    const { user, api } = renderStep(seeded(), {
      "POST /liturgy/generate": generateRoute(),
      "POST /liturgy/revise": fakeError(429, "rate_limited", "Too many requests. Try again in 30 seconds.", { details: { retry_after_seconds: 30 } }),
    });
    await review(user);
    const opening = card("Opening Prayer");
    await user.click(within(opening).getByRole("button", { name: "Revise with these notes" }));
    expect(await within(opening).findByRole("alert")).toHaveTextContent("Too many requests — try again in 30 s.");
    const illumination = card("Prayer for Illumination");
    await user.click(within(illumination).getByRole("button", { name: "Generate" }));
    expect(await within(illumination).findByText(/^Too many requests — try again in \d+ s\.$/)).toBeInTheDocument();
    expect(api.requests.filter((r) => r.path === "/liturgy/generate")).toHaveLength(0);
    act(() => {
      vi.advanceTimersByTime(31_000);
    });
    expect(within(opening).queryByRole("alert")).toBeNull();
    expect(within(opening).getByRole("button", { name: "Revise with these notes" })).toBeEnabled();
    expect(within(card("Assurance of Pardon")).getByRole("button", { name: "Revise with these notes" })).toBeEnabled();
  });

  it("a Generate 429 holds Revise, which shows the wait beside it until it ends", async () => {
    vi.useRealTimers(); // a second useFakeTimers call would keep beforeEach's Date-only fake
    vi.useFakeTimers({ toFake: ["Date", "setTimeout", "clearTimeout"], shouldAdvanceTime: true });
    vi.setSystemTime(DRAFT_NOW);
    const { user, api } = renderStep(seeded(), {
      "POST /liturgy/generate": fakeError(429, "rate_limited", "Too many requests. Try again in 30 seconds.", { details: { retry_after_seconds: 30 } }),
      "POST /liturgy/revise": reviseRoute(),
    });
    await review(user);
    await user.click(within(card("Prayer for Illumination")).getByRole("button", { name: "Generate" }));
    expect(await within(card("Prayer for Illumination")).findByText("Too many requests — try again in 30 s.")).toBeInTheDocument();
    const opening = card("Opening Prayer");
    const revise = within(opening).getByRole("button", { name: "Revise with these notes" });
    expect(revise).toHaveAttribute("aria-disabled", "true");
    expect(within(opening).getByText(/^Too many requests — try again in \d+ s\.$/)).toBeInTheDocument();
    expect(within(opening).queryByRole("alert")).toBeNull();
    await user.click(revise);
    expect(api.requests.filter((r) => r.path === "/liturgy/revise")).toHaveLength(0);
    act(() => {
      vi.advanceTimersByTime(31_000);
    });
    expect(revise).toBeEnabled();
    expect(within(opening).queryByText(/Too many requests/)).toBeNull();
    await user.click(revise);
    expect(await within(opening).findByText("Revised with these notes.")).toBeInTheDocument();
  });
});

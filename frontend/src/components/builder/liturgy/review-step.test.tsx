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
import type { ReviewBody } from "@/lib/api/types";
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
  testDraft,
  USER_ID,
} from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { LiturgyStep } from "./liturgy-step";
import { STILL_WORKING } from "./use-still-working";

const KEY = draftKey(USER_ID, church().id);
const STOCK = 'Stock phrase "as we journey". Say it more naturally.';
const QUICK = "Only quick checks ran. The full review isn't available right now.";

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

  it("clears a card's notes when it is typed in, regenerated, cleared or set to the church default", async () => {
    const draft = withCard(seeded(), "benediction", "Go in peace.", "typed");
    const { user } = renderStep(draft, {
      "POST /liturgy/review": reviewRoute((body) =>
        reviewResult({ cards: body.cards.map((c) => ({ section: c.section, notes: [reviewNote("theology", `About ${c.section}.`)] })) }),
      ),
      "POST /liturgy/generate": generateRoute(),
    });
    await user.click(await screen.findByRole("button", { name: "Review service" }));
    await screen.findByText("Review finished. 5 notes.");
    // Typing.
    await user.type(screen.getByRole("textbox", { name: "Call to Worship" }), "!");
    expect(within(card("Call to Worship")).queryByText("About call_to_worship.")).toBeNull();
    // Regenerate on an AI card (no confirm), once its new draft lands.
    await user.click(within(card("Assurance of Pardon")).getByRole("button", { name: "Regenerate" }));
    await within(card("Assurance of Pardon")).findByText("Replaced with a new AI draft.");
    expect(within(card("Assurance of Pardon")).queryByText("About assurance.")).toBeNull();
    // Clear text.
    await user.click(within(card("Prayer of Confession")).getByRole("button", { name: "More actions for Prayer of Confession" }));
    await user.click(await screen.findByRole("menuitem", { name: "Clear text" }));
    expect(within(card("Prayer of Confession")).queryByText("About prayer_of_confession.")).toBeNull();
    // Use church default.
    await user.click(within(card("Benediction")).getByRole("button", { name: "More actions for Benediction" }));
    await user.click(await screen.findByRole("menuitem", { name: "Use church default" }));
    expect(within(card("Benediction")).queryByText("About benediction.")).toBeNull();
    expect(within(card("Opening Prayer")).getByText("About opening_prayer.")).toBeInTheDocument(); // untouched
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

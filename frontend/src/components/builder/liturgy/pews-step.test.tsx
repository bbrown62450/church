/**
 * Hear it from the pews on the Liturgy step (pew voices spec 2026-10-20, "The
 * liturgy step" and Testing). The step runs inside the real builder layout
 * against the fake API. The clock is Tuesday, September 29, 2026 (only
 * `Date` is faked).
 */
import { act, screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import { Toaster } from "@/components/ui/sonner";
import type { PewsResult, ReviewBody, ReviseBody } from "@/lib/api/types";
import { draftKey, type DraftV1, type SectionKey } from "@/lib/draft/schema";
import { fakeError, installFakeApi, type FakeHandler } from "@/test/fake-api";
import {
  church,
  churchProfile,
  DRAFT_NOW,
  lectionaryRoute,
  liturgyConfig,
  me,
  reviewRoute,
  reviseRoute,
  testDraft,
  USER_ID,
} from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { PEWS_UNAVAILABLE } from "@/lib/liturgy/pews";

import { LiturgyStep } from "./liturgy-step";
import { PEWS_STILL_WORKING } from "./pews-panel";

const KEY = draftKey(USER_ID, church().id);
const TEEN = "I lost the thread in the long middle sentence.";
const WORRIED = "Nothing in the service named fear, which is what I carried in.";
const SHARP = "Calling God a friend in the confession felt too casual to me.";

type Origin = DraftV1["liturgy"]["cards"]["benediction"]["origin"];

function withCard(d: DraftV1, key: SectionKey, text: string, origin: Origin, enabled = true): DraftV1 {
  return { ...d, liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, [key]: { enabled, text, origin } } } };
}

/** A typed Call to Worship, an AI Opening Prayer and an archived Confession. */
function seeded(): DraftV1 {
  let d = withCard(testDraft(), "call_to_worship", "Leader: Come, let us worship.", "typed");
  d = withCard(d, "opening_prayer", "Gracious God, hear us.", "ai");
  return withCard(d, "prayer_of_confession", "Merciful God, our friend, we confess.", "archive");
}

const ANSWER: PewsResult = {
  voices: [
    { description: "Sharp, very conservative, reads every word", reactions: [{ text: SHARP, section: "prayer_of_confession", kind: "missed" }] },
    { description: "A teenager", reactions: [{ text: TEEN, section: "opening_prayer", kind: "missed" }] },
    { description: "A man who rarely comes to church", reactions: [] },
    { description: "Someone deeply worried about their health", reactions: [{ text: WORRIED, section: null, kind: "missed" }] },
  ],
};

function pewsRoute(answer: (body: ReviewBody) => PewsResult | { status: number } | Promise<PewsResult | { status: number }> = () => ANSWER) {
  return async (req: { body: unknown }) => answer(req.body as ReviewBody);
}

function renderStep(draft: DraftV1 = seeded(), routes: Record<string, FakeHandler> = {}) {
  window.localStorage.setItem(KEY, JSON.stringify(draft));
  const api = installFakeApi({
    "GET /church": churchProfile(),
    "GET /lectionary/readings": lectionaryRoute(),
    "GET /liturgy/config": liturgyConfig(),
    "POST /liturgy/review": reviewRoute(),
    "POST /liturgy/pews": pewsRoute(),
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

function panel() {
  return screen.getByRole("region", { name: "From the pews" });
}

function pewsRequests(api: ReturnType<typeof renderStep>["api"]) {
  return api.requests.filter((r) => r.path === "/liturgy/pews");
}

async function hear(user: ReturnType<typeof renderStep>["user"]) {
  await user.click(await screen.findByRole("button", { name: "Hear it from the pews" }));
  await screen.findByText("From the pews: 3 reactions.");
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
  toast.dismiss();
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("Hear it from the pews (pew voices spec)", () => {
  it("is off with nothing to hear; one tap sends the review's cards once and shows each voice's reactions", async () => {
    const empty = renderStep(testDraft());
    const off = await screen.findByRole("button", { name: "Hear it from the pews" });
    expect(off).toHaveAttribute("aria-disabled", "true");
    await empty.user.click(off);
    expect(pewsRequests(empty.api)).toHaveLength(0);
    empty.unmount();

    const { user, api } = renderStep();
    await hear(user);
    expect(pewsRequests(api)).toHaveLength(1);
    const body = pewsRequests(api)[0].body as ReviewBody;
    expect(body.cards.map((c) => [c.section, c.origin])).toEqual([
      ["call_to_worship", "typed"],
      ["opening_prayer", "ai"],
      ["prayer_of_confession", "archive"],
    ]);
    const box = panel();
    expect(within(box).getByRole("heading", { name: "A teenager" })).toBeInTheDocument();
    expect(within(box).queryByRole("heading", { name: "A man who rarely comes to church" })).toBeNull(); // no reactions
    const teen = within(box).getByRole("list", { name: "Reactions from A teenager" });
    expect(teen).toHaveTextContent(`Didn't landAbout Opening Prayer${TEEN}`);
    const worried = within(box).getByRole("list", { name: "Reactions from Someone deeply worried about their health" });
    expect(worried).toHaveTextContent(WORRIED);
    expect(within(worried).queryByText(/^About /)).toBeNull();
    expect(within(worried).queryByRole("button", { name: "Revise with this" })).toBeNull(); // the whole service
    expect(api.requests.some((r) => r.path === "/liturgy/review")).toBe(false); // its own button, its own request
  });

  it("labels each reaction Helped or Didn't land, and offers Revise with this only on one that did not land", async () => {
    const helped = "Naming the hospital waiting room in the prayer made me feel seen.";
    const missed = "The long middle sentence lost me.";
    const unknown = "I was not sure what this prayer asked of me.";
    const { user } = renderStep(seeded(), {
      "POST /liturgy/pews": pewsRoute(() => ({
        voices: [
          {
            description: "A teenager",
            reactions: [
              { text: helped, section: "opening_prayer", kind: "helped" },
              { text: missed, section: "opening_prayer", kind: "missed" },
            ],
          },
          { description: "A man who rarely comes to church", reactions: [{ text: unknown, section: "opening_prayer", kind: null }] },
        ],
      })),
    });
    await user.click(await screen.findByRole("button", { name: "Hear it from the pews" }));
    const box = await screen.findByRole("region", { name: "From the pews" });
    const items = within(within(box).getByRole("list", { name: "Reactions from A teenager" })).getAllByRole("listitem");
    expect(items[0]).toHaveTextContent(`HelpedAbout Opening Prayer${helped}`);
    expect(within(items[0]).queryByRole("button", { name: "Revise with this" })).toBeNull();
    expect(items[1]).toHaveTextContent(`Didn't landAbout Opening Prayer${missed}`);
    expect(within(items[1]).getByRole("button", { name: "Revise with this" })).toBeInTheDocument();
    // No kind (the AI gave neither): no label, and no Revise, the safer default.
    const other = within(box).getByRole("list", { name: "Reactions from A man who rarely comes to church" });
    expect(other).toHaveTextContent(`About Opening Prayer${unknown}`);
    expect(within(other).queryByText(/^(Helped|Didn't land)$/)).toBeNull();
    expect(within(other).queryByRole("button", { name: "Revise with this" })).toBeNull();
    expect(box.textContent).not.toContain("\u2014");
  });

  it("says No reactions this time. for an empty answer, and shows a failure's message", async () => {
    let answer: PewsResult | { status: number } = { voices: [{ description: "A teenager", reactions: [] }] };
    const { user } = renderStep(seeded(), { "POST /liturgy/pews": pewsRoute(() => answer) });
    await user.click(await screen.findByRole("button", { name: "Hear it from the pews" }));
    expect(await within(panel()).findByText("No reactions this time.")).toBeInTheDocument();
    answer = fakeError(503, "ai_busy", "The AI service is busy. Try again in a minute.");
    await user.click(screen.getByRole("button", { name: "Hear it from the pews" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("The AI service is busy. Try again in a minute.");
    expect(within(panel()).getByText("No reactions this time.")).toBeInTheDocument(); // the last answer stays
  });

  it("shows the server's 422 for no voice turned on, and its own words for a 404", async () => {
    let answer: PewsResult | { status: number } = fakeError(422, "invalid_request", "Turn on at least one voice in Settings → Prayers.");
    const { user } = renderStep(seeded(), { "POST /liturgy/pews": pewsRoute(() => answer) });
    await user.click(await screen.findByRole("button", { name: "Hear it from the pews" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Turn on at least one voice in Settings → Prayers.");
    answer = fakeError(404, "not_found", "Not found.");
    await user.click(screen.getByRole("button", { name: "Hear it from the pews" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(PEWS_UNAVAILABLE));
    expect(screen.getByRole("alert").textContent).not.toMatch(/hymn/i);
  });

  it("Cancel leaves no request live: an answer that comes after shows nothing, and the next tap asks again", async () => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => (release = resolve));
    let calls = 0;
    const { user, api } = renderStep(seeded(), {
      "POST /liturgy/pews": pewsRoute(async () => {
        calls += 1;
        if (calls === 1) await gate;
        return ANSWER;
      }),
    });
    await user.click(await screen.findByRole("button", { name: "Hear it from the pews" }));
    await user.click(await screen.findByRole("button", { name: "Cancel hearing from the pews" }));
    release();
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
    });
    expect(screen.queryByRole("region", { name: "From the pews" })).toBeNull();
    expect(screen.queryByText(/^From the pews: /)).toBeNull();
    await hear(user);
    expect(pewsRequests(api)).toHaveLength(2);
    expect(within(panel()).getByText(TEEN)).toBeInTheDocument();
  });

  it("says Still working after 8 s with no em dash, and Cancel stops the wait and keeps focus on the button", async () => {
    vi.useRealTimers();
    vi.useFakeTimers({ toFake: ["Date", "setTimeout", "clearTimeout"], shouldAdvanceTime: true });
    vi.setSystemTime(DRAFT_NOW);
    const { user, api } = renderStep(seeded(), { "POST /liturgy/pews": () => new Promise<never>(() => {}) });
    await user.click(await screen.findByRole("button", { name: "Hear it from the pews" }));
    const cancel = await screen.findByRole("button", { name: "Cancel hearing from the pews" });
    expect(cancel).toHaveTextContent("Cancel");
    expect(cancel).toHaveFocus();
    act(() => {
      vi.advanceTimersByTime(8_000);
    });
    const line = screen.getByText(`Listening… ${PEWS_STILL_WORKING}`);
    expect(line.textContent).not.toContain("\u2014");
    await user.click(cancel);
    expect(screen.getByRole("button", { name: "Hear it from the pews" })).toHaveFocus();
    expect(screen.queryByText(/Listening…/)).toBeNull();
    expect(screen.queryByRole("region", { name: "From the pews" })).toBeNull();
    expect(pewsRequests(api)).toHaveLength(1);
  });

  it("drops a reaction about a prayer edited while it ran, and keeps the rest", async () => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => (release = resolve));
    const { user } = renderStep(seeded(), {
      "POST /liturgy/pews": pewsRoute(async () => {
        await gate;
        return ANSWER;
      }),
    });
    await user.click(await screen.findByRole("button", { name: "Hear it from the pews" }));
    await screen.findByRole("button", { name: "Cancel hearing from the pews" });
    await user.type(screen.getByRole("textbox", { name: "Opening Prayer" }), " Amen.");
    release();
    expect(await screen.findByText("From the pews: 2 reactions.")).toBeInTheDocument();
    expect(within(panel()).queryByText(TEEN)).toBeNull();
    expect(within(panel()).getByText(SHARP)).toBeInTheDocument();
    expect(within(panel()).getByText(WORRIED)).toBeInTheDocument();
  });

  it("clears a reaction when its prayer's text changes; a whole-service one stays; × dismisses one", async () => {
    const { user } = renderStep();
    await hear(user);
    await user.type(screen.getByRole("textbox", { name: "Prayer of Confession" }), " Amen.");
    expect(within(panel()).queryByText(SHARP)).toBeNull();
    expect(within(panel()).getByText(TEEN)).toBeInTheDocument();
    expect(within(panel()).getByText(WORRIED)).toBeInTheDocument();
    await user.click(within(panel()).getByRole("button", { name: `Dismiss reaction: ${WORRIED}` }));
    expect(within(panel()).queryByText(WORRIED)).toBeNull();
    await user.click(within(panel()).getByRole("button", { name: `Dismiss reaction: ${TEEN}` }));
    expect(screen.queryByRole("region", { name: "From the pews" })).toBeNull(); // nothing left: the box goes
  });

  it("Revise with this sends the reaction as the one note and replaces an AI draft with Undo", async () => {
    const { user, api } = renderStep(seeded(), {
      "POST /liturgy/revise": reviseRoute(() => ({ text: "Gracious God, hear us now." })),
    });
    await hear(user);
    const teen = within(panel()).getByRole("list", { name: "Reactions from A teenager" });
    await user.click(within(teen).getByRole("button", { name: "Revise with this" }));
    const opening = card("Opening Prayer");
    expect(await within(opening).findByText("Revised with these notes.")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Opening Prayer" })).toHaveValue("Gracious God, hear us now.");
    const sent = api.requests.filter((r) => r.path === "/liturgy/revise");
    expect(sent).toHaveLength(1);
    expect(sent[0].body as ReviseBody).toMatchObject({ section: "opening_prayer", text: "Gracious God, hear us.", notes: [TEEN] });
    expect(within(panel()).queryByText(TEEN)).toBeNull(); // the prayer changed, so its reaction went
    await user.click(within(opening).getByRole("button", { name: "Undo" }));
    expect(screen.getByRole("textbox", { name: "Opening Prayer" })).toHaveValue("Gracious God, hear us.");
  });

  it("asks before revising saved or typed text: Keep my text sends nothing; Revise text revises", async () => {
    const { user, api } = renderStep(seeded(), {
      "POST /liturgy/revise": reviseRoute(() => ({ text: "Merciful God, we confess." })),
    });
    await hear(user);
    const sharp = within(panel()).getByRole("list", { name: "Reactions from Sharp, very conservative, reads every word" });
    await user.click(within(sharp).getByRole("button", { name: "Revise with this" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Replace your text?" });
    expect(dialog).toHaveTextContent(
      "Revise replaces the text in Prayer of Confession with a version that answers this reaction. You can undo right after.",
    );
    expect(dialog.textContent).not.toContain("\u2014");
    await user.click(within(dialog).getByRole("button", { name: "Keep my text" }));
    expect(api.requests.some((r) => r.path === "/liturgy/revise")).toBe(false);
    await user.click(within(sharp).getByRole("button", { name: "Revise with this" }));
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Revise text" }));
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Prayer of Confession" })).toHaveValue("Merciful God, we confess."));
    expect(api.requests.filter((r) => r.path === "/liturgy/revise")[0].body as ReviseBody).toMatchObject({ notes: [SHARP] });
    expect(within(card("Prayer of Confession")).getByRole("button", { name: "Undo" })).toBeInTheDocument();
  });

  it("asks before revising the member's own typed text too", async () => {
    const typed = "The call to worship moved so fast I missed the invitation.";
    const { user, api } = renderStep(seeded(), {
      "POST /liturgy/pews": pewsRoute(() => ({ voices: [{ description: "A teenager", reactions: [{ text: typed, section: "call_to_worship", kind: "missed" }] }] })),
    });
    await user.click(await screen.findByRole("button", { name: "Hear it from the pews" }));
    const teen = await within(await screen.findByRole("region", { name: "From the pews" })).findByRole("list", { name: "Reactions from A teenager" });
    await user.click(within(teen).getByRole("button", { name: "Revise with this" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Replace your text?" });
    expect(dialog).toHaveTextContent("Revise replaces the text in Call to Worship with a version that answers this reaction.");
    await user.click(within(dialog).getByRole("button", { name: "Keep my text" }));
    expect(api.requests.some((r) => r.path === "/liturgy/revise")).toBe(false);
  });

  it("Revise with this is gone on a switched-off card and off while its card is being revised", async () => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => (release = resolve));
    const { user, api } = renderStep(seeded(), {
      "POST /liturgy/revise": reviseRoute(async () => {
        await gate;
        return { text: "Gracious God, hear us now." };
      }),
    });
    await hear(user);
    await user.click(within(card("Prayer of Confession")).getByRole("switch", { name: "Include Prayer of Confession" }));
    const sharp = within(panel()).getByRole("list", { name: "Reactions from Sharp, very conservative, reads every word" });
    expect(within(sharp).getByText(SHARP)).toBeInTheDocument();
    expect(within(sharp).queryByRole("button", { name: "Revise with this" })).toBeNull();
    const teen = within(panel()).getByRole("list", { name: "Reactions from A teenager" });
    await user.click(within(teen).getByRole("button", { name: "Revise with this" }));
    const again = within(teen).getByRole("button", { name: "Revise with this" });
    await waitFor(() => expect(again).toHaveAttribute("aria-disabled", "true"));
    await user.click(again);
    expect(api.requests.filter((r) => r.path === "/liturgy/revise")).toHaveLength(1);
    release();
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Opening Prayer" })).toHaveValue("Gracious God, hear us now."));
  });

  it("during a 429's wait, Revise with this is off with the wait beside it, until the wait ends", async () => {
    vi.useRealTimers(); // a second useFakeTimers call would keep beforeEach's Date-only fake
    vi.useFakeTimers({ toFake: ["Date", "setTimeout", "clearTimeout"], shouldAdvanceTime: true });
    vi.setSystemTime(DRAFT_NOW);
    const { user, api } = renderStep(seeded(), {
      "POST /liturgy/revise": fakeError(429, "rate_limited", "Too many requests. Try again in 30 seconds.", { details: { retry_after_seconds: 30 } }),
    });
    await hear(user);
    const teen = within(panel()).getByRole("list", { name: "Reactions from A teenager" });
    await user.click(within(teen).getByRole("button", { name: "Revise with this" }));
    expect(await within(card("Opening Prayer")).findByRole("alert")).toHaveTextContent(/Too many requests/);
    const revise = within(teen).getByRole("button", { name: "Revise with this" });
    expect(revise).toHaveAttribute("aria-disabled", "true");
    const wait = within(teen).getByText(/^Too many requests\. Try again in \d+ seconds\.$/);
    expect(wait.parentElement).toBe(revise.parentElement); // beside the button
    expect(wait.textContent).not.toContain("\u2014");
    await user.click(revise);
    expect(api.requests.filter((r) => r.path === "/liturgy/revise")).toHaveLength(1);
    act(() => {
      vi.advanceTimersByTime(31_000);
    });
    expect(revise).toBeEnabled();
    expect(within(teen).queryByText(/Too many requests/)).toBeNull();
  });

  it("a 429 on Hear it from the pews holds the button, with the wait shown, until the wait ends", async () => {
    vi.useRealTimers(); // a second useFakeTimers call would keep beforeEach's Date-only fake
    vi.useFakeTimers({ toFake: ["Date", "setTimeout", "clearTimeout"], shouldAdvanceTime: true });
    vi.setSystemTime(DRAFT_NOW);
    let answer: PewsResult | { status: number } = fakeError(429, "rate_limited", "Too many requests. Try again in 30 seconds.", {
      details: { retry_after_seconds: 30 },
    });
    const { user, api } = renderStep(seeded(), { "POST /liturgy/pews": pewsRoute(() => answer) });
    await user.click(await screen.findByRole("button", { name: "Hear it from the pews" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Too many requests. Try again in 30 seconds.");
    const button = screen.getByRole("button", { name: "Hear it from the pews" });
    expect(button).toHaveAttribute("aria-disabled", "true");
    await user.click(button);
    expect(pewsRequests(api)).toHaveLength(1); // nothing sent during the wait
    answer = ANSWER;
    act(() => {
      vi.advanceTimersByTime(31_000);
    });
    expect(button).toBeEnabled();
    expect(screen.queryByRole("alert")).toBeNull(); // the wait is over, so its line goes
    await user.click(button);
    expect(await screen.findByText("From the pews: 3 reactions.")).toBeInTheDocument();
    expect(pewsRequests(api)).toHaveLength(2);
  });

  it("wraps long text at 375 px, with no em dash in its copy", async () => {
    const long = "w".repeat(400);
    const { user } = renderStep(seeded(), {
      "POST /liturgy/pews": pewsRoute(() => ({ voices: [{ description: `A ${long}`, reactions: [{ text: long, section: "opening_prayer", kind: "missed" }] }] })),
    });
    await user.click(await screen.findByRole("button", { name: "Hear it from the pews" }));
    const box = await screen.findByRole("region", { name: "From the pews" });
    expect(within(box).getByRole("heading", { name: `A ${long}` })).toHaveClass("[overflow-wrap:anywhere]");
    expect(within(box).getByText(long)).toHaveClass("min-w-0", "[overflow-wrap:anywhere]");
    expect(box).toHaveClass("min-w-0");
    expect(screen.getByRole("button", { name: "Hear it from the pews" }).parentElement).toHaveClass("flex-wrap");
    expect(box.textContent).not.toContain("\u2014");
  });
});

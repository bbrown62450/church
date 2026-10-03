/**
 * The Liturgy step (slice 4 spec, "User experience", Testing "dom"; F §4.6,
 * §4.8). The step runs inside the real builder layout against the fake API.
 * The clock is Tuesday, September 29, 2026 (only `Date` is faked), so a fresh
 * draft is dated Sunday, October 4, 2026 (a first Sunday), and the lectionary
 * answers "no readings", so the readings stay as each test seeds them.
 */
import { act, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import ReviewStepPage from "@/app/(signed-in)/(church)/builder/review/page";
import { Toaster } from "@/components/ui/sonner";
import type { GenerateLiturgyBody } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import { editOccasion, editScriptureLines, setDate, setPick } from "@/lib/draft/readings";
import { draftKey, type DraftV1, type SectionKey } from "@/lib/draft/schema";
import { editCardText } from "@/lib/liturgy/cards";
import { authEvents } from "@/lib/queries/auth-events";
import { keys } from "@/lib/queries/keys";
import { fakeError, installFakeApi, type FakeHandler, type FakeResponse, type RecordedRequest } from "@/test/fake-api";
import {
  bulletinSettings,
  church,
  CHURCH_IDS,
  churchProfile,
  DRAFT_NOW,
  generateRoute,
  gg2013,
  lectionaryRoute,
  liturgyConfig,
  me,
  sectionFailure,
  sectionResult,
  testDraft,
  USER_ID,
} from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { LiturgyStep } from "./liturgy-step";
import { UNDO_TOAST_MS } from "../hymns/use-undo-toasts";

import { STILL_WORKING } from "./use-still-working";
import { DEFAULT_BENEDICTION_FALLBACK } from "@/lib/liturgy/defaults";

const KEY = draftKey(USER_ID, church().id);
const [, , COME, , , , , , SENT] = gg2013();
const OCT_4 = "Isaiah 5:1-7\nPsalm 80:7-15\nPhilippians 3:4b-14\nMatthew 21:33-46";

function stored(): DraftV1 {
  return JSON.parse(window.localStorage.getItem(KEY) ?? "null") as DraftV1;
}

function withCard(key: SectionKey, patch: Partial<DraftV1["liturgy"]["cards"]["benediction"]>, d: DraftV1 = testDraft()): DraftV1 {
  return { ...d, liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, [key]: { ...d.liturgy.cards[key], ...patch } } } };
}

/** The step in the builder layout, with a Toaster for toast text; `routes` replace the defaults. */
function renderStep(draft: DraftV1 = testDraft(), routes: Record<string, FakeHandler> = {}, extra: ReactNode = null) {
  window.localStorage.setItem(KEY, JSON.stringify(draft));
  const api = installFakeApi({
    "GET /church": churchProfile(),
    "GET /lectionary/readings": lectionaryRoute(),
    "GET /liturgy/config": liturgyConfig(),
    "GET /church/bulletin-settings": bulletinSettings(),
    ...routes,
  });
  const view = renderWithProviders(
    <>
      <BuilderLayout>
        <LiturgyStep />
        {extra}
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

/** Each outline row: a card's title, or a landmark row's text. */
function outline(): string[] {
  const list = screen.getByRole("list", { name: "Order of worship" });
  return within(list)
    .getAllByRole("listitem")
    .map((li) => li.querySelector("h3")?.textContent ?? li.textContent ?? "");
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
  toast.dismiss(); // sonner replays a toast still showing to the next Toaster
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  window.location.hash = "";
});

describe("the Liturgy step (S User experience)", () => {
  it("shows the step's shape while the sections load, and Couldn't load the liturgy sections. with Retry when they fail", async () => {
    let fail = true;
    let release!: () => void;
    const gate = new Promise<void>((resolve) => (release = resolve));
    const { user } = renderStep(testDraft(), {
      "GET /liturgy/config": async () => {
        await gate;
        return fail ? fakeError(500, "internal_error", "Something went wrong.") : liturgyConfig();
      },
    });
    expect(await screen.findByRole("status", { name: "Loading the liturgy" })).toBeInTheDocument();
    release();
    expect(await screen.findByText("Couldn't load the liturgy sections.")).toBeInTheDocument();
    expect(screen.getByText("Something went wrong. (Ref: 4f9a2c1e)")).toBeInTheDocument();
    fail = false;
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("region", { name: "Call to Worship" })).toBeInTheDocument();
    expect(screen.queryByText("Couldn't load the liturgy sections.")).toBeNull();
  });

  it("lays out the order of worship as the Word files print it, with the draft's hymns, readings and title", async () => {
    const hymns = (d: DraftV1): DraftV1 => ({
      ...d,
      hymns: {
        ...d.hymns,
        slots: {
          opening: { hymn_id: COME.id, title: COME.title, number: COME.number, hymnal: "GG2013" },
          response: null,
          closing: { hymn_id: SENT.id, title: SENT.title, number: null, hymnal: "GG2013" },
        },
      },
    });
    const view = renderStep(hymns(editScriptureLines(testDraft(), OCT_4)));
    expect(await screen.findByRole("heading", { level: 2, name: "Liturgy" })).toBeInTheDocument();
    // No picks: the automatic readings, marked auto; the NT reading is never the Psalm.
    expect(outline()).toEqual([
      "Call to Worship",
      "Opening Prayer",
      "First Hymn · Come, Thou Almighty King",
      "Prayer of Confession",
      "Assurance of Pardon",
      "Prayer for Illumination",
      "First Reading · Isaiah 5:1-7 auto",
      "New Testament Reading · Philippians 3:4b-14 auto",
      "Sermon Title · [Sermon title]",
      "Affirmation of Faith · Apostles' Creed",
      "Second Hymn",
      "Include communion liturgy (The Sacrament of the Lord's Supper)",
      "Prayers of the People",
      "Offertory Prayer",
      "Third Hymn · Sent Forth by God's Blessing",
      "Benediction",
    ]);
    expect(screen.getByRole("link", { name: "First Hymn · Come, Thou Almighty King" })).toHaveAttribute("href", "/builder/hymns");
    expect(screen.getByRole("link", { name: "First Reading · Isaiah 5:1-7 auto" })).toHaveAttribute("href", "/builder/readings");
    view.unmount();

    // Explicit picks show without "auto"; a title shows as typed.
    const picked = setPick(setPick(editScriptureLines(testDraft(), OCT_4), "ot", "Isaiah 5:1-7"), "nt", "Matthew 21:33-46");
    renderStep({ ...picked, liturgy: { ...picked.liturgy, sermon_title: "Living Water" } });
    expect(await screen.findByRole("link", { name: "First Reading · Isaiah 5:1-7" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "New Testament Reading · Matthew 21:33-46" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sermon Title · Living Water" })).toBeInTheDocument();
  });

  it("writes what is typed to the draft as the user's text, and keeps it across a reload", async () => {
    const { user, unmount } = renderStep();
    const text = await screen.findByRole("textbox", { name: "Call to Worship" });
    expect(text).toHaveAttribute("placeholder", "Type your own text, or tap Generate.");
    expect(within(card("Call to Worship")).getByText("Empty")).toBeInTheDocument();
    await user.type(text, "Come, let us worship.");
    expect(within(card("Call to Worship")).getByText("Your text")).toBeInTheDocument();
    await waitFor(() =>
      expect(stored().liturgy.cards.call_to_worship).toEqual({ enabled: true, text: "Come, let us worship.", origin: "typed" }),
    );
    unmount();
    renderStep(stored());
    expect(await screen.findByRole("textbox", { name: "Call to Worship" })).toHaveValue("Come, let us worship.");
  });

  it("shows each section's hints and switches; a card switched off keeps its text and says so", async () => {
    const { user } = renderStep(withCard("opening_prayer", { text: "Gracious God", origin: "typed" }));
    await screen.findByRole("region", { name: "Call to Worship" });
    expect(within(card("Call to Worship")).getByText("Start lines with “Leader:” or “People:”. People lines print in bold.")).toBeInTheDocument();
    expect(within(card("Prayer of Confession")).getByText("Printed in bold for everyone to read together.")).toBeInTheDocument();
    expect(within(card("Assurance of Pardon")).getByText("People: Thanks be to God! Amen.")).toBeInTheDocument();
    expect(within(card("Assurance of Pardon")).getByText("Added automatically after your text.")).toBeInTheDocument();
    // The hints are the fields' descriptions.
    expect(screen.getByRole("textbox", { name: "Call to Worship" })).toHaveAccessibleDescription(
      "Start lines with “Leader:” or “People:”. People lines print in bold.",
    );
    expect(screen.getByRole("textbox", { name: "Assurance of Pardon" })).toHaveAccessibleDescription(
      "People: Thanks be to God! Amen. Added automatically after your text.",
    );
    const prayers = card("Prayers of the People");
    expect(within(prayers).getByText("Pastor's copy only")).toBeInTheDocument();
    expect(within(prayers).getByRole("switch", { name: "Include Prayers of the People" })).not.toBeChecked();
    expect(within(prayers).getByText("Off — not in the service. Any text is kept.")).toBeInTheDocument();
    expect(within(prayers).queryByRole("textbox")).toBeNull();

    const opening = card("Opening Prayer");
    await user.click(within(opening).getByRole("switch", { name: "Include Opening Prayer" }));
    expect(within(opening).queryByRole("textbox")).toBeNull();
    expect(within(opening).getByText("Off — not in the service. Any text is kept.")).toBeInTheDocument();
    await waitFor(() => expect(stored().liturgy.cards.opening_prayer).toEqual({ enabled: false, text: "Gracious God", origin: "typed" }));
    await user.click(within(opening).getByRole("switch", { name: "Include Opening Prayer" }));
    expect(within(opening).getByRole("textbox", { name: "Opening Prayer" })).toHaveValue("Gracious God");
  });

  it("shows the church's default benediction and follows it until edited; Use church default follows it again", async () => {
    const { user, queryClient } = renderStep();
    const benediction = await screen.findByRole("region", { name: "Benediction" });
    const text = within(benediction).getByRole("textbox", { name: "Benediction" });
    expect(text).toHaveValue(DEFAULT_BENEDICTION_FALLBACK);
    expect(within(benediction).getByText("Church default")).toBeInTheDocument();
    expect(within(benediction).getByText("Your church's default benediction. Admins can change it in Settings.")).toBeInTheDocument();
    // An admin changes the default (6a) and the profile refetches.
    act(() => queryClient.setQueryData(keys.churchProfile(church().id), churchProfile({ default_benediction: "The Lord bless you." })));
    await waitFor(() => expect(text).toHaveValue("The Lord bless you."));
    await user.clear(text);
    await user.type(text, "Go in peace.");
    expect(within(benediction).getByText("Your text")).toBeInTheDocument();
    expect(within(benediction).queryByText(/Your church's default benediction/)).toBeNull();
    act(() => queryClient.setQueryData(keys.churchProfile(church().id), churchProfile({ default_benediction: DEFAULT_BENEDICTION_FALLBACK })));
    await user.click(within(benediction).getByRole("button", { name: "More actions for Benediction" }));
    await user.click(await screen.findByRole("menuitem", { name: "Use church default" }));
    expect(text).toHaveValue(DEFAULT_BENEDICTION_FALLBACK);
    expect(within(benediction).getByText("Church default")).toBeInTheDocument();
    await waitFor(() => expect(stored().liturgy.cards.benediction).toEqual({ enabled: true, text: DEFAULT_BENEDICTION_FALLBACK, origin: "default" }));
  });

  it("Clear text empties a card with an Undo line; Undo brings the text back, and the line goes on the next edit", async () => {
    const { user } = renderStep(withCard("call_to_worship", { text: "Come.", origin: "typed" }));
    const cw = await screen.findByRole("region", { name: "Call to Worship" });
    expect(within(card("Opening Prayer")).getByRole("button", { name: "More actions for Opening Prayer" })).toBeDisabled();
    await user.click(within(cw).getByRole("button", { name: "More actions for Call to Worship" }));
    expect(screen.queryByRole("menuitem", { name: "Use church default" })).toBeNull();
    await user.click(await screen.findByRole("menuitem", { name: "Clear text" }));
    const text = within(cw).getByRole("textbox", { name: "Call to Worship" });
    expect(text).toHaveValue("");
    expect(within(cw).getByText("Empty")).toBeInTheDocument();
    expect(within(cw).getByText("Cleared.")).not.toHaveAttribute("aria-live");
    // Announced through the card's live region, which is there before the line appears.
    const announced = within(cw).getByText("Call to Worship: Cleared.", { selector: "[aria-live=polite]" });
    await user.click(within(cw).getByRole("button", { name: "Undo" }));
    expect(text).toHaveValue("Come.");
    expect(announced).toBeInTheDocument();
    expect(announced).toBeEmptyDOMElement();
    expect(within(cw).getByText("Your text")).toBeInTheDocument();
    expect(within(cw).queryByText("Cleared.")).toBeNull();
    await user.click(within(cw).getByRole("button", { name: "More actions for Call to Worship" }));
    await user.click(await screen.findByRole("menuitem", { name: "Clear text" }));
    await user.type(text, "Welcome");
    expect(within(cw).queryByText("Cleared.")).toBeNull();
    expect(within(cw).queryByRole("button", { name: "Undo" })).toBeNull();
  });

  it("writes the sermon title, shows it in the Sermon row, and the row focuses the field", async () => {
    const { user } = renderStep();
    const title = await screen.findByRole("textbox", { name: "Sermon title" });
    expect(title).toHaveAttribute("placeholder", "e.g. Living Water");
    expect(title).toHaveAttribute("maxLength", "300");
    expect(screen.getByText("Printed in the bulletin and the pastor's copy. If blank, both show “[Sermon title]”.")).toBeInTheDocument();
    await user.type(title, "Living Water");
    const row = screen.getByRole("button", { name: "Sermon Title · Living Water" });
    await waitFor(() => expect(stored().liturgy.sermon_title).toBe("Living Water"));
    await user.click(screen.getByRole("textbox", { name: "Call to Worship" }));
    await user.click(row);
    expect(title).toHaveFocus();
  });

  it("shows typed and AI text as text, never as markup, and counts characters past 18,000", async () => {
    let d = withCard("call_to_worship", { text: "<b>x</b>", origin: "typed" });
    d = withCard("opening_prayer", { text: "<i>AI</i> & more", origin: "ai" }, d);
    d = withCard("offertory_prayer", { text: "y".repeat(18_001), origin: "typed" }, d);
    d = withCard("prayer_of_confession", { text: "z".repeat(18_000), origin: "typed" }, d);
    renderStep({ ...d, liturgy: { ...d.liturgy, sermon_title: "<script>t</script>" } });
    expect(await screen.findByRole("textbox", { name: "Call to Worship" })).toHaveValue("<b>x</b>");
    expect(within(card("Opening Prayer")).getByRole("textbox")).toHaveValue("<i>AI</i> & more");
    expect(within(card("Opening Prayer")).getByText("AI draft")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sermon Title · <script>t</script>" })).toBeInTheDocument();
    expect(document.querySelector("b, i, script")).toBeNull();
    expect(within(card("Offertory Prayer")).getByText("18,001 / 20,000")).toBeInTheDocument();
    expect(within(card("Offertory Prayer")).getByRole("textbox")).toHaveAttribute("maxLength", "20000");
    expect(within(card("Prayer of Confession")).queryByText(/\/ 20,000/)).toBeNull();
  });

  it("hides the step footer below md while a text field has focus, and shows it again on blur (owner answer 3)", async () => {
    renderStep();
    const text = await screen.findByRole("textbox", { name: "Call to Worship" });
    const footer = screen.getByRole("navigation", { name: "Step navigation" });
    expect(footer).not.toHaveAttribute("data-keyboard-open");
    act(() => text.focus());
    expect(footer).toHaveAttribute("data-keyboard-open");
    expect(footer.className).toContain("max-md:hidden");
    act(() => text.blur());
    expect(footer).not.toHaveAttribute("data-keyboard-open");
    act(() => screen.getByRole("textbox", { name: "Sermon title" }).focus());
    expect(footer).toHaveAttribute("data-keyboard-open");
  });

  it("scrolls to the card the address names, as Review's links do", async () => {
    window.location.hash = "#card-assurance";
    const scroll = vi.spyOn(Element.prototype, "scrollIntoView");
    renderStep();
    await screen.findByRole("region", { name: "Assurance of Pardon" });
    await waitFor(() => expect(scroll).toHaveBeenCalled());
    expect(scroll.mock.contexts[0]).toBe(document.getElementById("card-assurance"));
  });

  it("scrolls nowhere, and still shows the step, when the address is malformed (M4)", async () => {
    window.location.hash = "#card-%E0";
    const scroll = vi.spyOn(Element.prototype, "scrollIntoView");
    renderStep();
    expect(await screen.findByRole("region", { name: "Assurance of Pardon" })).toBeInTheDocument();
    // The scroll effect runs in the commit that shows the cards; the sermon title field is there by then too.
    expect(screen.getByRole("textbox", { name: "Sermon title" })).toBeInTheDocument();
    expect(scroll).not.toHaveBeenCalled();
  });
});

describe("the card's own draft (S Card origin transitions)", () => {
  it("never shows another card's edit, and a typed card keeps its origin when switched", async () => {
    const d = editCardText(testDraft(), "assurance", "You are forgiven.");
    const { user } = renderStep(d);
    const assurance = await screen.findByRole("region", { name: "Assurance of Pardon" });
    await user.click(within(assurance).getByRole("switch", { name: "Include Assurance of Pardon" }));
    await user.click(within(assurance).getByRole("switch", { name: "Include Assurance of Pardon" }));
    expect(within(assurance).getByText("Your text")).toBeInTheDocument();
    expect(within(card("Call to Worship")).getByText("Empty")).toBeInTheDocument();
  });
});

// --- slice 4b T9: Generate, Regenerate and the AI bar ---------------------------------

/** A `POST /liturgy/generate` handler that answers each section only when the test releases it. */
function heldGenerate() {
  const waiting = new Map<string, (answer: FakeResponse | undefined) => void>();
  const sent: string[] = [];
  let open = 0;
  let most = 0;
  const handler = async (req: RecordedRequest) => {
    const section = (req.body as GenerateLiturgyBody).sections[0];
    sent.push(section);
    open += 1;
    most = Math.max(most, open);
    const answer = await new Promise<FakeResponse | undefined>((resolve) => waiting.set(section, resolve));
    open -= 1;
    return answer ?? { results: [sectionResult(section, `New ${section}`)] };
  };
  return {
    handler,
    sent,
    most: () => most,
    /** Answers `section` (by default "New {section}"), once its request has arrived. */
    release: async (section: SectionKey, answer?: FakeResponse) => {
      await waitFor(() => expect(waiting.has(section)).toBe(true));
      waiting.get(section)?.(answer);
      waiting.delete(section);
    },
  };
}

const generateCalls = (requests: RecordedRequest[]) => requests.filter((r) => r.path === "/liturgy/generate");

/**
 * A card's error, whether it came as an alert (the card's own run) or
 * quietly (a bulk run announces its errors politely, not as one alert each).
 */
function errorIn(label: string): HTMLElement | null {
  return card(label).querySelector<HTMLElement>('[data-slot="alert"]');
}

/** The AI bar's button is off with `aria-disabled`, never `disabled`, so it keeps focus (T1-T10 review). */
function expectBarOff(button: HTMLElement, off = true) {
  expect(button).not.toHaveAttribute("disabled");
  if (off) expect(button).toHaveAttribute("aria-disabled", "true");
  else expect(button).not.toHaveAttribute("aria-disabled", "true");
}

describe("Generate and Regenerate (S Generate and Regenerate, AI bar)", () => {
  it("Generate sends one section as the church, no overrides, and writes an AI draft with no toast", async () => {
    const { user, api } = renderStep();
    const cw = await screen.findByRole("region", { name: "Call to Worship" });
    api.set("POST /liturgy/generate", generateRoute());
    await user.click(within(cw).getByRole("button", { name: "Generate" }));
    expect(await within(cw).findByText("AI draft")).toBeInTheDocument();
    expect(within(cw).getByRole("textbox", { name: "Call to Worship" })).toHaveValue("Call to Worship written by the AI.");
    const [call] = generateCalls(api.requests);
    expect(call.headers["X-Church-Id"]).toBe(church().id);
    expect(call.body).toEqual({ occasion: "", scriptures: [], hymns: { opening: null, response: null, closing: null }, sections: ["call_to_worship"] });
    expect(generateCalls(api.requests)).toHaveLength(1);
    expect(within(cw).queryByText(/Replaced/)).toBeNull(); // nothing was replaced
    expect(screen.queryByText(/^Wrote/)).toBeNull();
    await waitFor(() => expect(stored().liturgy.cards.call_to_worship.origin).toBe("ai"));
  });

  it("Generate empty sections writes only switched-on empty cards, 3 at a time, and ends with one toast", async () => {
    const held = heldGenerate();
    const d = withCard("call_to_worship", { text: "Come, let us worship.", origin: "typed" }, withCard("assurance", { enabled: false }));
    const { user } = renderStep(d, { "POST /liturgy/generate": held.handler });
    const bar = await screen.findByRole("region", { name: "Write with AI" });
    expect(within(bar).getByText("Only switched-on sections with no text are written. Text you typed is never changed.")).toBeInTheDocument();
    await user.click(within(bar).getByRole("button", { name: "Generate empty sections (4)" }));
    expect(await within(bar).findByText("Writing 1 of 4…")).toBeInTheDocument();
    expect(within(bar).getByRole("button", { name: "Cancel" })).toBeInTheDocument();
    await waitFor(() => expect(held.sent).toHaveLength(3));
    expect(within(card("Offertory Prayer")).getByRole("button", { name: "Waiting…" })).toBeDisabled();
    await held.release("opening_prayer");
    expect(await within(bar).findByText("Writing 2 of 4…")).toBeInTheDocument();
    for (const key of ["prayer_of_confession", "prayer_for_illumination", "offertory_prayer"] as const) await held.release(key);
    expect(await screen.findByText("Wrote 4 sections.")).toBeInTheDocument();
    expect(held.sent).toEqual(["opening_prayer", "prayer_of_confession", "prayer_for_illumination", "offertory_prayer"]);
    expect(held.most()).toBe(3);
    // Typed text, a card that is off and the Benediction's default are never sent or changed.
    expect(screen.getByRole("textbox", { name: "Call to Worship" })).toHaveValue("Come, let us worship.");
    expect(screen.getByRole("textbox", { name: "Benediction" })).toHaveValue(DEFAULT_BENEDICTION_FALLBACK);
    expectBarOff(within(bar).getByRole("button", { name: "Generate empty sections (0)" }));
    expect(within(bar).getByText("Every switched-on section has text. Use Regenerate on a card for a new AI draft.")).toBeInTheDocument();
  });

  it("Regenerate on the user's text asks first; Keep my text sends nothing, Replace text replaces it with Undo", async () => {
    const { user, api } = renderStep(withCard("opening_prayer", { text: "Gracious God", origin: "typed" }), {
      "POST /liturgy/generate": generateRoute(),
    });
    const op = await screen.findByRole("region", { name: "Opening Prayer" });
    await user.click(within(op).getByRole("button", { name: "Regenerate" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Replace your text?" });
    expect(within(dialog).getByText("Regenerate replaces the text in Opening Prayer with a new AI draft. You can undo right after.")).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Keep my text" }));
    expect(generateCalls(api.requests)).toHaveLength(0);
    await user.click(within(op).getByRole("button", { name: "Regenerate" }));
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Replace text" }));
    const text = within(op).getByRole("textbox", { name: "Opening Prayer" });
    await waitFor(() => expect(text).toHaveValue("Opening Prayer written by the AI."));
    expect(within(op).getByText("Replaced with a new AI draft.")).toBeInTheDocument();
    await user.click(within(op).getByRole("button", { name: "Undo" }));
    expect(text).toHaveValue("Gracious God");
    expect(within(op).getByText("Your text")).toBeInTheDocument();
    // An AI draft is regenerated without asking.
    await user.click(within(op).getByRole("button", { name: "Regenerate" }));
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Replace text" }));
    await waitFor(() => expect(text).toHaveValue("Opening Prayer written by the AI."));
    await user.click(within(op).getByRole("button", { name: "Regenerate" }));
    await waitFor(() => expect(generateCalls(api.requests)).toHaveLength(3));
    expect(screen.queryByRole("alertdialog")).toBeNull();
  });

  // Heavy: six cards answer in one run, then a retry; near Vitest's 5 s default on a busy machine.
  it("shows each error on its card only, never in the draft, with Try again where it can help", { timeout: 10_000 }, async () => {
    let timeoutOnce = true;
    const answers: Partial<Record<SectionKey, () => FakeResponse | ReturnType<typeof sectionResult>>> = {
      call_to_worship: () =>
        timeoutOnce
          ? ((timeoutOnce = false), sectionFailure("call_to_worship", "ai_timeout", "The AI took too long to answer. Try again."))
          : sectionResult("call_to_worship", "Leader: Come!"),
      opening_prayer: () =>
        sectionFailure(
          "opening_prayer",
          "prompt_invalid",
          "The Opening Prayer prompt in Settings has a problem: Placeholders need a name, such as {occasion}. An admin can fix it under Settings → Liturgy prompts.",
        ),
      prayer_of_confession: () =>
        fakeError(404, "not_found", "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step."),
      assurance: () => fakeError(500, "internal_error", "Something went wrong."),
      prayer_for_illumination: () => sectionFailure("prayer_for_illumination", "ai_not_configured", "AI not configured. Type this section yourself."),
    };
    const { user } = renderStep(testDraft(), {
      "POST /liturgy/generate": generateRoute((section) => answers[section]?.() ?? sectionResult(section, `New ${section}`)),
    });
    const bar = await screen.findByRole("region", { name: "Write with AI" });
    await user.click(within(bar).getByRole("button", { name: "Generate empty sections (6)" }));
    expect(await screen.findByText("Wrote 1 of 6 sections. The rest show what went wrong.")).toBeInTheDocument();
    const alertIn = (label: string) => errorIn(label) as HTMLElement;
    expect(alertIn("Call to Worship")).toHaveTextContent("The AI took too long to answer. Try again.");
    // A bulk run's errors are announced politely, not as six alerts; each is linked to its card's text.
    expect(screen.queryByRole("alert")).toBeNull();
    expect(within(card("Call to Worship")).getByText("The AI took too long to answer. Try again.", { selector: "[aria-live=polite]" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Call to Worship" })).toHaveAccessibleDescription(/The AI took too long to answer\. Try again\./);
    expect(within(alertIn("Opening Prayer")).queryByRole("button", { name: "Try again" })).toBeNull();
    expect(within(alertIn("Prayer of Confession")).getByRole("link", { name: "Go to Hymns" })).toHaveAttribute("href", "/builder/hymns");
    expect(within(alertIn("Prayer of Confession")).queryByRole("button", { name: "Try again" })).toBeNull();
    expect(alertIn("Assurance of Pardon")).toHaveTextContent("Something went wrong. (Ref: 4f9a2c1e)");
    expect(alertIn("Prayer for Illumination")).toHaveTextContent("AI not configured. Type this section yourself.");
    expect(screen.getByRole("textbox", { name: "Call to Worship" })).toHaveValue(""); // the text is unchanged
    await waitFor(() => expect(stored().liturgy.cards.offertory_prayer.text).toBe("New offertory_prayer"));
    expect(window.localStorage.getItem(KEY)).not.toMatch(/took too long|has a problem|no longer in your hymnal|went wrong|not configured/);
    await user.click(within(alertIn("Call to Worship")).getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Call to Worship" })).toHaveValue("Leader: Come!"));
    expect(errorIn("Call to Worship")).toBeNull();
  });

  it("without AI sends nothing: empty cards say so, Regenerate is off, and the banner explains", async () => {
    const d = withCard("opening_prayer", { text: "Gracious God", origin: "typed" }, withCard("assurance", { enabled: false }));
    const { user, api } = renderStep(d, { "GET /liturgy/config": liturgyConfig({ ai_available: false }) });
    const bar = await screen.findByRole("region", { name: "Write with AI" });
    expect(within(bar).getByText("AI writing isn't set up for this app. Type each section yourself — everything else works as usual.")).toBeInTheDocument();
    await user.click(within(card("Call to Worship")).getByRole("button", { name: "Generate" }));
    expect(within(card("Call to Worship")).getByRole("alert")).toHaveTextContent("AI not configured. Type this section yourself.");
    await user.click(within(bar).getByRole("button", { name: "Generate empty sections (4)" }));
    const marked = ["Call to Worship", "Prayer of Confession", "Prayer for Illumination", "Offertory Prayer"];
    for (const label of marked) {
      expect(errorIn(label)).toHaveTextContent("AI not configured. Type this section yourself.");
      // Not announced once per card: the banner already says it.
      expect(within(card(label)).queryByText("AI not configured. Type this section yourself.", { selector: "[aria-live=polite]" })).toBeNull();
    }
    expect(screen.queryByRole("alert")).toBeNull();
    for (const label of ["Opening Prayer", "Assurance of Pardon", "Prayers of the People", "Benediction"]) {
      expect(errorIn(label)).toBeNull();
    }
    const op = card("Opening Prayer");
    expect(within(op).getByRole("button", { name: "Regenerate" })).toBeDisabled();
    expect(within(op).getByText("AI isn't set up")).toBeInTheDocument();
    expect(within(op).getByRole("textbox", { name: "Opening Prayer" })).toHaveValue("Gracious God");
    expect(within(op).getByText("Your text")).toBeInTheDocument();
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(generateCalls(api.requests)).toHaveLength(0);
    expect(screen.queryByText(/^Wrote/)).toBeNull();
  });

  // Heavy: three runs, one of them a bulk run of six with five answers; near Vitest's 5 s default on a busy machine.
  it("Cancel, switching a running card off, and typing in a queued card all stop it silently", { timeout: 10_000 }, async () => {
    const held = heldGenerate();
    const { user } = renderStep(testDraft(), { "POST /liturgy/generate": held.handler });
    const cw = await screen.findByRole("region", { name: "Call to Worship" });
    await user.click(within(cw).getByRole("button", { name: "Generate" }));
    expect(await within(cw).findByRole("button", { name: "Writing…" })).toHaveAttribute("aria-disabled", "true");
    expect(within(cw).getByRole("textbox", { name: "Call to Worship" })).toHaveAttribute("readonly");
    expect(within(cw).getByRole("button", { name: "More actions for Call to Worship" })).toBeDisabled();
    await user.click(within(cw).getByRole("button", { name: "Cancel Call to Worship" }));
    expect(within(cw).getByRole("button", { name: "Generate" })).toBeEnabled();
    await held.release("call_to_worship");

    const op = card("Opening Prayer");
    await user.click(within(op).getByRole("button", { name: "Generate" }));
    await within(op).findByRole("button", { name: "Writing…" });
    await user.click(within(op).getByRole("switch", { name: "Include Opening Prayer" }));
    await user.click(within(op).getByRole("switch", { name: "Include Opening Prayer" }));
    expect(within(op).getByRole("button", { name: "Generate" })).toBeEnabled(); // not restarted
    await held.release("opening_prayer");

    await user.click(screen.getByRole("button", { name: "Generate empty sections (6)" }));
    const assurance = card("Assurance of Pardon");
    expect(await within(assurance).findByRole("button", { name: "Waiting…" })).toBeDisabled();
    await user.type(within(assurance).getByRole("textbox", { name: "Assurance of Pardon" }), "You are forgiven.");
    for (const key of ["call_to_worship", "opening_prayer", "prayer_of_confession", "prayer_for_illumination", "offertory_prayer"] as const) {
      await held.release(key);
    }
    expect(await screen.findByText("Wrote 5 sections.")).toBeInTheDocument();
    expect(held.sent).not.toContain("assurance");
    expect(within(assurance).getByRole("textbox", { name: "Assurance of Pardon" })).toHaveValue("You are forgiven.");
    // The cancelled runs' answers were never applied, and no card shows an error.
    expect(screen.getByRole("textbox", { name: "Call to Worship" })).toHaveValue("New call_to_worship");
    expect(screen.queryByRole("alert")).toBeNull();
  });

  // Heavy: three runs, a New service, a 400 ms draft write and a profile change; near Vitest's 5 s default.
  it("drops a run for a replaced service or a result for an edit from another tab, and applies one to a card following the default", { timeout: 10_000 }, async () => {
    const held = heldGenerate();
    const { user, queryClient } = renderStep(testDraft(), { "POST /liturgy/generate": held.handler });
    const cw = await screen.findByRole("region", { name: "Call to Worship" });
    // New service while a run goes: the draft is replaced (a new created_at), and the run stops silently.
    await user.click(within(cw).getByRole("button", { name: "Generate" }));
    await within(cw).findByRole("button", { name: "Writing…" });
    vi.setSystemTime(new Date(DRAFT_NOW.getTime() + 60_000)); // the new draft's created_at differs
    await user.click(screen.getByRole("button", { name: "More actions" }));
    await user.click(await screen.findByRole("menuitem", { name: "New service" }));
    expect(await within(card("Call to Worship")).findByRole("button", { name: "Generate" })).toBeEnabled();
    await held.release("call_to_worship");
    expect(screen.getByRole("textbox", { name: "Call to Worship" })).toHaveValue("");

    // An edit from another tab while it writes.
    await user.click(within(card("Opening Prayer")).getByRole("button", { name: "Generate" }));
    await within(card("Opening Prayer")).findByRole("button", { name: "Writing…" });
    // The other tab edits the new service (written 400 ms after New service).
    await waitFor(() => expect(stored().created_at).toBe(new Date(DRAFT_NOW.getTime() + 60_000).toISOString()));
    const theirs = withCard("opening_prayer", { text: "From the other tab", origin: "typed" }, stored());
    act(() => {
      window.dispatchEvent(
        new StorageEvent("storage", { key: KEY, newValue: JSON.stringify({ ...theirs, updated_at: "2026-09-29T17:00:00.000Z" }) }),
      );
    });
    await held.release("opening_prayer");
    expect(await screen.findByText("Kept your edits — the new AI draft for Opening Prayer was not used.")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Opening Prayer" })).toHaveValue("From the other tab");
    // The New service run was dropped without a toast, and its answer never landed.
    expect(screen.queryByText(/The service changed/)).toBeNull();
    expect(screen.getByRole("textbox", { name: "Call to Worship" })).toHaveValue("");

    // Regenerate a Benediction following the default; the default changes mid-run.
    const bn = card("Benediction");
    await user.click(within(bn).getByRole("button", { name: "Regenerate" }));
    await within(bn).findByRole("button", { name: "Writing…" });
    act(() => queryClient.setQueryData(keys.churchProfile(church().id), churchProfile({ default_benediction: "Go in peace." })));
    await waitFor(() => expect(within(bn).getByRole("textbox", { name: "Benediction" })).toHaveValue("Go in peace."));
    await held.release("benediction");
    await waitFor(() => expect(within(bn).getByRole("textbox", { name: "Benediction" })).toHaveValue("New benediction"));
    expect(within(bn).getByText("AI draft")).toBeInTheDocument();
    await user.click(within(bn).getByRole("button", { name: "Undo" }));
    expect(within(bn).getByRole("textbox", { name: "Benediction" })).toHaveValue("Go in peace.");
    expect(within(bn).getByText("Church default")).toBeInTheDocument();
  });

  // Heavy: a bulk run of six, an error, New service and one more run; near Vitest's 5 s default on a busy machine.
  it("New service during a bulk run drops every run with one toast and clears the cards' errors and Undo", { timeout: 10_000 }, async () => {
    const held = heldGenerate();
    const { user } = renderStep(withCard("call_to_worship", { text: "Come.", origin: "typed" }), { "POST /liturgy/generate": held.handler });
    const cw = await screen.findByRole("region", { name: "Call to Worship" });
    await user.click(within(cw).getByRole("button", { name: "More actions for Call to Worship" }));
    await user.click(await screen.findByRole("menuitem", { name: "Clear text" }));
    expect(within(cw).getByText("Cleared.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Generate empty sections (6)" }));
    await waitFor(() => expect(held.sent).toHaveLength(3));
    // While the card runs its Undo is hidden, so Undo cannot change the text the run will replace.
    expect(within(cw).queryByText("Cleared.")).toBeNull();
    await held.release("call_to_worship", fakeError(500, "internal_error", "Something went wrong."));
    await waitFor(() => expect(errorIn("Call to Worship")).toHaveTextContent("Something went wrong. (Ref: 4f9a2c1e)"));
    expect(within(cw).getByText("Cleared.")).toBeInTheDocument(); // back once the run has ended
    await waitFor(() => expect(held.sent).toHaveLength(4));
    vi.setSystemTime(new Date(DRAFT_NOW.getTime() + 60_000)); // the new draft's created_at differs
    await user.click(screen.getByRole("button", { name: "More actions" }));
    await user.click(await screen.findByRole("menuitem", { name: "New service" }));
    expect(await screen.findByText("The service changed, so the AI drafts were discarded.")).toBeInTheDocument();
    expectBarOff(screen.getByRole("button", { name: "Generate empty sections (6)" }), false);
    expect(errorIn("Call to Worship")).toBeNull();
    expect(within(card("Call to Worship")).queryByText("Cleared.")).toBeNull();
    // The answers still on their way land nowhere; a new run works as usual.
    await held.release("opening_prayer");
    await held.release("prayer_of_confession");
    await user.click(within(card("Offertory Prayer")).getByRole("button", { name: "Generate" }));
    await held.release("offertory_prayer");
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Offertory Prayer" })).toHaveValue("New offertory_prayer"));
    expect(screen.getByRole("textbox", { name: "Opening Prayer" })).toHaveValue("");
    expect(screen.queryByText(/^Wrote/)).toBeNull();
    expect(screen.queryByText(/The service changed, so the AI draft for/)).toBeNull();
    expect(held.sent).toEqual(["call_to_worship", "opening_prayer", "prayer_of_confession", "assurance", "offertory_prayer"]);
  });

  it("keeps focus on the card when its control goes: Replace text, Cancel, Keep my text, an error, Try again, Clear and Undo", async () => {
    const held = heldGenerate();
    const { user } = renderStep(withCard("opening_prayer", { text: "Gracious God", origin: "typed" }), { "POST /liturgy/generate": held.handler });
    const op = await screen.findByRole("region", { name: "Opening Prayer" });
    // Replace text: Regenerate is gone while the card runs, so the card's Cancel takes focus.
    await user.click(within(op).getByRole("button", { name: "Regenerate" }));
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Replace text" }));
    await waitFor(() => expect(within(op).getByRole("button", { name: "Cancel Opening Prayer" })).toHaveFocus());
    await user.click(within(op).getByRole("button", { name: "Cancel Opening Prayer" }));
    expect(within(op).getByRole("button", { name: "Regenerate" })).toHaveFocus();
    await user.click(within(op).getByRole("button", { name: "Regenerate" }));
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Keep my text" }));
    await waitFor(() => expect(within(op).getByRole("button", { name: "Regenerate" })).toHaveFocus());
    // Try again: its alert goes, so the card's Cancel.
    const cw = card("Call to Worship");
    await user.click(within(cw).getByRole("button", { name: "Generate" }));
    await waitFor(() => expect(within(cw).getByRole("button", { name: "Cancel Call to Worship" })).toHaveFocus());
    await held.release("call_to_worship", {
      status: 200,
      body: { results: [sectionFailure("call_to_worship", "ai_timeout", "The AI took too long to answer. Try again.")] },
    });
    // The error replaces the row whose Cancel had focus: its Try again takes it.
    const retry = within(await within(cw).findByRole("alert")).getByRole("button", { name: "Try again" });
    await waitFor(() => expect(retry).toHaveFocus());
    await user.click(retry);
    await waitFor(() => expect(within(cw).getByRole("button", { name: "Cancel Call to Worship" })).toHaveFocus());
    // Clear: the ⋯ menu is off on an empty card, so "Cleared. Undo"; Undo: the card's heading.
    await user.click(within(op).getByRole("button", { name: "More actions for Opening Prayer" }));
    await user.click(await screen.findByRole("menuitem", { name: "Clear text" }));
    await waitFor(() => expect(within(op).getByRole("button", { name: "Undo" })).toHaveFocus());
    await user.click(within(op).getByRole("button", { name: "Undo" }));
    expect(within(op).getByRole("heading", { name: "Opening Prayer" })).toHaveFocus();
  });

  it("keeps focus on the card when a run ends without text and nothing can be tried again", async () => {
    const held = heldGenerate();
    const { user } = renderStep(testDraft(), { "POST /liturgy/generate": held.handler });
    const cw = await screen.findByRole("region", { name: "Call to Worship" });
    await user.click(within(cw).getByRole("button", { name: "Generate" }));
    await waitFor(() => expect(within(cw).getByRole("button", { name: "Cancel Call to Worship" })).toHaveFocus());
    await held.release("call_to_worship", {
      status: 200,
      body: { results: [sectionFailure("call_to_worship", "ai_not_configured", "AI not configured. Type this section yourself.")] },
    });
    await waitFor(() => expect(errorIn("Call to Worship")).toHaveTextContent("AI not configured. Type this section yourself."));
    expect(within(errorIn("Call to Worship") as HTMLElement).queryByRole("button", { name: "Try again" })).toBeNull();
    // Cancel went with the run; the card's new Generate takes focus, not the page.
    await waitFor(() => expect(within(cw).getByRole("button", { name: "Generate" })).toHaveFocus());
    expect(document.body).not.toHaveFocus();
  });

  it("keeps a 429's wait when the member leaves the step and comes back, and the AI bar waits too", async () => {
    const view = renderStep(testDraft(), {
      "POST /liturgy/generate": fakeError(429, "rate_limited", "Too many requests. Try again in 30 seconds.", {
        details: { retry_after_seconds: 30 },
      }),
    });
    await view.user.click(within(await screen.findByRole("region", { name: "Offertory Prayer" })).getByRole("button", { name: "Generate" }));
    expect(within(await within(card("Offertory Prayer")).findByRole("alert")).getByRole("button", { name: "Try again" })).toBeDisabled();
    expectBarOff(screen.getByRole("button", { name: "Generate empty sections (6)" }));
    const page = (step: ReactNode) => (
      <>
        <BuilderLayout>{step}</BuilderLayout>
        <Toaster />
      </>
    );
    view.rerender(page(<ReviewStepPage />));
    expect(screen.queryByRole("region", { name: "Offertory Prayer" })).toBeNull();
    view.rerender(page(<LiturgyStep />));
    // Back at once: the wait goes on (it is not restarted, nor over).
    expect(within(await within(await screen.findByRole("region", { name: "Offertory Prayer" })).findByRole("alert")).getByRole("button", { name: "Try again" })).toBeDisabled();
    view.rerender(page(<ReviewStepPage />));
    vi.setSystemTime(new Date(DRAFT_NOW.getTime() + 30_000)); // the 30 s pass while the member is away
    view.rerender(page(<LiturgyStep />));
    const offertory = await screen.findByRole("region", { name: "Offertory Prayer" });
    expect(within(within(offertory).getByRole("alert")).getByRole("button", { name: "Try again" })).toBeEnabled();
    expectBarOff(screen.getByRole("button", { name: "Generate empty sections (6)" }), false);
  });

  it("keeps writing while the member is on another step, and the result is there on return", async () => {
    const held = heldGenerate();
    const view = renderStep(testDraft(), { "POST /liturgy/generate": held.handler });
    const cw = await screen.findByRole("region", { name: "Call to Worship" });
    await view.user.click(within(cw).getByRole("button", { name: "Generate" }));
    await within(cw).findByRole("button", { name: "Writing…" });
    const page = (step: ReactNode) => (
      <>
        <BuilderLayout>{step}</BuilderLayout>
        <Toaster />
      </>
    );
    view.rerender(page(<ReviewStepPage />));
    expect(screen.queryByRole("region", { name: "Call to Worship" })).toBeNull();
    await held.release("call_to_worship");
    await waitFor(() => expect(stored().liturgy.cards.call_to_worship.text).toBe("New call_to_worship"));
    view.rerender(page(<LiturgyStep />));
    expect(await screen.findByRole("textbox", { name: "Call to Worship" })).toHaveValue("New call_to_worship");
  });

  // Heavy: a bulk run of six and four cards' alerts; near Vitest's 5 s default on a busy machine.
  it("stops the queue on a 429: that card and every waiting one show the wait", { timeout: 10_000 }, async () => {
    const held = heldGenerate();
    const { user } = renderStep(testDraft(), { "POST /liturgy/generate": held.handler });
    await user.click(await screen.findByRole("button", { name: "Generate empty sections (6)" }));
    await waitFor(() => expect(held.sent).toHaveLength(3));
    expect(screen.getByRole("button", { name: "Cancel" })).toHaveFocus(); // the same button, so focus stays
    await held.release(
      "call_to_worship",
      fakeError(429, "rate_limited", "Too many requests. Try again in 30 seconds.", { details: { retry_after_seconds: 30 } }),
    );
    for (const label of ["Call to Worship", "Assurance of Pardon", "Prayer for Illumination", "Offertory Prayer"]) {
      await waitFor(() => expect(errorIn(label)).toHaveTextContent("Too many requests — try again in 30 s."));
      expect(within(errorIn(label) as HTMLElement).getByRole("button", { name: "Try again" })).toBeDisabled();
    }
    await held.release("opening_prayer");
    await held.release("prayer_of_confession");
    expect(await screen.findByText("Wrote 2 of 6 sections. The rest show what went wrong.")).toBeInTheDocument();
    expect(held.sent).toEqual(["call_to_worship", "opening_prayer", "prayer_of_confession"]);
    // The AI bar waits as well, and keeps focus while it does.
    expectBarOff(screen.getByRole("button", { name: "Generate empty sections (4)" }));
    expect(screen.getByRole("button", { name: "Generate empty sections (4)" })).toHaveFocus();
    await user.click(screen.getByRole("button", { name: "Generate empty sections (4)" }));
    expect(held.sent).toHaveLength(3); // its click does nothing while it waits
  });

  it("enables Try again once a 429's wait has passed", async () => {
    const { user } = renderStep(testDraft(), {
      "POST /liturgy/generate": fakeError(429, "rate_limited", "Too many requests. Try again in 1 seconds.", {
        details: { retry_after_seconds: 1 },
      }),
    });
    await user.click(within(await screen.findByRole("region", { name: "Offertory Prayer" })).getByRole("button", { name: "Generate" }));
    const retry = within(await within(card("Offertory Prayer")).findByRole("alert")).getByRole("button", { name: "Try again" });
    expect(retry).toBeDisabled();
    await waitFor(() => expect(retry).toBeEnabled(), { timeout: 2_000 });
  });

  it("a 401 or a lost church goes to the app's handling and shows nothing on the card", async () => {
    const events: string[] = [];
    const off = [
      authEvents.onSignOutRequired(() => events.push("signOutRequired")),
      authEvents.onChurchAccessLost((id) => events.push(`lost:${id}`)),
    ];
    const { user, api } = renderStep();
    const cw = await screen.findByRole("region", { name: "Call to Worship" });
    api.set("POST /liturgy/generate", fakeError(401, "unauthenticated", "Please sign in."));
    await user.click(within(cw).getByRole("button", { name: "Generate" }));
    await waitFor(() => expect(events).toEqual(["signOutRequired"]));
    api.set("POST /liturgy/generate", fakeError(403, "forbidden", "No access.", { details: { reason: "no_church_access" } }));
    await user.click(within(cw).getByRole("button", { name: "Generate" }));
    await waitFor(() => expect(events).toEqual(["signOutRequired", `lost:${church().id}`]));
    expect(within(cw).queryByRole("alert")).toBeNull();
    for (const stop of off) stop();
  });

  it("says Still working after 8 s on the card and in the bar", async () => {
    vi.useRealTimers(); // a second useFakeTimers call would keep beforeEach's Date-only fake
    vi.useFakeTimers({ toFake: ["Date", "setTimeout", "clearTimeout"], shouldAdvanceTime: true });
    vi.setSystemTime(DRAFT_NOW);
    const held = heldGenerate();
    const { user } = renderStep(testDraft(), { "POST /liturgy/generate": held.handler });
    await user.click(await screen.findByRole("button", { name: "Generate empty sections (6)" }));
    await within(card("Call to Worship")).findByRole("button", { name: "Writing…" });
    expect(screen.queryByText(STILL_WORKING)).toBeNull();
    act(() => {
      vi.advanceTimersByTime(8_000);
    });
    expect(within(card("Call to Worship")).getByText(STILL_WORKING)).toHaveAttribute("aria-live", "polite");
    expect(screen.getByText(`Writing 1 of 6… ${STILL_WORKING}`)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expectBarOff(screen.getByRole("button", { name: "Generate empty sections (6)" }), false);
    expect(screen.queryByText(STILL_WORKING)).toBeNull();
  });

  it("notes when AI text will be general, and when every section is off", async () => {
    const view = renderStep();
    const { user } = view;
    const bar = await screen.findByRole("region", { name: "Write with AI" });
    expect(within(bar).getByText(/No occasion or readings yet, so AI text will be general\./)).toBeInTheDocument();
    expect(within(bar).getByRole("link", { name: "Date & readings" })).toHaveAttribute("href", "/builder/readings");
    expect(within(bar).queryByText(/All liturgy sections are switched off/)).toBeNull();
    for (const label of ["Call to Worship", "Opening Prayer", "Prayer of Confession", "Assurance of Pardon", "Prayer for Illumination", "Offertory Prayer", "Benediction"]) {
      await user.click(within(card(label)).getByRole("switch", { name: `Include ${label}` }));
    }
    expect(
      within(bar).getByText(
        "All liturgy sections are switched off. The Word files will list only hymns, readings, the sermon title and any custom elements.",
      ),
    ).toBeInTheDocument();
    view.unmount();
    renderStep(editOccasion(testDraft(), "Harvest Home"));
    expect(await screen.findByRole("button", { name: "Generate empty sections (6)" })).toBeInTheDocument();
    expect(screen.queryByText(/No occasion or readings yet/)).toBeNull();
  });
});

// --- slice 4b T10: communion and custom elements ------------------------------------------

/** Moves the draft's date, as Date & readings would (the communion default follows it). */
function MoveDate() {
  const { update } = useDraft();
  return (
    <button type="button" onClick={() => update((d) => setDate(d, "2026-10-11"))}>
      Move to October 11
    </button>
  );
}

function withElements(elements: DraftV1["liturgy"]["custom_elements"], d: DraftV1 = testDraft()): DraftV1 {
  return { ...d, liturgy: { ...d.liturgy, custom_elements: elements } };
}

const COMMUNION = "Include communion liturgy (The Sacrament of the Lord's Supper)";

describe("the communion card (S Communion card)", () => {
  it("follows the first-Sunday rule until toggled, says why, restores the default, and shows the fixed text", async () => {
    const { user } = renderStep(testDraft(), {}, <MoveDate />);
    const communion = await screen.findByRole("region", { name: COMMUNION });
    const toggle = within(communion).getByRole("switch", { name: COMMUNION });
    expect(toggle).toBeChecked();
    expect(within(communion).getByText("On by default — October 4, 2026 is the first Sunday of the month.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Move to October 11" }));
    expect(toggle).not.toBeChecked();
    expect(within(communion).getByText("Off by default — it's on by default only on the first Sunday of the month.")).toBeInTheDocument();
    await user.click(toggle);
    expect(toggle).toBeChecked();
    expect(within(communion).getByText("You changed this.")).toBeInTheDocument();
    await waitFor(() => expect(stored().liturgy).toMatchObject({ include_communion: true, communion_origin: "user" }));
    await user.click(within(communion).getByRole("button", { name: "Use default" }));
    expect(toggle).not.toBeChecked();
    expect(within(communion).queryByRole("button", { name: "Use default" })).toBeNull();
    expect(toggle).toHaveFocus(); // the button went; focus did not drop to the page
    // The fixed text, read-only, from the config.
    expect(within(communion).queryByText("And also with you.")).toBeNull();
    await user.click(within(communion).getByRole("button", { name: "Show communion text" }));
    expect(within(communion).getByRole("heading", { level: 4, name: "The Sacrament of the Lord's Supper" })).toBeInTheDocument();
    expect(within(communion).getByRole("heading", { level: 5, name: "Invitation to the Table" })).toBeInTheDocument();
    expect(within(communion).getByText("And also with you.")).toHaveClass("font-semibold");
    expect(within(communion).getByText("Printed after the Second Hymn. The same text is used for every service.")).toBeInTheDocument();
  });

  it("says when communion came from a saved service", async () => {
    const d = testDraft();
    renderStep({ ...d, liturgy: { ...d.liturgy, include_communion: false, communion_origin: "archive" } });
    const communion = await screen.findByRole("region", { name: COMMUNION });
    expect(within(communion).getByText("Set from the saved service.")).toBeInTheDocument();
    expect(within(communion).getByRole("button", { name: "Use default" })).toBeInTheDocument();
  });
});

describe("custom elements (S Custom elements)", () => {
  it("requires a label, adds after its place with the fields trimmed, scrolls to it, and opens empty next time", async () => {
    const scroll = vi.spyOn(Element.prototype, "scrollIntoView");
    const { user } = renderStep();
    await user.click(await screen.findByRole("button", { name: "Add custom element" }));
    const dialog = await screen.findByRole("dialog", { name: "Add custom element" });
    expect(within(dialog).getByText("A heading and text printed in the Word files at the place you choose.")).toBeInTheDocument();
    expect(within(dialog).getByRole("combobox", { name: "Place" })).toHaveTextContent("After Call to Worship");
    await user.click(within(dialog).getByRole("button", { name: "Add" }));
    expect(within(dialog).getByText("Label is required.")).toBeInTheDocument();
    expect(within(dialog).getByRole("textbox", { name: "Label" })).toHaveFocus();
    await user.type(within(dialog).getByRole("textbox", { name: "Label" }), "  Children's Moment ");
    expect(within(dialog).queryByText("Label is required.")).toBeNull();
    await user.type(within(dialog).getByRole("textbox", { name: "Text (optional)" }), "Come forward. ");
    await user.click(within(dialog).getByRole("combobox", { name: "Place" }));
    await user.click(await screen.findByRole("option", { name: "After Opening Prayer" }));
    await user.click(within(dialog).getByRole("button", { name: "Add" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    const added = await screen.findByRole("region", { name: "Children's Moment" });
    expect(outline().slice(0, 4)).toEqual(["Call to Worship", "Opening Prayer", "Children's Moment", "First Hymn"]);
    expect(within(added).getByText("Custom")).toBeInTheDocument();
    expect(within(added).getByRole("textbox", { name: "Text" })).toHaveValue("Come forward.");
    await waitFor(() =>
      expect(stored().liturgy.custom_elements).toEqual([
        { id: expect.any(String), label: "Children's Moment", text: "Come forward.", insert_after: "opening_prayer" },
      ]),
    );
    await waitFor(() => expect(scroll.mock.contexts).toContain(added));
    await user.click(screen.getByRole("button", { name: "Add custom element" }));
    const again = await screen.findByRole("dialog", { name: "Add custom element" });
    expect(within(again).getByRole("textbox", { name: "Label" })).toHaveValue("");
    expect(within(again).getByRole("combobox", { name: "Place" })).toHaveTextContent("After Call to Worship");
  });

  it("edits the label, text and place inline; a blank label says it won't print, and an unknown place is the end", async () => {
    const { user } = renderStep(
      withElements([
        { id: "a", label: "Anthem", text: "<b>Choir</b>", insert_after: "sermon" },
        { id: "b", label: "Minute for Mission", text: "", insert_after: "bogus" },
      ]),
    );
    const anthem = await screen.findByRole("region", { name: "Anthem" });
    expect(within(anthem).getByRole("textbox", { name: "Text" })).toHaveValue("<b>Choir</b>");
    const rows = outline();
    expect(rows.indexOf("Anthem")).toBe(rows.indexOf("Sermon Title · [Sermon title]") + 1);
    expect(rows.at(-1)).toBe("Minute for Mission"); // an unknown place prints at the end
    expect(within(card("Minute for Mission")).getByRole("combobox", { name: "Place" })).toHaveTextContent("At the end (after Benediction)");
    await user.click(within(anthem).getByRole("combobox", { name: "Place" }));
    await user.click(await screen.findByRole("option", { name: "After Second Hymn" }));
    await waitFor(() => expect(outline().indexOf("Anthem")).toBe(outline().indexOf("Second Hymn") + 1));
    const label = within(card("Anthem")).getByRole("textbox", { name: "Label" });
    await user.clear(label);
    const blank = screen.getByRole("region", { name: "Custom element" });
    expect(within(blank).getByText("Add a label, or remove this element — it won't be printed without one.")).toBeInTheDocument();
    await user.type(label, "Choir Anthem");
    await waitFor(() =>
      expect(stored().liturgy.custom_elements[0]).toEqual({ id: "a", label: "Choir Anthem", text: "<b>Choir</b>", insert_after: "second_hymn" }),
    );
  });

  it("Remove offers Undo, which puts the element back at the same index", async () => {
    const { user } = renderStep(
      withElements([
        { id: "a", label: "Anthem", text: "", insert_after: "sermon" },
        { id: "b", label: "Children's Moment", text: "", insert_after: "sermon" },
      ]),
    );
    const anthem = await screen.findByRole("region", { name: "Anthem" });
    await user.click(within(anthem).getByRole("button", { name: "More actions for Anthem" }));
    await user.click(await screen.findByRole("menuitem", { name: "Remove" }));
    expect(screen.queryByRole("region", { name: "Anthem" })).toBeNull();
    const toastText = await screen.findByText("Removed “Anthem”.");
    await waitFor(() => expect(stored().liturgy.custom_elements.map((e) => e.id)).toEqual(["b"]));
    expect(UNDO_TOAST_MS).toBe(8000);
    await user.click(within(toastText.closest("li") as HTMLElement).getByRole("button", { name: "Undo" }));
    expect(await screen.findByRole("region", { name: "Anthem" })).toBeInTheDocument();
    await waitFor(() => expect(stored().liturgy.custom_elements.map((e) => e.id)).toEqual(["a", "b"]));
  });

  it("stops at 30 elements", async () => {
    const thirty = Array.from({ length: 30 }, (_, i) => ({ id: `e${i}`, label: `Element ${i}`, text: "", insert_after: "end" }));
    renderStep(withElements(thirty));
    expect(await screen.findByRole("button", { name: "Add custom element" })).toBeDisabled();
    expect(screen.getByText("You can add up to 30 custom elements.")).toBeInTheDocument();
  });

  it("after Remove, focus goes to the next card's heading, or to Add custom element when none follows", async () => {
    const { user } = renderStep(
      withElements([
        { id: "a", label: "Anthem", text: "", insert_after: "sermon" },
        { id: "b", label: "Minute for Mission", text: "", insert_after: "end" },
      ]),
    );
    const anthem = await screen.findByRole("region", { name: "Anthem" });
    await user.click(within(anthem).getByRole("button", { name: "More actions for Anthem" }));
    await user.click(await screen.findByRole("menuitem", { name: "Remove" }));
    // After the Sermon row come two landmark rows, then the communion card, whose heading takes focus.
    await waitFor(() => expect(within(card(COMMUNION)).getByRole("heading", { name: COMMUNION })).toHaveFocus());
    await user.click(within(card("Minute for Mission")).getByRole("button", { name: "More actions for Minute for Mission" }));
    await user.click(await screen.findByRole("menuitem", { name: "Remove" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Add custom element" })).toHaveFocus());
  });

  // Heavy: 30 cards, a Remove and an Add through the dialog; near Vitest's 5 s default on a busy machine.
  it("Undo of Remove never goes past 30 elements", { timeout: 10_000 }, async () => {
    const thirty = Array.from({ length: 30 }, (_, i) => ({ id: `e${i}`, label: `Element ${i}`, text: "", insert_after: "end" }));
    const { user } = renderStep(withElements(thirty));
    const first = await screen.findByRole("region", { name: "Element 0" });
    await user.click(within(first).getByRole("button", { name: "More actions for Element 0" }));
    await user.click(await screen.findByRole("menuitem", { name: "Remove" }));
    const toastText = await screen.findByText("Removed “Element 0”.");
    await user.click(screen.getByRole("button", { name: "Add custom element" }));
    const dialog = await screen.findByRole("dialog", { name: "Add custom element" });
    await user.type(within(dialog).getByRole("textbox", { name: "Label" }), "Anthem");
    await user.click(within(dialog).getByRole("button", { name: "Add" }));
    expect(await screen.findByRole("region", { name: "Anthem" })).toBeInTheDocument();
    await user.click(within(toastText.closest("li") as HTMLElement).getByRole("button", { name: "Undo" }));
    // The toast and the step's own line.
    await waitFor(() => expect(screen.getAllByText("You can add up to 30 custom elements.")).toHaveLength(2));
    expect(screen.queryByRole("region", { name: "Element 0" })).toBeNull();
    await waitFor(() => expect(stored().liturgy.custom_elements).toHaveLength(30));
  });

  it("keeps each church's elements in its own draft (streamlit_tests/test_streamlit_tenancy.py)", async () => {
    const hope = church({ id: CHURCH_IDS.hope, name: "Hope" });
    window.localStorage.setItem(
      draftKey(USER_ID, hope.id),
      JSON.stringify({ ...withElements([{ id: "h", label: "Hope's Anthem", text: "", insert_after: "end" }]), church_id: hope.id }),
    );
    const grace = renderStep(withElements([{ id: "g", label: "Grace's Anthem", text: "", insert_after: "end" }]));
    expect(await screen.findByRole("region", { name: "Grace's Anthem" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Hope's Anthem" })).toBeNull();
    grace.unmount();
    installFakeApi({
      "GET /church": churchProfile({ ...hope }),
      "GET /lectionary/readings": lectionaryRoute(),
      "GET /liturgy/config": liturgyConfig(),
    });
    renderWithProviders(
      <BuilderLayout>
        <LiturgyStep />
      </BuilderLayout>,
      { me: me({ churches: [church(), hope] }), church: hope, path: "/builder/liturgy" },
    );
    expect(await screen.findByRole("region", { name: "Hope's Anthem" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Grace's Anthem" })).toBeNull();
  });
});

// --- T1-T10 review fixes ----------------------------------------------------------------

describe("after the T1-T10 review", () => {
  it("a 429's wait outlives New service and an error typed over: the AI bar waits and Generate sends nothing", async () => {
    const { user, api } = renderStep(testDraft(), { "POST /liturgy/generate": fakeError(429, "rate_limited", "Too many requests. Try again in 30 seconds.", { details: { retry_after_seconds: 30 } }) });
    await user.click(within(await screen.findByRole("region", { name: "Offertory Prayer" })).getByRole("button", { name: "Generate" }));
    expect(await within(card("Offertory Prayer")).findByRole("alert")).toHaveTextContent("Too many requests — try again in 30 s.");
    // Typing over the error takes it away, not the wait.
    await user.type(within(card("Offertory Prayer")).getByRole("textbox", { name: "Offertory Prayer" }), "We offer");
    expect(errorIn("Offertory Prayer")).toBeNull();
    expectBarOff(screen.getByRole("button", { name: "Generate empty sections (5)" }));
    vi.setSystemTime(new Date(DRAFT_NOW.getTime() + 10_000)); // a new created_at; 20 s of the wait left
    await user.click(screen.getByRole("button", { name: "More actions" }));
    await user.click(await screen.findByRole("menuitem", { name: "New service" }));
    const confirm = await screen.findByRole("alertdialog", { name: "Start a new service?" });
    await user.click(within(confirm).getByRole("button", { name: "Start new service" }));
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Offertory Prayer" })).toHaveValue(""));
    expectBarOff(screen.getByRole("button", { name: "Generate empty sections (6)" }));
    await user.click(within(card("Call to Worship")).getByRole("button", { name: "Generate" }));
    expect(await within(card("Call to Worship")).findByRole("alert")).toHaveTextContent("Too many requests — try again in 20 s.");
    expect(within(within(card("Call to Worship")).getByRole("alert")).getByRole("button", { name: "Try again" })).toBeDisabled();
    expect(generateCalls(api.requests)).toHaveLength(1);
  });

  it("keeps focus on the AI bar's button when a bulk run ends, and its click does nothing while it is off", async () => {
    const held = heldGenerate();
    const { user } = renderStep(testDraft(), { "POST /liturgy/generate": held.handler });
    await user.click(await screen.findByRole("button", { name: "Generate empty sections (6)" }));
    expect(screen.getByRole("button", { name: "Cancel" })).toHaveFocus();
    for (const key of ["call_to_worship", "opening_prayer", "prayer_of_confession", "assurance", "prayer_for_illumination", "offertory_prayer"] as const) {
      await held.release(key);
    }
    expect(await screen.findByText("Wrote 6 sections.")).toBeInTheDocument();
    const button = screen.getByRole("button", { name: "Generate empty sections (0)" });
    expect(button).toHaveFocus();
    expectBarOff(button);
    await user.click(button);
    expect(held.sent).toHaveLength(6);
    expect(screen.queryByRole("button", { name: "Cancel" })).toBeNull();
  });

  it("Try again asks first when the card holds the user's own text", async () => {
    const { user, api } = renderStep(withCard("opening_prayer", { text: "Gracious God", origin: "typed" }), {
      "POST /liturgy/generate": generateRoute((section) => sectionFailure(section, "ai_timeout", "The AI took too long to answer. Try again.")),
    });
    const op = await screen.findByRole("region", { name: "Opening Prayer" });
    await user.click(within(op).getByRole("button", { name: "Regenerate" }));
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Replace text" }));
    const alert = await within(op).findByRole("alert");
    expect(within(op).getByRole("textbox", { name: "Opening Prayer" })).toHaveValue("Gracious God");
    await user.click(within(alert).getByRole("button", { name: "Try again" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Replace your text?" });
    await user.click(within(dialog).getByRole("button", { name: "Keep my text" }));
    expect(generateCalls(api.requests)).toHaveLength(1);
    expect(within(op).getByRole("textbox", { name: "Opening Prayer" })).toHaveValue("Gracious God");
  });

  it("after adding the 30th element its heading takes focus, since Add custom element is then off", async () => {
    const many = Array.from({ length: 29 }, (_, i) => ({ id: `e${i}`, label: `Element ${i}`, text: "", insert_after: "end" }));
    const { user } = renderStep(withElements(many));
    await user.click(await screen.findByRole("button", { name: "Add custom element" }));
    const dialog = await screen.findByRole("dialog", { name: "Add custom element" });
    await user.type(within(dialog).getByRole("textbox", { name: "Label" }), "Anthem");
    await user.click(within(dialog).getByRole("button", { name: "Add" }));
    const added = await screen.findByRole("region", { name: "Anthem" });
    await waitFor(() => expect(within(added).getByRole("heading", { name: "Anthem" })).toHaveFocus());
    expect(screen.getByRole("button", { name: "Add custom element" })).toBeDisabled();
  });

  it("Add checks the latest draft: another tab that filled the list wins, with the limit's message", async () => {
    const many = Array.from({ length: 29 }, (_, i) => ({ id: `e${i}`, label: `Element ${i}`, text: "", insert_after: "end" }));
    const { user } = renderStep(withElements(many));
    await user.click(await screen.findByRole("button", { name: "Add custom element" }));
    const dialog = await screen.findByRole("dialog", { name: "Add custom element" });
    await user.type(within(dialog).getByRole("textbox", { name: "Label" }), "Anthem");
    await waitFor(() => expect(stored().liturgy.custom_elements).toHaveLength(29));
    const theirs = JSON.stringify({
      ...withElements([...many, { id: "t", label: "Theirs", text: "", insert_after: "end" }], stored()),
      updated_at: "2026-09-29T17:00:00.000Z",
    });
    window.localStorage.setItem(KEY, theirs); // the other tab's write, then its event here
    act(() => {
      window.dispatchEvent(new StorageEvent("storage", { key: KEY, newValue: theirs }));
    });
    await user.click(within(dialog).getByRole("button", { name: "Add" }));
    // The toast and the step's own line.
    await waitFor(() => expect(screen.getAllByText("You can add up to 30 custom elements.")).toHaveLength(2));
    expect(screen.getByRole("region", { name: "Theirs" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Anthem" })).toBeNull();
    expect(stored().liturgy.custom_elements.map((e) => e.label)).not.toContain("Anthem");
    expect(stored().liturgy.custom_elements).toHaveLength(30);
  });

  it("Undo of Remove does nothing once New service has replaced the draft", async () => {
    const { user } = renderStep(withElements([{ id: "a", label: "Anthem", text: "", insert_after: "sermon" }]));
    const anthem = await screen.findByRole("region", { name: "Anthem" });
    await user.click(within(anthem).getByRole("button", { name: "More actions for Anthem" }));
    await user.click(await screen.findByRole("menuitem", { name: "Remove" }));
    const toastText = await screen.findByText("Removed “Anthem”.");
    vi.setSystemTime(new Date(DRAFT_NOW.getTime() + 60_000)); // the new draft's created_at differs
    await user.click(screen.getByRole("button", { name: "More actions" }));
    await user.click(await screen.findByRole("menuitem", { name: "New service" }));
    const fresh = new Date(DRAFT_NOW.getTime() + 60_000).toISOString();
    await waitFor(() => expect(stored().created_at).toBe(fresh));
    await user.click(within(toastText.closest("li") as HTMLElement).getByRole("button", { name: "Undo" }));
    // Positive first: the fresh draft is the one on screen and stored; then nothing came back into it.
    await waitFor(() => expect(screen.queryByText("Removed “Anthem”.")).toBeNull());
    expect(screen.queryByRole("region", { name: "Anthem" })).toBeNull();
    expect(stored().created_at).toBe(fresh);
    expect(stored().liturgy.custom_elements).toEqual([]);
  });
});

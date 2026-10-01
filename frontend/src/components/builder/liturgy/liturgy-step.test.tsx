/**
 * The Liturgy step (slice 4 spec, "User experience", Testing "dom"; F §4.6,
 * §4.8). The step runs inside the real builder layout against the fake API.
 * The clock is Tuesday, September 29, 2026 (only `Date` is faked), so a fresh
 * draft is dated Sunday, October 4, 2026 (a first Sunday), and the lectionary
 * answers "no readings", so the readings stay as each test seeds them.
 */
import { act, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import { Toaster } from "@/components/ui/sonner";
import { editScriptureLines, setPick } from "@/lib/draft/readings";
import { draftKey, type DraftV1, type SectionKey } from "@/lib/draft/schema";
import { editCardText } from "@/lib/liturgy/cards";
import { keys } from "@/lib/queries/keys";
import { fakeError, installFakeApi, type FakeHandler } from "@/test/fake-api";
import {
  church,
  churchProfile,
  DRAFT_NOW,
  gg2013,
  lectionaryRoute,
  liturgyConfig,
  me,
  testDraft,
  USER_ID,
} from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { LiturgyStep } from "./liturgy-step";

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
    expect(text).toHaveValue("Halverson");
    expect(within(benediction).getByText("Church default")).toBeInTheDocument();
    expect(within(benediction).getByText("Your church's default benediction. Admins can change it in Settings.")).toBeInTheDocument();
    // An admin changes the default (6a) and the profile refetches.
    act(() => queryClient.setQueryData(keys.churchProfile(church().id), churchProfile({ default_benediction: "The Lord bless you." })));
    await waitFor(() => expect(text).toHaveValue("The Lord bless you."));
    await user.clear(text);
    await user.type(text, "Go in peace.");
    expect(within(benediction).getByText("Your text")).toBeInTheDocument();
    expect(within(benediction).queryByText(/Your church's default benediction/)).toBeNull();
    act(() => queryClient.setQueryData(keys.churchProfile(church().id), churchProfile({ default_benediction: "Halverson" })));
    await user.click(within(benediction).getByRole("button", { name: "More actions for Benediction" }));
    await user.click(await screen.findByRole("menuitem", { name: "Use church default" }));
    expect(text).toHaveValue("Halverson");
    expect(within(benediction).getByText("Church default")).toBeInTheDocument();
    await waitFor(() => expect(stored().liturgy.cards.benediction).toEqual({ enabled: true, text: "Halverson", origin: "default" }));
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
    expect(within(cw).getByText("Cleared.")).toBeInTheDocument();
    await user.click(within(cw).getByRole("button", { name: "Undo" }));
    expect(text).toHaveValue("Come.");
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

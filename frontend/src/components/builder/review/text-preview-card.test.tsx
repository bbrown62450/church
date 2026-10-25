/**
 * The Review step's text preview (formatting spec, "The Review preview"):
 * closed at first; open, each box with text as the printed bulletin prints it
 * (the rules shared/formatting.json pins for both sides), what is typed always
 * shown as text, a 44 px toggle and no em dash. In the real builder layout
 * against the fake API.
 */
import { screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import { draftKey, type DraftV1 } from "@/lib/draft/schema";
import { printedLines } from "@/lib/formatting";
import { installFakeApi } from "@/test/fake-api";
import {
  bulletinSettings,
  church,
  churchProfile,
  DRAFT_NOW,
  gmailConnection,
  lectionaryRoute,
  liturgyConfig,
  me,
  previousBulletin,
  testDraft,
  USER_ID,
} from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { PREVIEW_EMPTY, PREVIEW_INTRO, PREVIEW_TITLE, previewBoxes, TextPreviewCard } from "./text-preview-card";

const KEY = draftKey(USER_ID, church().id);

function render(draft: DraftV1) {
  window.localStorage.setItem(KEY, JSON.stringify(draft));
  installFakeApi({
    "GET /church": churchProfile(),
    "GET /lectionary/readings": lectionaryRoute(),
    "GET /liturgy/config": liturgyConfig(),
    "GET /church/bulletin-settings": bulletinSettings(),
    "GET /services/previous-bulletin": previousBulletin(),
    "GET /gmail-connection": gmailConnection(),
  });
  return renderWithProviders(
    <BuilderLayout>
      <TextPreviewCard />
    </BuilderLayout>,
    { me: me(), church: church(), path: "/builder/review" },
  );
}

function filled(): DraftV1 {
  const draft = testDraft();
  const cards = draft.liturgy.cards;
  const set = (key: keyof typeof cards, text: string) => (cards[key] = { ...cards[key], enabled: true, text, origin: "typed" });
  set("opening_prayer", "# For the world\nWe pray for **peace** and *justice*.\n- the sick\n12. the lonely");
  set("call_to_worship", "Leader: Come.\nPeople: We come *gladly*.");
  set("assurance", "Leader: In Christ we are forgiven.");
  set("offertory_prayer", "<img src=x onerror=alert(1)> **<b>bold</b>**");
  set("benediction", "   ");
  set("prayer_of_confession", "We confess:\n1. our pride");
  draft.liturgy.custom_elements = [{ id: "c1", label: "Anthem", text: "Sung by the *choir*", insert_after: "sermon" }];
  draft.bulletin.announcements.other = "# This week\n- Choir";
  return draft;
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
});

async function open(draft: DraftV1) {
  const { user } = render(draft);
  const card = await screen.findByRole("region", { name: PREVIEW_TITLE });
  expect(within(card).getByText(PREVIEW_INTRO)).toBeInTheDocument();
  const toggle = within(card).getByRole("button", { name: "Show text preview" });
  expect(toggle).toHaveClass("min-h-11"); // 44 px on a phone
  expect(within(card).queryByRole("region", { name: "Opening Prayer" })).toBeNull();
  await user.click(toggle);
  return card;
}

const style = (element: HTMLElement) => element.closest("p")?.getAttribute("data-style");

describe("the text preview (formatting spec)", () => {
  it("shows each box as it prints: headings, bold, italic, lists, People lines and the fixed response", async () => {
    const card = await open(filled());
    const prayer = within(card).getByRole("region", { name: "Opening Prayer" });
    expect(style(within(prayer).getByText("For the world"))).toBe("heading1");
    expect(within(prayer).getByText("peace")).toHaveClass("font-bold");
    expect(within(prayer).getByText("justice")).toHaveClass("italic");
    expect(style(within(prayer).getByText("the sick"))).toBe("item");
    expect(within(prayer).getByText("•")).toBeInTheDocument();
    expect(within(prayer).getByText("12.")).not.toHaveClass("font-bold");
    // The Prayer of Confession's markers are bold, as every file prints them.
    const confession = within(card).getByRole("region", { name: "Prayer of Confession" });
    expect(within(confession).getByText("1.")).toHaveClass("font-bold");
    const call = within(card).getByRole("region", { name: "Call to Worship" });
    expect(within(call).getByText("People:", { exact: false })).toHaveClass("font-bold");
    expect(within(call).getByText("gladly")).toHaveClass("font-bold", "italic");
    const assurance = within(card).getByRole("region", { name: "Assurance of Pardon" });
    expect(within(assurance).getByText("People: Thanks be to God! Amen.")).toHaveClass("font-bold");
    expect(within(within(card).getByRole("region", { name: "Anthem" })).getByText("choir")).toHaveClass("italic");
    const other = within(card).getByRole("region", { name: "Other announcements" });
    expect(style(within(other).getByText("This week"))).toBe("center_heading1");
    expect(within(card).queryByRole("region", { name: "Benediction" })).toBeNull(); // blank: nothing prints
    expect(card.textContent).not.toContain("\u2014");
  });

  it("shows what is typed as text, never as markup", async () => {
    const card = await open(filled());
    const offertory = within(card).getByRole("region", { name: "Offertory Prayer" });
    expect(within(offertory).getByText("<img src=x onerror=alert(1)>", { exact: false })).toBeInTheDocument();
    expect(within(offertory).getByText("<b>bold</b>")).toHaveClass("font-bold");
    expect(card.querySelector("img, b, script")).toBeNull();
  });

  it("says so when no box has text", async () => {
    const draft = testDraft();
    for (const card of Object.values(draft.liturgy.cards)) Object.assign(card, { text: "", origin: "typed" });
    const card = await open(draft);
    expect(within(card).getByText(PREVIEW_EMPTY)).toBeInTheDocument();
  });
});

describe("previewBoxes (formatting spec)", () => {
  const lines = (draft: DraftV1, id: string) => {
    const box = previewBoxes(draft).find((b) => b.id === id);
    return box ? printedLines(box.box, box.text) : undefined;
  };

  it("prints the Prayer of Confession and the Affirmation's own text all bold, as the printed bulletin does", () => {
    const draft = testDraft();
    const cards = draft.liturgy.cards;
    cards.prayer_of_confession = { ...cards.prayer_of_confession, enabled: true, text: "We confess *our sin*.", origin: "typed" };
    draft.liturgy.affirmation = { include: true, choice: "own", text: "We trust in *God*.\n- who made us", origin: "user" };
    expect(lines(draft, "prayer_of_confession")).toEqual([
      {
        style: "bold",
        marker: "",
        spans: [
          { text: "We confess ", bold: true, italic: false },
          { text: "our sin", bold: true, italic: true },
          { text: ".", bold: true, italic: false },
        ],
      },
    ]);
    expect(lines(draft, "affirmation")).toEqual([
      {
        style: "bold",
        marker: "",
        spans: [
          { text: "We trust in ", bold: true, italic: false },
          { text: "God", bold: true, italic: true },
          { text: ".", bold: true, italic: false },
        ],
      },
      { style: "item", marker: "•", markerBold: true, spans: [{ text: "who made us", bold: true, italic: false }] },
    ]);
  });

  it("leaves out a custom element whose label is blank, as the server does", () => {
    const draft = testDraft();
    draft.liturgy.custom_elements = [
      { id: "blank", label: " \u000b ", text: "Sung by the choir", insert_after: "sermon" },
      { id: "named", label: " Anthem ", text: "Sung by the choir", insert_after: "sermon" },
    ];
    const custom = previewBoxes(draft).filter((b) => b.id.startsWith("custom-"));
    expect(custom.map((b) => [b.id, b.label])).toEqual([["custom-named", "Anthem"]]);
  });

  it("leaves out a switched-off card, and the Affirmation when it is off or a creed", () => {
    const draft = testDraft();
    const cards = draft.liturgy.cards;
    cards.opening_prayer = { ...cards.opening_prayer, enabled: false, text: "Gracious God", origin: "typed" };
    draft.liturgy.affirmation = { include: false, choice: "own", text: "We trust.", origin: "user" };
    expect(lines(draft, "opening_prayer")).toBeUndefined();
    expect(lines(draft, "affirmation")).toBeUndefined();
    draft.liturgy.affirmation = { include: true, choice: "nicene", text: "We trust.", origin: "user" };
    expect(lines(draft, "affirmation")).toBeUndefined();
  });

  it("reads line endings, a vertical tab and a form feed as the server does", () => {
    const draft = testDraft();
    const cards = draft.liturgy.cards;
    cards.opening_prayer = { ...cards.opening_prayer, enabled: true, text: "\r\n# One\r- two\u000b- three\u000c\u0001four ", origin: "typed" };
    expect(previewBoxes(draft).find((b) => b.id === "opening_prayer")?.text).toBe("# One\n- two\n- three\nfour");
  });
});

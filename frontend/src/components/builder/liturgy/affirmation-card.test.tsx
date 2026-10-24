/**
 * The Affirmation of Faith card on the Liturgy step (affirmation spec, "The
 * Affirmation card"), in the real builder layout against the fake API, as
 * liturgy-step.test.tsx renders it. The clock is Tuesday, September 29, 2026.
 */
import { screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import { Toaster } from "@/components/ui/sonner";
import { draftKey, type DraftV1 } from "@/lib/draft/schema";
import { installFakeApi, type FakeHandler } from "@/test/fake-api";
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

import { AFFIRMATION_OFF, OWN_TEXT_BLANK, OWN_TEXT_HINT } from "./affirmation-card";
import { LiturgyStep } from "./liturgy-step";

const KEY = draftKey(USER_ID, church().id);
const TITLE = "Include Affirmation of Faith";
const OWN = "We trust in God the Holy Spirit.";

function stored(): DraftV1 {
  return JSON.parse(window.localStorage.getItem(KEY) ?? "null") as DraftV1;
}

function renderStep(draft: DraftV1 = testDraft(), routes: Record<string, FakeHandler> = {}) {
  window.localStorage.setItem(KEY, JSON.stringify(draft));
  installFakeApi({
    "GET /church": churchProfile(),
    "GET /lectionary/readings": lectionaryRoute(),
    "GET /liturgy/config": liturgyConfig(),
    "GET /church/bulletin-settings": bulletinSettings(),
    "GET /services/previous-bulletin": previousBulletin(),
    "GET /gmail-connection": gmailConnection(),
    ...routes,
  });
  return renderWithProviders(
    <>
      <BuilderLayout>
        <LiturgyStep />
      </BuilderLayout>
      <Toaster />
    </>,
    { me: me(), church: church(), path: "/builder/liturgy" },
  );
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
  toast.dismiss();
});

afterEach(() => {
  vi.useRealTimers();
});

async function card() {
  return screen.findByRole("region", { name: TITLE });
}

describe("the Affirmation of Faith card (affirmation spec)", () => {
  it("starts on, with the church's default chosen, and shows the creed and its credit behind Show creed text", async () => {
    const { user } = renderStep();
    const region = await card();
    expect(within(region).getByRole("switch", { name: TITLE })).toBeChecked();
    expect(within(region).getByText("Your church's default.")).toBeInTheDocument();
    const choices = within(region).getAllByRole("radio");
    expect(choices.map((radio) => radio.closest("label")?.textContent)).toEqual(["Apostles' Creed", "Nicene Creed", "Your own text"]);
    expect(within(region).getByRole("radio", { name: "Apostles' Creed" })).toBeChecked();
    // 44 px rows at every width (375 px included).
    for (const radio of choices) expect(radio.closest("label")).toHaveClass("min-h-11");
    await user.click(within(region).getByRole("radio", { name: "Nicene Creed" }));
    await user.click(within(region).getByRole("button", { name: "Show creed text" }));
    // One line per sense line, each with a hanging indent (a line that wraps on a phone reads as one).
    for (const line of ["We believe in one God,", "the Father, the Almighty,"]) {
      expect(within(region).getByText(line)).toHaveClass("pl-4", "-indent-4");
    }
    expect(within(region).getByText(/Consultation \(ELLC\), and used by permission\./)).toBeInTheDocument();
    expect(within(region).getByText("You changed this.")).toBeInTheDocument();
    await waitFor(() => expect(stored().liturgy.affirmation).toEqual({ include: true, choice: "nicene", text: "", origin: "user" }));
    expect(region.textContent).not.toContain("\u2014");
  });

  it("switched off hides the choices and says it is not printed or emailed", async () => {
    const { user } = renderStep();
    const region = await card();
    await user.click(within(region).getByRole("switch", { name: TITLE }));
    expect(within(region).queryAllByRole("radio")).toEqual([]);
    expect(within(region).getByText(`${AFFIRMATION_OFF} You changed this.`)).toBeInTheDocument();
    await waitFor(() => expect(stored().liturgy.affirmation.include).toBe(false));
    expect(region.textContent).not.toContain("\u2014");
  });

  it("takes own text in a box like a prayer card's, and Use church default puts the default back with focus on the switch", async () => {
    const { user } = renderStep();
    const region = await card();
    await user.click(within(region).getByRole("radio", { name: "Your own text" }));
    const box = within(region).getByRole("textbox", { name: "Your own text" });
    expect(box).toHaveAccessibleDescription(`${OWN_TEXT_HINT} ${OWN_TEXT_BLANK}`);
    expect(box).toHaveAttribute("maxlength", "20000");
    await user.type(box, OWN);
    expect(box).toHaveAccessibleDescription(OWN_TEXT_HINT);
    await waitFor(() => expect(stored().liturgy.affirmation).toEqual({ include: true, choice: "own", text: OWN, origin: "user" }));
    await user.click(within(region).getByRole("button", { name: "Use church default" }));
    await waitFor(() => expect(within(region).getByRole("switch", { name: TITLE })).toHaveFocus());
    expect(within(region).getByRole("radio", { name: "Apostles' Creed" })).toBeChecked();
    expect(within(region).queryByRole("button", { name: "Use church default" })).toBeNull();
    await waitFor(() => expect(stored().liturgy.affirmation).toEqual({ include: true, choice: "apostles", text: "", origin: "default" }));
  });

  it("follows a church whose default is its own text, and says so for a saved service", async () => {
    const own = churchProfile({ default_affirmation: { choice: "own", text: OWN } });
    renderStep(testDraft(), { "GET /church": own });
    const region = await card();
    await waitFor(() => expect(within(region).getByRole("textbox", { name: "Your own text" })).toHaveValue(OWN));
    expect(within(region).getByRole("radio", { name: "Your own text" })).toBeChecked();
  });

  it("keeps the Affirmation row when the API sends no card data (the pages ahead of the server side)", async () => {
    const older = { ...liturgyConfig(), affirmation: undefined } as unknown as ReturnType<typeof liturgyConfig>;
    renderStep(testDraft(), { "GET /liturgy/config": older });
    const order = await screen.findByRole("list", { name: "Order of worship" });
    await waitFor(() =>
      expect(within(order).getAllByRole("listitem").map((li) => li.textContent)).toContain("Affirmation of Faith · Apostles' Creed"),
    );
    expect(screen.queryByRole("region", { name: TITLE })).toBeNull();
  });

  it("shows a saved service's choice as set from the saved service", async () => {
    const d = testDraft();
    renderStep({ ...d, liturgy: { ...d.liturgy, affirmation: { include: false, choice: "nicene", text: "", origin: "archive" } } });
    const region = await card();
    expect(within(region).getByRole("switch", { name: TITLE })).not.toBeChecked();
    expect(within(region).getByText(`${AFFIRMATION_OFF} Set from the saved service.`)).toBeInTheDocument();
    expect(within(region).getByRole("button", { name: "Use church default" })).toBeInTheDocument();
  });
});

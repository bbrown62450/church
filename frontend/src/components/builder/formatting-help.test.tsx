/**
 * The "Formatting help" line under each text box (formatting spec, "Help
 * copy"; owner decision 4), as each box's description: the prayer cards (bold
 * and italic only in the two dialogue cards), a custom element, the
 * Affirmation's own text and the four free-text announcements; never a name
 * box. In the real builder layout against the fake API.
 */
import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import BulletinStepPage from "@/app/(signed-in)/(church)/builder/bulletin/page";
import { LiturgyStep } from "@/components/builder/liturgy/liturgy-step";
import { draftKey, type DraftV1 } from "@/lib/draft/schema";
import { installFakeApi } from "@/test/fake-api";
import {
  bulletinSettings,
  church,
  churchProfile,
  DRAFT_NOW,
  filledBulletinSettings,
  gmailConnection,
  lectionaryRoute,
  liturgyConfig,
  me,
  previousBulletin,
  testDraft,
  USER_ID,
} from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { DIALOGUE_HELP, FORMATTING_HELP } from "./formatting-help";

const KEY = draftKey(USER_ID, church().id);

function render(page: "liturgy" | "bulletin", draft: DraftV1) {
  window.localStorage.setItem(KEY, JSON.stringify(draft));
  installFakeApi({
    "GET /church": churchProfile(),
    "GET /lectionary/readings": lectionaryRoute(),
    "GET /liturgy/config": liturgyConfig(),
    "GET /church/bulletin-settings": page === "bulletin" ? filledBulletinSettings() : bulletinSettings(),
    "GET /services/previous-bulletin": previousBulletin(),
    "GET /gmail-connection": gmailConnection(),
  });
  return renderWithProviders(<BuilderLayout>{page === "liturgy" ? <LiturgyStep /> : <BulletinStepPage />}</BuilderLayout>, {
    me: me(),
    church: church(),
    path: `/builder/${page}`,
  });
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
});

describe("the formatting help line (formatting spec)", () => {
  it("is in each box's description on the Liturgy step, bold and italic only for the dialogue cards", async () => {
    const draft = testDraft();
    draft.liturgy.custom_elements = [{ id: "c1", label: "Anthem", text: "", insert_after: "sermon" }];
    draft.liturgy.affirmation = { include: true, choice: "own", text: "We trust.", origin: "user" };
    render("liturgy", draft);
    const prayer = await screen.findByRole("textbox", { name: "Opening Prayer" });
    expect(prayer).toHaveAccessibleDescription(expect.stringContaining(FORMATTING_HELP));
    for (const name of ["Call to Worship", "Assurance of Pardon"]) {
      const box = screen.getByRole("textbox", { name });
      expect(box).toHaveAccessibleDescription(expect.stringContaining(DIALOGUE_HELP));
      expect(box).not.toHaveAccessibleDescription(expect.stringContaining(FORMATTING_HELP));
    }
    expect(screen.getByRole("textbox", { name: "Text" })).toHaveAccessibleDescription(FORMATTING_HELP);
    expect(screen.getByRole("textbox", { name: "Your own text" })).toHaveAccessibleDescription(
      expect.stringContaining(FORMATTING_HELP),
    );
  });

  it("is under the free-text announcements, not the names", async () => {
    render("bulletin", testDraft());
    for (const name of ["This week's activities", "Prayers and concerns", "Items for collection", "Other announcements"]) {
      expect(await screen.findByRole("textbox", { name })).toHaveAccessibleDescription(FORMATTING_HELP);
    }
    expect(screen.getByRole("textbox", { name: "Ushers and counters" })).not.toHaveAccessibleDescription(
      expect.stringContaining("Formatting"),
    );
  });

  it("names the marks without an em dash", () => {
    for (const copy of [FORMATTING_HELP, DIALOGUE_HELP]) expect(copy).not.toContain("\u2014");
    expect(FORMATTING_HELP).toContain("**bold**");
    expect(FORMATTING_HELP).toContain("# Heading");
  });
});

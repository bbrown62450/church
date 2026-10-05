/**
 * The Voices of the Church panel (Voices V1 spec "The panel"; owner's planning answers 1, 3, 4 and
 * source decision 2, 2026-10-05): collapsed with its count, the sections as printed, "Not yet
 * transcribed", the lectionary label, loading and failure, the credit; 44 px targets.
 */
import { screen, waitFor, within } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import { fakeError, installFakeApi, type FakeHandler } from "@/test/fake-api";
import {
  church,
  linkingComment,
  me,
  uncheckedVoiceSection,
  voiceComment,
  voices,
  voiceSection,
  voicesRoute,
} from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";
import type { VoicesPassage } from "@/lib/voices";

import { VoicesPanel } from "./voices-panel";

const MATTHEW: VoicesPassage = { reference: "Matthew 22:15-22", line: "Matthew 22:15-22", fromLectionary: false };

function Panel({ passage }: { passage: VoicesPassage }) {
  const [open, setOpen] = useState(false);
  return <VoicesPanel passage={passage} open={open} onOpenChange={setOpen} />;
}

function renderPanel(handler: FakeHandler = voicesRoute(), passage: VoicesPassage = MATTHEW) {
  const api = installFakeApi({ "GET /voices": handler });
  const view = renderWithProviders(<Panel passage={passage} />, { me: me(), church: church() });
  return { ...view, api };
}

function trigger() {
  return screen.getByRole("button", { name: /^Voices of the Church/ });
}

describe("VoicesPanel", () => {
  it("starts collapsed with the count of quotations on the verses, as a 44 px disclosure button", async () => {
    const { api } = renderPanel();
    await waitFor(() => expect(trigger()).toHaveAccessibleName("Voices of the Church 4 quotations on these verses"));
    expect(trigger()).toHaveAttribute("aria-expanded", "false");
    expect(trigger()).toHaveClass("min-h-11");
    expect(screen.queryByText(/This is the first excellence/)).toBeNull();
    expect(screen.queryByText("From the Gospel for this Sunday: Matthew 22:15-22")).toBeNull();
    expect(api.requests.map((r) => r.path)).toEqual(["/voices?reference=Matthew%2022%3A15-22"]);
  });

  it("opens to each quotation with its father, the margin reference, the text as printed and the credit", async () => {
    const { user } = renderPanel();
    await waitFor(() => expect(trigger()).toHaveAccessibleName(/4 quotations/));
    await user.click(trigger());
    expect(trigger()).toHaveAttribute("aria-expanded", "true");
    const region = screen.getByRole("region", { name: "Matthew 22:15-22" });
    expect(within(region).getByRole("heading", { name: "Matthew 22:15-22" })).toBeInTheDocument();
    const pages = within(region).getByRole("link", { name: /Printed pages 748-752/ });
    expect(pages).toHaveAttribute("href", "https://archive.org/details/catenaurecommpt301thomuoft/page/n19/mode/1up");
    expect(pages).toHaveAttribute("target", "_blank");
    expect(pages).toHaveAttribute("rel", "noopener noreferrer");
    expect(pages).toHaveAccessibleName("Printed pages 748-752, Vol. I, St. Matthew, Part III (1842) (opens in a new tab)");
    expect(pages).toHaveClass("min-h-11");

    const items = within(region).getAllByRole("listitem");
    expect(items.map((item) => within(item).getByRole("heading").textContent)).toEqual([
      "Jerome",
      "Chrysostom Chrys. Hom. lxx.",
      "Origen",
      "The Gloss Gloss. ord.",
    ]);
    expect(within(items[0]).getByText(/^This is the first excellence of the answerer/)).toBeInTheDocument();
    // Italics as printed, a printed paragraph break, and the margin's Scripture reference.
    const origen = items[2];
    expect(within(origen).getByText("forbidding to marry, and commanding to abstain from meats, which God hath created.").tagName).toBe("EM");
    expect(within(origen).getByText("Or the prince of this world, that is, the Devil, is called Cæsar.").tagName).toBe("P");
    expect(within(origen).getByText("In the margin: 1 Tim. 4, 3.")).toBeInTheDocument();
    expect(screen.getByText(/^From the Catena Aurea of Thomas Aquinas, vol. I, St. Matthew/)).toBeInTheDocument();
    expect(screen.queryByText(/\*/)).toBeNull();

    await user.click(trigger());
    expect(trigger()).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("region", { name: "Matthew 22:15-22" })).toBeNull();
  });

  it("says a section not yet checked is not yet transcribed, and counts only the checked quotations", async () => {
    const { user } = renderPanel(voicesRoute((reference) =>
      voices(reference, { sections: [voiceSection({ comments: [voiceComment()] }), uncheckedVoiceSection()] })));
    await waitFor(() => expect(trigger()).toHaveAccessibleName("Voices of the Church 1 quotation on these verses"));
    await user.click(trigger());
    const unchecked = screen.getByRole("region", { name: "Matthew 22:23-33" });
    expect(within(unchecked).getByText("Not yet transcribed for this passage.")).toBeInTheDocument();
    expect(within(unchecked).getByRole("link", { name: /Printed pages 752-760/ })).toBeInTheDocument();
    expect(within(unchecked).queryByRole("listitem")).toBeNull();
  });

  it("shows the Catena's own linking words under no father's name, an erratum's note, and counts the fathers only", async () => {
    const hilary = voiceComment({ label: "Hilary;", father: "Hilary", work: null, text: "For if." });
    const corrected = voiceComment({
      label: "Pseudo-Jerome;",
      father: "Pseudo-Jerome",
      work: null,
      printed_label: "JEROME",
      notes: ["¹ alia re frui.", "² al. bonum."],
    });
    const { user } = renderPanel(voicesRoute((reference) =>
      voices(reference, { sections: [voiceSection({ comments: [hilary, linkingComment(), corrected] })] })));
    await waitFor(() => expect(trigger()).toHaveAccessibleName("Voices of the Church 2 quotations on these verses"));
    await user.click(trigger());
    const items = within(screen.getByRole("region", { name: "Matthew 22:15-22" })).getAllByRole("listitem");
    expect(items.map((item) => within(item).getByRole("heading").textContent)).toEqual([
      "Hilary",
      "Aquinas, linking the comments",
      "Pseudo-Jerome",
    ]);
    expect(within(items[1]).getByText("On these two commandments hang all the Law and the Prophets.").tagName).toBe("EM");
    expect(within(items[2]).getByText("Corrected by the volume's errata: printed as JEROME")).toBeInTheDocument();
    expect(within(items[2]).getByText("In the margin: ¹ alia re frui. ² al. bonum.")).toBeInTheDocument();
  });

  it("shows no panel for a line the server cannot read as a Gospel passage", async () => {
    renderPanel(() => fakeError(422, "invalid_request", "Choose a passage from Matthew, Mark, Luke or John."));
    expect(trigger()).toHaveAccessibleName("Voices of the Church Loading the fathers' comments…");
    await waitFor(() => expect(screen.queryByRole("button", { name: /^Voices of the Church/ })).toBeNull());
    expect(screen.queryByText("The fathers' comments couldn't be loaded.")).toBeNull();
  });

  it("says so in the button when nothing on the verses is checked yet", async () => {
    renderPanel(voicesRoute((reference) => voices(reference, { sections: [uncheckedVoiceSection()] })));
    await waitFor(() =>
      expect(trigger()).toHaveAccessibleName("Voices of the Church Not yet transcribed for this passage."));
  });

  it("labels the Sunday's lectionary Gospel when no bulletin reading is from a Gospel", async () => {
    renderPanel(voicesRoute(), { ...MATTHEW, fromLectionary: true });
    expect(await screen.findByText("From the Gospel for this Sunday: Matthew 22:15-22")).toBeInTheDocument();
  });

  it("says it is loading, then a failure with Try again, which asks again", async () => {
    let answer: (value: unknown) => void = () => {};
    let calls = 0;
    const { user } = renderPanel(() => {
      calls += 1;
      if (calls === 1) return fakeError(503, "internal_error", "Something went wrong.");
      return new Promise((resolve) => (answer = resolve));
    });
    await user.click(trigger());
    const retry = await screen.findByRole("button", { name: "Try again: Voices of the Church" });
    expect(screen.getAllByText("The fathers' comments couldn't be loaded.")).toHaveLength(2); // the button and the panel
    expect(trigger()).toHaveAccessibleName("Voices of the Church The fathers' comments couldn't be loaded.");
    expect(retry).toHaveClass("h-11");
    await user.click(retry);
    expect(await screen.findAllByText("Loading the fathers' comments…")).not.toHaveLength(0);
    answer(voices());
    await waitFor(() => expect(trigger()).toHaveAccessibleName(/4 quotations/));
  });
});

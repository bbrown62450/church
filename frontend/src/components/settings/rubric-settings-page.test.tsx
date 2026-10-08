/**
 * Settings → Rubric (slice 6a-3a; 6a spec UX §6): every member reads the
 * rubric, owners and admins edit its checklists and preferences and save one
 * sparse PATCH. Rendered inside the Settings layout, as the route is, with a
 * Toaster. Below `md` (jsdom's matchMedia never matches) every card starts closed.
 */
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, describe, expect, it, vi } from "vitest";

import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
import RubricSettingsRoute from "@/app/(signed-in)/(church)/settings/rubric/page";
import { DISCARD_TITLE } from "@/components/app/leave-guard";
import { Toaster } from "@/components/ui/sonner";
import type { Church, RubricValues } from "@/lib/api/types";
import { authEvents } from "@/lib/queries/auth-events";
import { keys } from "@/lib/queries/keys";
import { RUBRIC_RESET, RUBRIC_SAVED } from "@/lib/queries/rubric";
import { KEEP_ONE_POINT } from "@/lib/settings/rubric";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { church, defaultRubric, me, rubric } from "@/test/fixtures";
import { testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import { THEME_NOTE } from "./checklist-card";
import { ADMINS_ONLY, RESET_ALL_TITLE, RUBRIC_INTRO } from "./rubric-settings-page";

afterEach(() => {
  toast.dismiss();
});

const DEFAULTS = defaultRubric();
const THIS_YEAR = new Date().getFullYear();

function renderPage(role: Church["role"] = "admin", routes: Record<string, FakeHandler> = {}) {
  const active = church({ role });
  const api = installFakeApi({ "GET /rubric": rubric(), "PATCH /rubric": () => rubric(), ...routes });
  const view = renderWithProviders(
    <>
      <SettingsLayout>
        <RubricSettingsRoute />
      </SettingsLayout>
      <Toaster />
    </>,
    { me: me({ churches: [active] }), church: active, path: "/settings/rubric" },
  );
  return { ...view, api };
}

function patches(api: { requests: RecordedRequest[] }) {
  return api.requests.filter((r) => r.method === "PATCH" && r.path === "/rubric");
}

/** A card's header button: its title, then "Customized" when it is. */
function cardButton(title: string) {
  return screen.findByRole("button", { name: new RegExp(`^${title.replace(/[()]/g, "\\$&")}( Customized)?$`) });
}

/** Opens a card (they start closed on a phone) and returns it. */
async function openCard(user: ReturnType<typeof renderPage>["user"], title: string) {
  const button = await cardButton(title);
  await user.click(button);
  return button.closest("[data-slot=collapsible]") as HTMLElement;
}

function points(card: HTMLElement) {
  return within(card).getAllByRole("textbox").map((box) => (box as HTMLTextAreaElement).value);
}

describe("Settings → Rubric (slice 6a-3a)", () => {
  it("shows a member the rubric as text, with the note and no controls", async () => {
    const { user } = renderPage("member", { "GET /rubric": rubric({ prayers: { benediction: ["Sends the people out."] } }) });
    expect(await screen.findByText(ADMINS_ONLY)).toBeInTheDocument();
    expect(screen.getByText(RUBRIC_INTRO)).toBeInTheDocument();
    expect(screen.getByLabelText("Prefer hymns written before")).toHaveAttribute("readonly");
    expect(screen.getByRole("switch", { name: "Prefer familiar hymns" })).toHaveAttribute("aria-disabled", "true");
    const card = await openCard(user, "Benediction");
    expect(within(card).getByText("A good Benediction:")).toBeInTheDocument();
    expect(within(card).getAllByRole("listitem").map((li) => li.textContent)).toEqual(["Sends the people out."]);
    expect(screen.getByRole("button", { name: "Benediction Customized" })).toBeInTheDocument();
    expect(within(card).queryAllByRole("textbox")).toEqual([]);
    for (const name of [/^Remove point/, "Add a point", /Reset to default/, "Save rubric", "Reset all to defaults"]) {
      expect(screen.queryByRole("button", { name })).toBeNull();
    }
  });

  it("saves one PATCH with only the changed checklist, cleaned, and the badge follows the points", async () => {
    const { api, user } = renderPage("admin", {
      "PATCH /rubric": () => rubric({ prayers: { benediction: ["Benediction point one", "Sends the people out."] } }),
    });
    const save = await screen.findByRole("button", { name: "Save rubric" });
    expect(save).toBeDisabled();
    const card = await openCard(user, "Benediction");
    const second = within(card).getByRole("textbox", { name: "Point 2 of Benediction" });
    await user.clear(second);
    await user.type(second, "  Sends the   people out. ");
    expect(screen.getByRole("button", { name: "Benediction Customized" })).toBeInTheDocument();
    await user.click(save);
    expect(await screen.findByText(RUBRIC_SAVED)).toBeInTheDocument();
    expect(patches(api)).toHaveLength(1);
    expect(patches(api)[0].body).toEqual({ prayers: { benediction: ["Benediction point one", "Sends the people out."] } });
    expect(patches(api)[0].headers["x-church-id"]).toBe(church().id);
    await waitFor(() => expect(save).toBeDisabled());
  });

  it("sends null for a checklist put back to its default, and Reset to default restores the default points unsaved", async () => {
    const { api, user } = renderPage("admin", { "GET /rubric": rubric({ prayers: { benediction: ["Ours."] } }) });
    const card = await openCard(user, "Benediction");
    expect(points(card)).toEqual(["Ours."]);
    await user.click(within(card).getByRole("button", { name: "Reset to default" }));
    expect(points(card)).toEqual(DEFAULTS.prayers.benediction);
    // The button is disabled now: focus goes to the first point.
    await waitFor(() => expect(document.activeElement).toBe(within(card).getByRole("textbox", { name: "Point 1 of Benediction" })));
    expect(screen.getByRole("button", { name: "Benediction" })).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Reset to default" })).toBeDisabled();
    expect(patches(api)).toHaveLength(0);
    await user.click(screen.getByRole("button", { name: "Save rubric" }));
    await screen.findByText(RUBRIC_SAVED);
    expect(patches(api)[0].body).toEqual({ prayers: { benediction: null } });
  });

  it("sends only the year and refreshes the hymn lists; a year out of range is named and blocks Save", async () => {
    const { api, user, queryClient } = renderPage("admin", { "PATCH /rubric": () => rubric({ prefer_before_year: 1900 }) });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const year = await screen.findByLabelText("Prefer hymns written before");
    const save = screen.getByRole("button", { name: "Save rubric" });
    for (const bad of ["1499", String(THIS_YEAR + 1)]) {
      await user.clear(year);
      await user.type(year, bad);
      expect(screen.getByText(`The preferred year must be between 1500 and ${THIS_YEAR}.`)).toBeInTheDocument();
      expect(year).toHaveAttribute("aria-invalid", "true");
      expect(save).toBeDisabled();
    }
    await user.clear(year);
    await user.type(year, "1900");
    expect(screen.queryByText(/The preferred year must be/)).toBeNull();
    await user.click(save);
    await screen.findByText(RUBRIC_SAVED);
    expect(patches(api)[0].body).toEqual({ prefer_before_year: 1900 });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["church", church().id, "hymns"] });
  });

  it("names a partial year only once the box loses focus, and blocks Save meanwhile", async () => {
    const { user } = renderPage("admin");
    const year = await screen.findByLabelText("Prefer hymns written before");
    const save = screen.getByRole("button", { name: "Save rubric" });
    await user.clear(year);
    await user.type(year, "18");
    expect(screen.queryByText(/The preferred year must be/)).toBeNull();
    expect(year).not.toHaveAttribute("aria-invalid");
    expect(save).toBeDisabled();
    await user.tab();
    expect(screen.getByText(`The preferred year must be between 1500 and ${THIS_YEAR}.`)).toBeInTheDocument();
    expect(year).toHaveAttribute("aria-invalid", "true");
    await user.type(year, "50");
    expect(year).toHaveValue("1850");
    expect(screen.queryByText(/The preferred year must be/)).toBeNull();
    expect(save).toBeEnabled();
  });

  it("adds a point below on Enter, keeps a pasted line break as a space, stops at 12, and needs one point", async () => {
    const eleven: RubricValues["hymns"] = { closing: Array.from({ length: 11 }, (_, i) => `Point ${i + 1}`) };
    const { api, user } = renderPage("admin", { "GET /rubric": rubric({ hymns: eleven }) });
    const card = await openCard(user, "Closing (Sending) Hymn");
    const first = within(card).getByRole("textbox", { name: "Point 1 of Closing (Sending) Hymn" });
    await user.click(first);
    await user.keyboard("{End}{Enter}");
    const added = within(card).getByRole("textbox", { name: "Point 2 of Closing (Sending) Hymn" });
    await waitFor(() => expect(added).toHaveFocus());
    expect(points(card)).toEqual(["Point 1", "", ...eleven.closing!.slice(1)]);
    fireEvent.change(added, { target: { value: "Joyful\nand sending" } });
    expect(added).toHaveValue("Joyful and sending");
    expect(within(card).getByRole("button", { name: "Add a point" })).toBeDisabled();
    expect(within(card).getByText("A checklist can have at most 12 points.")).toBeInTheDocument();
    await user.keyboard("{Enter}");
    expect(points(card)).toHaveLength(12);
    for (let n = 12; n >= 1; n -= 1) {
      await user.click(within(card).getByRole("button", { name: `Remove point ${n} from Closing (Sending) Hymn` }));
    }
    expect(within(card).getByText(KEEP_ONE_POINT)).toBeInTheDocument();
    await waitFor(() => expect(within(card).getByRole("button", { name: "Add a point" })).toHaveFocus());
    expect(screen.getByRole("button", { name: "Save rubric" })).toBeDisabled();
    await user.click(within(card).getByRole("button", { name: "Add a point" }));
    await user.keyboard("Ends in hope");
    await user.click(screen.getByRole("button", { name: "Save rubric" }));
    await screen.findByText(RUBRIC_SAVED);
    expect(patches(api)[0].body).toEqual({ hymns: { closing: ["Ends in hope"] } });
  });

  it("shows the theme note under the Opening and Closing cards only, even while they are closed", async () => {
    renderPage("admin");
    const opening = await cardButton("Opening (Gathering) Hymn");
    expect(opening).toHaveAttribute("aria-expanded", "false"); // a phone: every card starts closed
    const notes = screen.getAllByText(THEME_NOTE);
    expect(notes).toHaveLength(2);
    expect(notes[0].previousElementSibling).toContainElement(opening);
    expect(notes[1].previousElementSibling).toContainElement(await cardButton("Closing (Sending) Hymn"));
  });

  it("shows the server's 422 above the footer, keeps the edits and toasts nothing", async () => {
    const message = "Checklist points cannot contain control characters.";
    const { user } = renderPage("admin", { "PATCH /rubric": fakeError(422, "invalid_rubric", message) });
    const card = await openCard(user, "Benediction");
    await user.type(within(card).getByRole("textbox", { name: "Point 1 of Benediction" }), "!");
    await user.click(screen.getByRole("button", { name: "Save rubric" }));
    const alert = await screen.findByText(message);
    await waitFor(() => expect(alert.closest("[data-slot=alert]")).toHaveFocus());
    expect(alert.closest("[data-slot=alert]")!.nextElementSibling).toContainElement(screen.getByRole("button", { name: "Save rubric" }));
    expect(points(card)[0]).toBe("Benediction point one!");
    expect(document.querySelector("[data-sonner-toast]")).toBeNull();
  });

  it("asks before resetting everything, sends null for each customized item, cannot be closed while it runs", async () => {
    let finish: (value: unknown) => void = () => {};
    const { api, user } = renderPage("admin", {
      "GET /rubric": rubric({ hymns: { closing: ["Ours."] }, prefer_familiar: false }),
      "PATCH /rubric": () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    });
    await user.click(await screen.findByRole("button", { name: "Reset all to defaults" }));
    const dialog = await screen.findByRole("alertdialog", { name: RESET_ALL_TITLE });
    expect(dialog).toHaveTextContent("Your church's checklists and preferences go back to the shared defaults.");
    await user.click(within(dialog).getByRole("button", { name: "Reset all" }));
    await user.keyboard("{Escape}");
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(screen.getByRole("alertdialog", { name: RESET_ALL_TITLE })).toBeInTheDocument();
    expect(patches(api)[0].body).toEqual({ hymns: { closing: null }, prefer_familiar: null });
    finish(rubric());
    expect(await screen.findByText(RUBRIC_RESET)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(screen.getByRole("switch", { name: "Prefer familiar hymns" })).toBeChecked();
    expect(screen.queryByRole("button", { name: "Reset all to defaults" })).toBeNull();
    await waitFor(() => expect(screen.getByRole("heading", { name: "Service rubric" })).toHaveFocus());
  });

  it("toasts a role 403, refetches the profile and does not report the church as lost", async () => {
    const lost = vi.fn();
    const off = authEvents.onChurchAccessLost(lost);
    const { user, queryClient } = renderPage("admin", { "PATCH /rubric": fakeError(403, "forbidden", "Only church admins can do this.") });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    await user.click(await screen.findByRole("switch", { name: "Prefer familiar hymns" }));
    await user.click(screen.getByRole("button", { name: "Save rubric" }));
    expect(await screen.findByText("Only church admins can do this.")).toBeInTheDocument();
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.churchProfile(church().id) });
    expect(lost).not.toHaveBeenCalled();
    off();
  });

  it("rebases on newer data and asks before leaving with unsaved edits", async () => {
    const { user, queryClient } = renderPage("admin");
    const year = await screen.findByLabelText("Prefer hymns written before");
    await user.click(screen.getByRole("switch", { name: "Prefer familiar hymns" }));
    queryClient.setQueryData(keys.rubric(church().id), rubric({ prefer_before_year: 1900 }));
    await waitFor(() => expect(year).toHaveValue("1900"));
    expect(screen.getByRole("switch", { name: "Prefer familiar hymns" })).not.toBeChecked();
    await user.click(screen.getByRole("link", { name: "Contacts" }));
    const dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Discard changes" }));
    expect(testRouter.push).toHaveBeenCalledWith("/settings/contacts");
  });

  it("lets the footer sit after the cards while the phone keyboard is open", async () => {
    const { user } = renderPage("admin");
    const footer = (await screen.findByRole("button", { name: "Save rubric" })).parentElement!;
    expect(footer).toHaveClass("sticky", "bottom-0");
    expect(footer).not.toHaveAttribute("data-keyboard-open");
    await user.click(screen.getByLabelText("Prefer hymns written before"));
    expect(footer).toHaveAttribute("data-keyboard-open");
    expect(footer).toHaveClass("max-md:static");
  });

  it("shows the error state with Retry when the rubric cannot be read", async () => {
    renderPage("admin", { "GET /rubric": fakeError(500, "internal_error", "Something went wrong.") });
    expect(await screen.findByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});

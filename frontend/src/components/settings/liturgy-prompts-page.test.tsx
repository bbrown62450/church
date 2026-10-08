/**
 * Settings → Liturgy prompts (slice 6a-3a; 6a spec UX §3): every member reads
 * the prompts, owners and admins edit, reset and save them. Rendered inside
 * the Settings layout, as the route is, with a Toaster. Below `md` (jsdom's
 * matchMedia never matches) every card starts closed.
 */
import { screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, describe, expect, it, vi } from "vitest";

import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
import LiturgySettingsRoute from "@/app/(signed-in)/(church)/settings/liturgy/page";
import { DISCARD_TITLE } from "@/components/app/leave-guard";
import { Toaster } from "@/components/ui/sonner";
import type { Church, PromptKey } from "@/lib/api/types";
import { authEvents } from "@/lib/queries/auth-events";
import { keys } from "@/lib/queries/keys";
import { PROMPTS_RESET, PROMPTS_SAVED } from "@/lib/queries/liturgy-prompts";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { church, DEFAULT_PROMPTS, liturgyPrompts, me } from "@/test/fixtures";
import { testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";
import { positionAt, setViewport } from "@/test/viewport";

import { ADMINS_ONLY, BRACE_NOTE, PROMPTS_INTRO, RESET_ALL_TITLE, SYSTEM_NOTE } from "./liturgy-prompts-page";

afterEach(() => {
  toast.dismiss();
});

/** A fake `/church/liturgy-prompts`: `PUT` stores what it is sent, and `GET` answers with it, as the server does. */
function promptsServer(initial: Partial<Record<PromptKey, string>> = {}) {
  let stored = { ...initial };
  return {
    get: () => liturgyPrompts(stored),
    put: (req: RecordedRequest) => {
      stored = { ...(req.body as { prompts: Record<PromptKey, string> }).prompts };
      return liturgyPrompts(stored);
    },
  };
}

function renderPage(role: Church["role"] = "admin", routes: Record<string, FakeHandler> = {}) {
  const active = church({ role });
  const api = installFakeApi({ "GET /church/liturgy-prompts": liturgyPrompts(), ...routes });
  const view = renderWithProviders(
    <>
      <SettingsLayout>
        <LiturgySettingsRoute />
      </SettingsLayout>
      <Toaster />
    </>,
    { me: me({ churches: [active] }), church: active, path: "/settings/liturgy" },
  );
  return { ...view, api };
}

function puts(api: { requests: RecordedRequest[] }) {
  return api.requests.filter((r) => r.method === "PUT" && r.path === "/church/liturgy-prompts");
}

/** A card's header button: its title, then "Customized" when it is. */
function cardButton(title: string) {
  return screen.findByRole("button", { name: new RegExp(`^${title.replace(/[()]/g, "\\$&")}( Customized)?$`) });
}

/** Opens a card (they start closed on a phone) and returns its box. */
async function openCard(user: ReturnType<typeof renderPage>["user"], title: string) {
  await user.click(await cardButton(title));
  return screen.findByRole("textbox", { name: title });
}

describe("Settings → Liturgy prompts (slice 6a-3a)", () => {
  it("shows a member every prompt read-only, with the note, the help in its place and no controls", async () => {
    const { user } = renderPage("member", { "GET /church/liturgy-prompts": liturgyPrompts({ benediction: "Go in peace." }, { can_edit: false }) });
    expect(await screen.findByText(ADMINS_ONLY)).toBeInTheDocument();
    expect(screen.getByText(PROMPTS_INTRO)).toBeInTheDocument();
    const titles = screen.getAllByRole("button", { name: /./ }).map((b) => b.textContent);
    expect(titles).toEqual([
      "Overall voice (system prompt)",
      "Call to Worship",
      "Opening Prayer",
      "Prayer of Confession",
      "Assurance of Pardon",
      "Prayer for Illumination",
      "Prayers of the People",
      "Offertory Prayer",
      "BenedictionCustomized",
    ]);
    const system = await openCard(user, "Overall voice (system prompt)");
    expect(system).toHaveAttribute("readonly");
    expect(system).toHaveValue(DEFAULT_PROMPTS.system);
    expect(system).toHaveAccessibleDescription(SYSTEM_NOTE);
    const benediction = await openCard(user, "Benediction");
    expect(benediction).toHaveValue("Go in peace.");
    expect(benediction).toHaveAttribute("readonly");
    const help = screen.getByText(/^Placeholders you can use/);
    expect(help.textContent).toMatch(new RegExp(`ignored \\(they render as blank\\)\\. ${BRACE_NOTE.replace(/[{}.]/g, "\\$&")}$`));
    expect(help.previousElementSibling).toHaveTextContent("Section prompts");
    expect(screen.queryByRole("button", { name: "Reset to default" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Save prompts" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Reset all to defaults" })).toBeNull();
  });

  it("opens every card on a wide screen", async () => {
    const wide = vi.spyOn(window, "matchMedia").mockImplementation(
      (query) => ({ matches: true, media: query, addEventListener: () => {}, removeEventListener: () => {} }) as unknown as MediaQueryList,
    );
    try {
      renderPage("admin");
      await screen.findByRole("textbox", { name: "Overall voice (system prompt)" });
      expect(screen.getAllByRole("textbox")).toHaveLength(9);
    } finally {
      wide.mockRestore(); // even when the test fails: a spy left in place would open every card after it
    }
  });

  it("marks a changed card Customized, puts its default back, and saves only the church's own wording", async () => {
    const server = promptsServer();
    const { api, user } = renderPage("admin", { "GET /church/liturgy-prompts": server.get, "PUT /church/liturgy-prompts": server.put });
    const save = await screen.findByRole("button", { name: "Save prompts" });
    expect(save).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Reset all to defaults" })).toBeNull();
    const benediction = await openCard(user, "Benediction");
    const reset = within(benediction.closest("[data-slot=collapsible]") as HTMLElement).getByRole("button", { name: "Reset to default" });
    expect(reset).toBeDisabled();
    await user.type(benediction, " Amen.");
    expect(screen.getByRole("button", { name: /^Benediction/ })).toHaveTextContent("BenedictionCustomized");
    await user.click(reset);
    expect(benediction).toHaveValue(DEFAULT_PROMPTS.benediction);
    expect(document.activeElement).toBe(benediction); // the button is disabled now: focus is in the box
    expect(screen.getByRole("button", { name: /^Benediction/ })).toHaveTextContent(/^Benediction$/);
    expect(save).toBeDisabled();
    await user.clear(benediction);
    await user.type(benediction, "  Go in peace.  ");
    const confession = await openCard(user, "Prayer of Confession");
    await user.type(confession, " ");
    await user.click(save);
    expect(await screen.findByText(PROMPTS_SAVED)).toBeInTheDocument();
    expect(puts(api)).toHaveLength(1);
    expect(puts(api)[0].body).toEqual({ prompts: { benediction: "Go in peace." } });
    expect(puts(api)[0].headers["x-church-id"]).toBe(church().id);
    await waitFor(() => expect(save).toBeDisabled());
    expect(benediction).toHaveValue("Go in peace.");
    expect(screen.getByRole("button", { name: "Reset all to defaults" })).toBeInTheDocument();
  });

  it("opens and focuses the card a 422 names, with its message, and saves nothing", async () => {
    const message = "Benediction prompt: It has a { or } without a partner. Use {{ or }} to print a brace.";
    const { user } = renderPage("admin", {
      "PUT /church/liturgy-prompts": fakeError(422, "prompt_invalid", message, { fields: { "prompts.benediction": message } }),
    });
    const benediction = await openCard(user, "Benediction");
    await user.type(benediction, " {{");
    await user.click(screen.getByRole("button", { name: /^Benediction/ })); // closed again before saving
    expect(screen.queryByRole("textbox", { name: "Benediction" })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Save prompts" }));
    const box = await screen.findByRole("textbox", { name: "Benediction" });
    await waitFor(() => expect(box).toHaveFocus());
    expect(box).toHaveAttribute("aria-invalid", "true");
    expect(box).toHaveAccessibleDescription(message);
    expect(screen.queryByText(PROMPTS_SAVED)).toBeNull();
    await user.type(box, "x");
    expect(screen.queryByText(message)).toBeNull();
  });

  it("toasts a refusal that names no card, and keeps the edits", async () => {
    const { user } = renderPage("admin", {
      "PUT /church/liturgy-prompts": fakeError(422, "invalid_request", "The request was not valid.", {
        fields: { "prompts.sermon.[key]": "Not a valid value." },
      }),
    });
    const offertory = await openCard(user, "Offertory Prayer");
    await user.type(offertory, " Amen.");
    await user.click(screen.getByRole("button", { name: "Save prompts" }));
    expect(await screen.findByText("The request was not valid.")).toBeInTheDocument();
    expect(offertory).toHaveValue(`${DEFAULT_PROMPTS.offertory_prayer} Amen.`);
  });

  it("asks before resetting everything, cannot be closed while it runs, and then shows the defaults", async () => {
    let finish: (value: unknown) => void = () => {};
    const { api, user } = renderPage("admin", {
      "GET /church/liturgy-prompts": liturgyPrompts({ system: "Our own voice.", benediction: "Go in peace." }),
      "PUT /church/liturgy-prompts": () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    });
    const benediction = await openCard(user, "Benediction");
    await user.type(benediction, " Amen.");
    await user.click(screen.getByRole("button", { name: "Reset all to defaults" }));
    const dialog = await screen.findByRole("alertdialog", { name: RESET_ALL_TITLE });
    expect(dialog).toHaveTextContent("Your church's custom wording will be removed and the shared defaults used.");
    await user.click(within(dialog).getByRole("button", { name: "Reset all" }));
    await user.keyboard("{Escape}");
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(screen.getByRole("alertdialog", { name: RESET_ALL_TITLE })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save prompts", hidden: true })).toBeDisabled();
    expect(puts(api)[0].body).toEqual({ prompts: {} });
    finish(liturgyPrompts());
    expect(await screen.findByText(PROMPTS_RESET)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(benediction).toHaveValue(DEFAULT_PROMPTS.benediction);
    expect(screen.queryByRole("button", { name: "Reset all to defaults" })).toBeNull();
    await waitFor(() => expect(screen.getByRole("heading", { name: "Liturgy prompts" })).toHaveFocus());
  });

  it("rebases on newer data: another admin's change shows in an untouched card, and the edited card is kept", async () => {
    const { api, user, queryClient } = renderPage("admin", { "PUT /church/liturgy-prompts": promptsServer().put });
    const system = await openCard(user, "Overall voice (system prompt)");
    const benediction = await openCard(user, "Benediction");
    await user.type(benediction, " Amen.");
    queryClient.setQueryData(keys.liturgyPrompts(church().id), liturgyPrompts({ system: "Another admin's voice." }));
    await waitFor(() => expect(system).toHaveValue("Another admin's voice."));
    expect(benediction).toHaveValue(`${DEFAULT_PROMPTS.benediction} Amen.`);
    await user.click(screen.getByRole("button", { name: "Save prompts" }));
    await screen.findByText(PROMPTS_SAVED);
    expect(puts(api)[0].body).toEqual({
      prompts: { system: "Another admin's voice.", benediction: `${DEFAULT_PROMPTS.benediction} Amen.` },
    });
  });

  it("toasts a role 403, refetches the profile and does not report the church as lost", async () => {
    const lost = vi.fn();
    const off = authEvents.onChurchAccessLost(lost);
    const { user, queryClient } = renderPage("admin", {
      "PUT /church/liturgy-prompts": fakeError(403, "forbidden", "Only church admins can do this."),
    });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    await user.type(await openCard(user, "Benediction"), " Amen.");
    await user.click(screen.getByRole("button", { name: "Save prompts" }));
    expect(await screen.findByText("Only church admins can do this.")).toBeInTheDocument();
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.churchProfile(church().id) });
    expect(lost).not.toHaveBeenCalled();
    off();
  });

  it("asks before leaving with unsaved edits, through the Settings nav", async () => {
    const { user } = renderPage("admin");
    const contacts = await screen.findByRole("link", { name: "Contacts" });
    const benediction = await openCard(user, "Benediction");
    await user.type(benediction, " Amen.");
    await user.click(contacts);
    let dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Keep editing" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(benediction).toHaveValue(`${DEFAULT_PROMPTS.benediction} Amen.`);
    expect(testRouter.push).not.toHaveBeenCalled();
    await user.click(contacts);
    dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Discard changes" }));
    expect(testRouter.push).toHaveBeenCalledWith("/settings/contacts");
  });

  it("lets the footer sit after the cards while the keyboard is open on a phone held sideways (900x400)", async () => {
    // 6a-3a build review 2: an iPhone in landscape is 844-932px wide, above md, and its keyboard leaves little room.
    const restore = setViewport(900, 400);
    try {
      const { user } = renderPage("admin");
      const footer = (await screen.findByRole("button", { name: "Save prompts" })).parentElement!;
      expect(positionAt(footer)).toBe("sticky");
      await user.click(screen.getByRole("textbox", { name: "Benediction" }));
      expect(footer).toHaveAttribute("data-keyboard-open");
      expect(positionAt(footer)).toBe("static");
    } finally {
      restore();
    }
  });

  it("lets the footer sit after the cards while the phone keyboard is open", async () => {
    const { user } = renderPage("admin");
    const footer = (await screen.findByRole("button", { name: "Save prompts" })).parentElement!;
    expect(footer).toHaveClass("sticky", "bottom-0");
    expect(positionAt(footer, 390)).toBe("sticky");
    expect(footer).not.toHaveAttribute("data-keyboard-open");
    await user.click(await openCard(user, "Benediction"));
    expect(footer).toHaveAttribute("data-keyboard-open");
    expect(positionAt(footer, 390)).toBe("static");
  });

  it("shows the error state with Retry when the prompts cannot be read", async () => {
    renderPage("admin", { "GET /church/liturgy-prompts": fakeError(500, "internal_error", "Something went wrong.") });
    expect(await screen.findByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});

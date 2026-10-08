/**
 * Settings → Prayers (slice 6a-3b; prayer library spec "Prayers page (slice
 * 6a)"; 6a spec UX §5): every member reads the library, owners and admins add,
 * edit, remove and save prayers and the voice profile together. Rendered inside
 * the Settings layout, as the route is, with a Toaster.
 */
import { act, screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, describe, expect, it, vi } from "vitest";

import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
import PrayersSettingsRoute from "@/app/(signed-in)/(church)/settings/prayers/page";
import { DISCARD_TITLE } from "@/components/app/leave-guard";
import { STILL_WORKING } from "@/components/settings/hymnals-card";
import { Toaster } from "@/components/ui/sonner";
import type { Church, PrayerLibrary, PrayerLibraryBody } from "@/lib/api/types";
import { authEvents } from "@/lib/queries/auth-events";
import { keys } from "@/lib/queries/keys";
import { LIBRARY_SAVED } from "@/lib/queries/prayer-library";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { church, me, prayer, prayerLibrary } from "@/test/fixtures";
import { testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";
import { positionAt, setViewport } from "@/test/viewport";

import { ADMINS_ONLY, EMPTY_LIBRARY, PRAYERS_INTRO, REMOVE_TITLE } from "./prayers-settings-page";
import { DRAFT_TITLE, NO_SAVED_PRAYERS, SAVE_FIRST, WRITE_IT_YOURSELF } from "./voice-profile-card";

afterEach(() => {
  toast.dismiss();
});

const CONFESSION = prayer(1);
const BENEDICTION = prayer(2, { type: "benediction", text: "Go in peace.\nServe the Lord." });

/** A fake `/church/prayer-library`: `PUT` stores what it is sent (new prayers get ids), and `GET` answers with it. */
function libraryServer(initial: PrayerLibrary = prayerLibrary([CONFESSION, BENEDICTION], { voice_profile: "Warm and plain." })) {
  let stored = initial;
  let made = 10;
  return {
    get: () => stored,
    put: (req: RecordedRequest) => {
      const body = req.body as PrayerLibraryBody;
      stored = prayerLibrary(
        body.prayers.map((p) => {
          const id = p.id ?? prayer((made += 1)).id;
          return { id, type: p.type as PrayerLibrary["prayers"][number]["type"], text: p.text, added_at: "2026-10-08T16:00:00Z" };
        }),
        { voice_profile: body.voice_profile },
      );
      return stored;
    },
  };
}

function renderPage(role: Church["role"] = "admin", routes: Record<string, FakeHandler> = {}) {
  const active = church({ role });
  const server = libraryServer();
  const api = installFakeApi({ "GET /church/prayer-library": server.get, "PUT /church/prayer-library": server.put, ...routes });
  const view = renderWithProviders(
    <>
      <SettingsLayout>
        <PrayersSettingsRoute />
      </SettingsLayout>
      <Toaster />
    </>,
    { me: me({ churches: [active] }), church: active, path: "/settings/prayers" },
  );
  return { ...view, api };
}

function puts(api: { requests: RecordedRequest[] }) {
  return api.requests.filter((r) => r.method === "PUT" && r.path === "/church/prayer-library");
}

function prayerItems() {
  return within(screen.getByRole("list", { name: "Prayers" })).getAllByRole("listitem");
}

async function chooseType(user: ReturnType<typeof renderPage>["user"], n: number, label: string) {
  await user.click(screen.getByRole("combobox", { name: `Type of prayer ${n}` }));
  await user.click(await screen.findByRole("option", { name: label }));
}

describe("Settings → Prayers (slice 6a-3b)", () => {
  it("shows a member the whole library read-only, with the note and no controls", async () => {
    renderPage("member", {
      "GET /church/prayer-library": prayerLibrary([CONFESSION, BENEDICTION], { voice_profile: "Warm and plain.", can_edit: false }),
    });
    expect(await screen.findByText(ADMINS_ONLY)).toBeInTheDocument();
    expect(screen.getByText(PRAYERS_INTRO)).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Voice profile" })).toHaveAttribute("readonly");
    expect(screen.getByRole("textbox", { name: "Voice profile" })).toHaveValue("Warm and plain.");
    expect(screen.getByText(PRAYERS_INTRO)).toHaveTextContent("Everyone in your church can read this page.");
    const items = within(screen.getByRole("list", { name: "Prayers" })).getAllByRole("listitem");
    expect(items.map((item) => item.firstChild?.textContent)).toEqual(["Prayer of Confession", "Benediction"]);
    expect(items[1]).toHaveTextContent("Go in peace. Serve the Lord.", { normalizeWhitespace: true });
    expect(items[1].lastChild).toHaveClass("min-w-0", "break-words", "whitespace-pre-wrap"); // a long word wraps at 375 px
    expect(within(screen.getByRole("form", { name: "Prayer library" })).queryAllByRole("button")).toEqual([]);
    expect(screen.queryByRole("combobox")).toBeNull();
  });

  it("shows the empty library and adds a first prayer, which saves with the profile", async () => {
    const { api, user } = renderPage("admin", { "GET /church/prayer-library": prayerLibrary() });
    expect(await screen.findByText(EMPTY_LIBRARY)).toBeInTheDocument();
    expect(screen.getByText(PRAYERS_INTRO)).toHaveTextContent("Everyone in your church can read this page.");
    const save = screen.getByRole("button", { name: "Save" });
    expect(save).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Add a prayer" }));
    expect(screen.getByRole("combobox", { name: "Type of prayer 1" })).toHaveFocus();
    expect(screen.queryByText(EMPTY_LIBRARY)).toBeNull();
    await chooseType(user, 1, "Benediction");
    await user.type(screen.getByRole("textbox", { name: "Prayer 1" }), "  Go in peace.");
    expect(prayerItems()[0].firstChild).toHaveTextContent(/^Go in peace\.$/); // the first line, as the row's summary
    await user.type(screen.getByRole("textbox", { name: "Voice profile" }), "Plain words.");
    await user.click(save);
    expect(await screen.findByText(LIBRARY_SAVED)).toBeInTheDocument();
    expect(puts(api)).toHaveLength(1);
    expect(puts(api)[0].body).toEqual({ prayers: [{ type: "benediction", text: "Go in peace." }], voice_profile: "Plain words." });
    expect(puts(api)[0].headers["x-church-id"]).toBe(church().id);
    await waitFor(() => expect(save).toBeDisabled());
    expect(screen.getByRole("textbox", { name: "Prayer 1" })).toHaveValue("Go in peace."); // still open, as stored
  });

  it("edits a saved prayer's type and text and sends every prayer back with its id", async () => {
    const { api, user } = renderPage("admin");
    const edit = await screen.findByRole("button", { name: "Edit prayer 2" });
    expect(edit).toHaveAttribute("aria-expanded", "false");
    await user.click(edit);
    expect(screen.getByRole("button", { name: "Close prayer 2" })).toHaveAttribute("aria-expanded", "true");
    const text = screen.getByRole("textbox", { name: "Prayer 2" });
    expect(text).toHaveValue("Go in peace.\nServe the Lord.");
    await user.clear(text);
    await user.type(text, "Go now in peace.");
    await chooseType(user, 2, "Offertory Prayer");
    await user.click(screen.getByRole("button", { name: "Save" }));
    await screen.findByText(LIBRARY_SAVED);
    expect(puts(api)[0].body).toEqual({
      prayers: [
        { id: CONFESSION.id, type: "prayer_of_confession", text: CONFESSION.text },
        { id: BENEDICTION.id, type: "offertory_prayer", text: "Go now in peace." },
      ],
      voice_profile: "Warm and plain.",
    });
  });

  it("asks before removing a prayer, puts focus on the next one, and the save leaves it out", async () => {
    const { api, user } = renderPage("admin");
    const remove = await screen.findByRole("button", { name: "Remove prayer 1" });
    await user.click(remove);
    let dialog = await screen.findByRole("alertdialog", { name: REMOVE_TITLE });
    expect(dialog).toHaveTextContent("It leaves your library when you save.");
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(prayerItems()).toHaveLength(2);
    await waitFor(() => expect(remove).toHaveFocus());
    await user.click(remove);
    dialog = await screen.findByRole("alertdialog", { name: REMOVE_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Remove prayer" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(prayerItems()).toHaveLength(1);
    await waitFor(() => expect(screen.getByRole("button", { name: "Edit prayer 1" })).toHaveFocus());
    await user.click(screen.getByRole("button", { name: "Save" }));
    await screen.findByText(LIBRARY_SAVED);
    expect(puts(api)[0].body).toEqual({
      prayers: [{ id: BENEDICTION.id, type: "benediction", text: BENEDICTION.text }],
      voice_profile: "Warm and plain.",
    });
  });

  it("checks a new prayer before sending: the type and the text, focusing the first, with nothing sent", async () => {
    const { api, user } = renderPage("admin");
    await user.click(await screen.findByRole("button", { name: "Add a prayer" }));
    await user.type(screen.getByRole("textbox", { name: "Prayer 3" }), "   ");
    await user.click(screen.getByRole("button", { name: "Save" }));
    const type = screen.getByRole("combobox", { name: "Type of prayer 3" });
    await waitFor(() => expect(type).toHaveFocus());
    expect(type).toHaveAttribute("aria-invalid", "true");
    expect(type).toHaveAccessibleDescription("Choose a prayer type.");
    expect(screen.getByRole("textbox", { name: "Prayer 3" })).toHaveAccessibleDescription("Prayer text is required.");
    await chooseType(user, 3, "Other");
    expect(screen.queryByText("Choose a prayer type.")).toBeNull();
    await user.click(screen.getByRole("textbox", { name: "Prayer 3" }));
    await user.paste("x".repeat(6_001));
    await user.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Prayer 3" })).toHaveFocus());
    expect(screen.getByText("This prayer is too long (6,000 characters at most).")).toBeInTheDocument();
    expect(puts(api)).toEqual([]);
  });

  it("shows a refusal under the row it names, opening and focusing it, and toasts one it cannot place", async () => {
    const message = "This prayer is too long (6,000 characters at most).";
    const { api, user } = renderPage("admin", {
      "PUT /church/prayer-library": fakeError(422, "invalid_request", message, { fields: { "prayers.1.text": message } }),
    });
    await user.type(await screen.findByRole("textbox", { name: "Voice profile" }), " Amen.");
    await user.click(screen.getByRole("button", { name: "Save" }));
    const text = await screen.findByRole("textbox", { name: "Prayer 2" });
    await waitFor(() => expect(text).toHaveFocus());
    expect(text).toHaveAccessibleDescription(message);
    expect(screen.queryByText(LIBRARY_SAVED)).toBeNull();
    await user.type(text, "x");
    expect(screen.queryByText(message)).toBeNull();
    api.set("PUT /church/prayer-library", fakeError(422, "invalid_request", "You can keep up to 30 prayers.", {
      fields: { prayers: "You can keep up to 30 prayers." },
    }));
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("You can keep up to 30 prayers.")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Voice profile" })).toHaveValue("Warm and plain. Amen.");
  });

  it("toasts a refusal naming a row that was removed while the save ran", async () => {
    const message = "This prayer is too long (6,000 characters at most).";
    let answer: (response: unknown) => void = () => {};
    const { api, user } = renderPage("admin", {
      "PUT /church/prayer-library": () => new Promise((resolve) => (answer = resolve)),
    });
    await user.type(await screen.findByRole("textbox", { name: "Voice profile" }), " Amen.");
    await user.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(puts(api)).toHaveLength(1));
    await user.click(screen.getByRole("button", { name: "Remove prayer 2" }));
    const dialog = await screen.findByRole("alertdialog", { name: REMOVE_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Remove prayer" }));
    await waitFor(() => expect(prayerItems()).toHaveLength(1));
    answer(fakeError(422, "invalid_request", message, { fields: { "prayers.1.text": message } }));
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: "Prayer 2" })).toBeNull();
    expect(screen.getByRole("textbox", { name: "Voice profile" })).toHaveValue("Warm and plain. Amen.");
  });

  it("toasts a role 403, refetches the profile and does not report the church as lost", async () => {
    const lost = vi.fn();
    const off = authEvents.onChurchAccessLost(lost);
    const { user, queryClient } = renderPage("admin", {
      "PUT /church/prayer-library": fakeError(403, "forbidden", "Only church admins can do this."),
    });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    await user.type(await screen.findByRole("textbox", { name: "Voice profile" }), " Amen.");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("Only church admins can do this.")).toBeInTheDocument();
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.churchProfile(church().id) });
    expect(lost).not.toHaveBeenCalled();
    off();
  });

  it("rebases on newer data: another admin's profile shows when untouched, and an edited list is kept", async () => {
    const { api, user, queryClient } = renderPage("admin");
    await user.click(await screen.findByRole("button", { name: "Edit prayer 1" }));
    await user.type(screen.getByRole("textbox", { name: "Prayer 1" }), " Amen.");
    queryClient.setQueryData(keys.prayerLibrary(church().id), prayerLibrary([BENEDICTION], { voice_profile: "Another admin's profile." }));
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Voice profile" })).toHaveValue("Another admin's profile."));
    expect(prayerItems()).toHaveLength(2);
    await user.click(screen.getByRole("button", { name: "Save" }));
    await screen.findByText(LIBRARY_SAVED);
    expect(puts(api)[0].body).toEqual({
      prayers: [
        { id: CONFESSION.id, type: "prayer_of_confession", text: `${CONFESSION.text} Amen.` },
        { id: BENEDICTION.id, type: "benediction", text: BENEDICTION.text },
      ],
      voice_profile: "Another admin's profile.",
    });
  });

  it("asks before leaving with unsaved edits, through the Settings nav", async () => {
    const { user } = renderPage("admin");
    const contacts = await screen.findByRole("link", { name: "Contacts" });
    await user.type(await screen.findByRole("textbox", { name: "Voice profile" }), " Amen.");
    await user.click(contacts);
    let dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Keep editing" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(testRouter.push).not.toHaveBeenCalled();
    await user.click(contacts);
    dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Discard changes" }));
    expect(testRouter.push).toHaveBeenCalledWith("/settings/contacts");
  });

  it("holds Add a prayer at 30, with the server's words", async () => {
    const thirty = Array.from({ length: 30 }, (_, i) => prayer(i + 1));
    renderPage("admin", { "GET /church/prayer-library": prayerLibrary(thirty) });
    expect(await screen.findByRole("button", { name: "Add a prayer" })).toBeDisabled();
    expect(screen.getByText("You can keep up to 30 prayers.")).toBeInTheDocument();
  });

  it("lets the Save bar sit after the list while a text box has focus, upright and sideways", async () => {
    const restore = setViewport(900, 400);
    try {
      const { user } = renderPage("admin");
      const footer = (await screen.findByRole("button", { name: "Save" })).parentElement!;
      expect(positionAt(footer)).toBe("sticky");
      expect(positionAt(footer, 390)).toBe("sticky");
      await user.click(screen.getByRole("textbox", { name: "Voice profile" }));
      expect(footer).toHaveAttribute("data-keyboard-open");
      expect(positionAt(footer)).toBe("static");
      expect(positionAt(footer, 390)).toBe("static");
    } finally {
      restore();
    }
  });

  it("shows the error state with Retry when the library cannot be read", async () => {
    renderPage("admin", { "GET /church/prayer-library": fakeError(500, "internal_error", "Something went wrong.") });
    expect(await screen.findByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});

describe("Settings → Prayers: the voice-profile draft (slice 6a-3b)", () => {
  const DRAFT_ROUTE = "POST /church/prayer-library/voice-profile-draft";

  function drafts(api: { requests: RecordedRequest[] }) {
    return api.requests.filter((r) => r.method === "POST" && r.path === "/church/prayer-library/voice-profile-draft");
  }

  it("asks for a draft only from saved prayers: Save your prayers first, or add one first", async () => {
    const { user } = renderPage("admin", { [DRAFT_ROUTE]: { draft: "x" } });
    const update = await screen.findByRole("button", { name: "Update from my prayers" });
    expect(update).toBeEnabled();
    await user.type(screen.getByRole("textbox", { name: "Voice profile" }), " Amen."); // the profile alone: still allowed
    expect(update).toBeEnabled();
    await user.click(screen.getByRole("button", { name: "Add a prayer" }));
    expect(update).toBeDisabled();
    expect(update).toHaveAccessibleDescription(SAVE_FIRST);
    await chooseType(user, 3, "Other");
    await user.type(screen.getByRole("textbox", { name: "Prayer 3" }), "Bless this meal.");
    await user.click(screen.getByRole("button", { name: "Save" }));
    await screen.findByText(LIBRARY_SAVED);
    await waitFor(() => expect(update).toBeEnabled());
    expect(screen.queryByText(SAVE_FIRST)).toBeNull();
  });

  it("says to add and save a prayer first when none is saved, and shows a member no button", async () => {
    const { unmount } = renderPage("admin", { "GET /church/prayer-library": prayerLibrary() });
    const update = await screen.findByRole("button", { name: "Update from my prayers" });
    expect(update).toBeDisabled();
    expect(update).toHaveAccessibleDescription(NO_SAVED_PRAYERS);
    unmount();
    renderPage("member", { "GET /church/prayer-library": prayerLibrary([CONFESSION], { can_edit: false }) });
    await screen.findByText(ADMINS_ONLY);
    expect(screen.queryByRole("button", { name: "Update from my prayers" })).toBeNull();
  });

  it("shows the draft beside the profile as text, and Use this draft puts it in the box to save", async () => {
    const answer = "Warm and <b>plain</b>.\nShort sentences.";
    const { api, user } = renderPage("admin", { [DRAFT_ROUTE]: { draft: answer } });
    await user.click(await screen.findByRole("button", { name: "Update from my prayers" }));
    const title = await screen.findByRole("heading", { name: DRAFT_TITLE });
    await waitFor(() => expect(title).toHaveFocus());
    const panel = title.closest("section")!;
    expect(panel).toHaveTextContent("Warm and <b>plain</b>. Short sentences.", { normalizeWhitespace: true });
    expect(document.body).not.toHaveTextContent("\u2014"); // no em dash in anything the page shows
    expect(panel.querySelector("b")).toBeNull(); // the AI's answer is text, never markup
    expect(screen.getByRole("textbox", { name: "Voice profile" })).toHaveValue("Warm and plain."); // not replaced yet
    expect(drafts(api)).toHaveLength(1);
    await user.click(within(panel).getByRole("button", { name: "Use this draft" }));
    const box = screen.getByRole("textbox", { name: "Voice profile" });
    expect(box).toHaveValue(answer);
    expect(box).toHaveFocus();
    expect(screen.queryByRole("heading", { name: DRAFT_TITLE })).toBeNull();
    await user.type(box, " Amen.");
    await user.click(screen.getByRole("button", { name: "Save" }));
    await screen.findByText(LIBRARY_SAVED);
    expect(puts(api)[0].body).toMatchObject({ voice_profile: `${answer} Amen.` });
  });

  it("Keep mine leaves the profile as it was and puts focus back on the button", async () => {
    const { api, user } = renderPage("admin", { [DRAFT_ROUTE]: { draft: "A different voice." } });
    const update = await screen.findByRole("button", { name: "Update from my prayers" });
    await user.click(update);
    const title = await screen.findByRole("heading", { name: DRAFT_TITLE });
    await user.click(within(title.closest("section")!).getByRole("button", { name: "Keep mine" }));
    expect(screen.queryByRole("heading", { name: DRAFT_TITLE })).toBeNull();
    expect(screen.getByRole("textbox", { name: "Voice profile" })).toHaveValue("Warm and plain.");
    expect(update).toHaveFocus();
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
    expect(puts(api)).toEqual([]);
  });

  it("keeps focus in a prayer being typed in when the draft arrives, and says the draft is there", async () => {
    let answer: (response: unknown) => void = () => {};
    const { user } = renderPage("admin", { [DRAFT_ROUTE]: () => new Promise((resolve) => (answer = resolve)) });
    await user.click(await screen.findByRole("button", { name: "Edit prayer 1" }));
    await user.click(screen.getByRole("button", { name: "Update from my prayers" }));
    const box = screen.getByRole("textbox", { name: "Prayer 1" });
    await user.type(box, " Amen.");
    answer({ draft: "A warm, plain voice." });
    const title = await screen.findByRole("heading", { name: DRAFT_TITLE });
    expect(box).toHaveFocus();
    expect(title).not.toHaveFocus();
    const status = document.getElementById("voice-draft-status")!;
    expect(status).toHaveAttribute("aria-live", "polite");
    expect(status).toHaveTextContent(DRAFT_TITLE);
    expect(document.body).not.toHaveTextContent("\u2014");
  });

  it("says it is still working after 8 s, and Cancel stops the wait with nothing shown", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true, toFake: ["setTimeout", "clearTimeout"] });
    try {
      const { user } = renderPage("admin", { [DRAFT_ROUTE]: () => new Promise(() => {}) });
      const update = await screen.findByRole("button", { name: "Update from my prayers" });
      await user.click(update);
      expect(update).toHaveTextContent("Drafting…");
      expect(screen.queryByText(STILL_WORKING)).toBeNull();
      act(() => {
        vi.advanceTimersByTime(8_000);
      });
      expect(await screen.findByText(STILL_WORKING)).toBeInTheDocument();
      expect(document.body).not.toHaveTextContent("\u2014");
      await user.click(screen.getByRole("button", { name: "Cancel" }));
      await waitFor(() => expect(update).toHaveTextContent("Update from my prayers"));
      expect(update).toHaveFocus();
      expect(vi.mocked(fetch).mock.calls.at(-1)![1]!.signal!.aborted).toBe(true);
      expect(screen.queryByText(STILL_WORKING)).toBeNull();
      expect(screen.queryByRole("alert")).toBeNull();
      expect(screen.queryByRole("heading", { name: DRAFT_TITLE })).toBeNull();
    } finally {
      vi.useRealTimers();
    }
  });

  it("stops the wait when the page is left", async () => {
    const { user, unmount } = renderPage("admin", { [DRAFT_ROUTE]: () => new Promise(() => {}) });
    await user.click(await screen.findByRole("button", { name: "Update from my prayers" }));
    const signal = vi.mocked(fetch).mock.calls.at(-1)![1]!.signal!;
    expect(signal.aborted).toBe(false);
    unmount();
    expect(signal.aborted).toBe(true);
  });

  it("shows why a draft failed in the card, and toasts a role 403 instead", async () => {
    const { api, user } = renderPage("admin", {
      [DRAFT_ROUTE]: fakeError(503, "ai_not_configured", "AI isn't set up on this app yet."),
    });
    const update = await screen.findByRole("button", { name: "Update from my prayers" });
    await user.click(update);
    expect(await screen.findByRole("alert")).toHaveTextContent(`AI isn't set up on this app yet. ${WRITE_IT_YOURSELF}`);
    api.set(DRAFT_ROUTE, fakeError(429, "rate_limited", "Too many requests. Try again in 15 seconds.", { details: { retry_after_seconds: 15 } }));
    await user.click(update);
    expect(await screen.findByRole("alert")).toHaveTextContent("Too many requests. Try again in 15 seconds.");
    api.set(DRAFT_ROUTE, fakeError(403, "forbidden", "Only church admins can do this."));
    await user.click(update);
    expect(await screen.findByText("Only church admins can do this.")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.getByRole("textbox", { name: "Voice profile" })).toHaveValue("Warm and plain.");
  });
});

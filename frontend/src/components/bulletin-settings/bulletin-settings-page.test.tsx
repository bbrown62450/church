/**
 * The Bulletin settings page (printed bulletin spec, PR 2a; PR 2 planning
 * answers 1-3): admins edit and save the whole form, members read a summary.
 * Since slice 6a-3a it is Settings → Bulletin, so it renders inside the
 * Settings layout, as the route does, with a Toaster.
 */
import { act, screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, describe, expect, it } from "vitest";

import BulletinSettingsRoute from "@/app/(signed-in)/(church)/settings/bulletin/page";
import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
import { Toaster } from "@/components/ui/sonner";
import type { BulletinSettings, Church } from "@/lib/api/types";
import { makeQueryClient } from "@/lib/queries/client";
import { SETTINGS_SAVED } from "@/lib/queries/bulletin-settings";
import { keys } from "@/lib/queries/keys";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { bulletinSettings, church, filledBulletinSettings, me } from "@/test/fixtures";
import { testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import { ADMINS_ONLY, DISCARD_TITLE } from "./bulletin-settings-page";

const PATH = "/church/bulletin-settings";

function renderPage(role: Church["role"] = "admin", routes: Record<string, FakeHandler> = {}, cached?: BulletinSettings) {
  const api = installFakeApi({ [`GET ${PATH}`]: filledBulletinSettings(), ...routes });
  const active = church({ role });
  const queryClient = makeQueryClient({ queries: { retry: false } });
  if (cached) queryClient.setQueryData(keys.bulletinSettings(active.id), cached);
  const view = renderWithProviders(
    <>
      <SettingsLayout>
        <BulletinSettingsRoute />
      </SettingsLayout>
      <Toaster />
    </>,
    { me: me({ churches: [active] }), church: active, path: "/settings/bulletin", queryClient },
  );
  return { ...view, api };
}

function puts(api: { requests: RecordedRequest[] }) {
  return api.requests.filter((r) => r.method === "PUT" && r.path === PATH);
}

function leaveWarned(): boolean {
  const event = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(event);
  return event.defaultPrevented;
}

/** What the page set `returnValue` to on a reload or close (undefined: not set). */
function leaveReturnValue(): unknown {
  const event = new Event("beforeunload", { cancelable: true });
  let set: unknown = undefined;
  Object.defineProperty(event, "returnValue", { configurable: true, get: () => set, set: (v) => (set = v) });
  window.dispatchEvent(event);
  return set;
}

/** Clicks `link` as `init` says; true when the page let the link do what a link does (not prevented). */
function clickFollowsLink(link: HTMLElement, init: MouseEventInit): boolean {
  let followed = false;
  const after = (event: Event) => {
    followed = !event.defaultPrevented;
    event.preventDefault(); // jsdom cannot navigate
  };
  window.addEventListener("click", after);
  try {
    act(() => {
      link.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, button: 0, ...init }));
    });
  } finally {
    window.removeEventListener("click", after);
  }
  return followed;
}

afterEach(() => {
  toast.dismiss();
});

describe("Bulletin settings (printed bulletin PR 2a)", () => {
  it("lets an admin change the details, who leads a part and the stars, and saves the whole form", async () => {
    const { api, user } = renderPage("admin", { [`PUT ${PATH}`]: (r: RecordedRequest) => r.body });
    const phone = await screen.findByLabelText("Phone");
    expect(phone).toHaveValue("(555) 010-0100");
    expect(phone).toHaveAttribute("inputmode", "tel");
    expect(screen.getByLabelText("Address")).toHaveValue("100 Example Street\nSpringfield, ST 00000");
    expect(screen.queryByText(ADMINS_ONLY)).toBeNull();
    await user.clear(phone);
    await user.clear(screen.getByLabelText("Service time"));
    await user.type(screen.getByLabelText("Service time"), "9:00 a.m.");
    await user.click(screen.getByRole("combobox", { name: "Sermon: led by" }));
    await user.click(await screen.findByRole("option", { name: "Organist" }));
    await user.click(screen.getByRole("switch", { name: "Prelude: congregation stands" }));
    await user.click(screen.getByRole("switch", { name: "Doxology: congregation stands" }));
    const save = screen.getByRole("button", { name: "Save settings" });
    expect(save).toHaveClass("h-11");
    await user.click(save);
    expect(await screen.findByText(SETTINGS_SAVED)).toBeInTheDocument();
    const expected = filledBulletinSettings({
      phone: "",
      service_time: "9:00 a.m.",
      starred: ["prelude", "first_hymn", "gloria_patri", "affirmation_of_faith", "second_hymn", "third_hymn", "benediction"],
      leaders: { ...bulletinSettings().leaders, sermon: "organist" },
    });
    expect(puts(api)).toHaveLength(1);
    expect(puts(api)[0].body).toEqual(expected);
    // The starred parts (toEqual checked their order) and the leaders in the printed order.
    expect(Object.keys((puts(api)[0].body as typeof expected).leaders)).toEqual(Object.keys(expected.leaders));
    expect(leaveWarned()).toBe(false); // saved: nothing to lose
  });

  it("shows a member the settings as plain text, with no fields and no Save", async () => {
    renderPage("member", { [`GET ${PATH}`]: filledBulletinSettings({ email: "" }) });
    expect(await screen.findByText(ADMINS_ONLY)).toBeInTheDocument();
    const main = screen.getByRole("main");
    // Each summary part is an h3 under the page's h2 "Bulletin settings".
    expect(within(main).getByRole("heading", { level: 2, name: "Bulletin settings" })).toBeInTheDocument();
    expect(within(main).getByRole("heading", { level: 3, name: "Church details" })).toBeInTheDocument();
    expect(within(main).getByText("(555) 010-0100")).toBeInTheDocument();
    expect(within(main).getByText("Not filled in")).toBeInTheDocument(); // the email
    expect(within(main).getByText("Sermon:").parentElement).toHaveTextContent("Sermon: Worship leader");
    expect(within(main).getByText("Opening hymn:").parentElement).toHaveTextContent(
      "Opening hymn: No one, congregation stands",
    );
    expect(within(main).queryAllByRole("textbox")).toEqual([]);
    expect(within(main).queryAllByRole("switch")).toEqual([]);
    expect(screen.queryByRole("button", { name: "Save settings" })).toBeNull();
  });

  it("checks the address before saving, and shows a field the server refuses as an error under it", async () => {
    const { api, user } = renderPage("admin", {
      [`PUT ${PATH}`]: fakeError(422, "invalid_request", "The request was not valid.", {
        fields: { phone: "Not a valid value." },
      }),
    });
    const address = await screen.findByLabelText("Address");
    await user.type(address, "\nLine three\nLine four");
    await user.click(screen.getByRole("button", { name: "Save settings" }));
    const problem = screen.getByRole("alert");
    expect(problem).toHaveTextContent("Use up to 3 lines of up to 60 characters each.");
    expect(problem).toHaveClass("text-destructive");
    expect(address).toHaveAttribute("aria-invalid", "true");
    expect(address).toHaveAccessibleDescription(
      "Up to 3 lines, as printed on the cover. Use up to 3 lines of up to 60 characters each.",
    );
    expect(address).toHaveFocus();
    expect(puts(api)).toEqual([]);
    await user.clear(address);
    await user.click(screen.getByRole("button", { name: "Save settings" }));
    expect(await screen.findByText("The request was not valid.")).toBeInTheDocument();
    const phone = screen.getByLabelText("Phone");
    await waitFor(() => expect(phone).toHaveAttribute("aria-invalid", "true"));
    expect(phone).toHaveAccessibleDescription("Not a valid value.");
    expect(phone).toHaveFocus();
    expect(address).not.toHaveAttribute("aria-invalid");
    expect((puts(api)[0].body as { address_lines: string[] }).address_lines).toEqual([]);
    expect(within(screen.getByRole("main")).getByRole("link", { name: "Back to the builder" })).toHaveAttribute(
      "href",
      "/builder",
    );
  });

  it("opens on the settings fetched now, and newer data updates only the fields not edited", async () => {
    const { api, user, queryClient } = renderPage(
      "admin",
      { [`PUT ${PATH}`]: (r: RecordedRequest) => r.body },
      bulletinSettings(), // an older copy in the cache
    );
    const phone = await screen.findByLabelText("Phone");
    expect(phone).toHaveValue("(555) 010-0100"); // not the cached blank
    await user.clear(phone);
    await user.type(phone, "(555) 010-0199");
    await user.click(screen.getByRole("switch", { name: "Prelude: congregation stands" }));
    // Meanwhile another admin saved a new organist, phone and stars.
    api.set(
      `GET ${PATH}`,
      filledBulletinSettings({ organist: "Pat Example", phone: "(555) 010-0155", starred: ["doxology"] }),
    );
    await act(() => queryClient.refetchQueries({ queryKey: keys.bulletinSettings(church().id) }));
    await waitFor(() => expect(screen.getByLabelText("Organist")).toHaveValue("Pat Example"));
    expect(phone).toHaveValue("(555) 010-0199");
    expect(screen.getByRole("switch", { name: "Prelude: congregation stands" })).toBeChecked();
    expect(screen.getByRole("switch", { name: "Doxology: congregation stands" })).toBeChecked();
    expect(screen.getByRole("switch", { name: "Sermon: congregation stands" })).not.toBeChecked();
    await user.click(screen.getByRole("button", { name: "Save settings" }));
    await waitFor(() => expect(puts(api)).toHaveLength(1));
    expect(puts(api)[0].body).toMatchObject({ organist: "Pat Example", phone: "(555) 010-0199", starred: ["prelude", "doxology"] });
  });

  it("keeps what is typed while saving, and shows what was stored everywhere else", async () => {
    let answer: (body: unknown) => void = () => {};
    const { api, user } = renderPage("admin", {
      [`PUT ${PATH}`]: () =>
        new Promise((resolve) => {
          answer = resolve;
        }),
    });
    const standNote = await screen.findByLabelText("Stand note");
    await user.clear(standNote);
    await user.type(standNote, "*Please stand if able");
    await user.click(screen.getByRole("button", { name: "Save settings" }));
    await waitFor(() => expect(puts(api)).toHaveLength(1));
    await user.type(screen.getByLabelText("Organist"), " Jr.");
    answer(filledBulletinSettings({ stand_note: "Please stand if able" })); // the server drops the star
    expect(await screen.findByText(SETTINGS_SAVED)).toBeInTheDocument();
    expect(standNote).toHaveValue("Please stand if able");
    expect(screen.getByLabelText("Organist")).toHaveValue("Jordan Doe Jr.");
    expect(leaveWarned()).toBe(true); // the organist is not saved yet
  });

  it("asks before leaving with unsaved edits", async () => {
    const { user } = renderPage("admin");
    const organist = await screen.findByLabelText("Organist");
    const back = within(screen.getByRole("main")).getByRole("link", { name: "Back to the builder" });
    expect(leaveWarned()).toBe(false);
    await user.type(organist, " Jr.");
    expect(leaveWarned()).toBe(true);
    await user.click(back);
    let dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Keep editing" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(organist).toHaveValue("Jordan Doe Jr.");
    expect(testRouter.push).not.toHaveBeenCalled();
    await user.click(back);
    dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Discard changes" }));
    expect(testRouter.push).toHaveBeenCalledWith("/builder");
  });

  it("sets returnValue too on a reload with unsaved edits (browsers that ask only then)", async () => {
    const { user } = renderPage("admin");
    const organist = await screen.findByLabelText("Organist");
    expect(leaveReturnValue()).toBeUndefined();
    await user.type(organist, " Jr.");
    expect(leaveReturnValue()).toBe("");
  });

  it("lets a modified or middle click on Back open the link as usual, with no discard dialog", async () => {
    const { user } = renderPage("admin");
    const organist = await screen.findByLabelText("Organist");
    const back = within(screen.getByRole("main")).getByRole("link", { name: "Back to the builder" });
    await user.type(organist, " Jr.");
    for (const init of [{ ctrlKey: true }, { metaKey: true }, { shiftKey: true }, { altKey: true }, { button: 1 }]) {
      expect(clickFollowsLink(back, init)).toBe(true);
      expect(screen.queryByRole("alertdialog")).toBeNull();
    }
    expect(testRouter.push).not.toHaveBeenCalled();
    expect(organist).toHaveValue("Jordan Doe Jr.");
    expect(clickFollowsLink(back, {})).toBe(false); // a plain click still asks first
    expect(await screen.findByRole("alertdialog", { name: DISCARD_TITLE })).toBeInTheDocument();
  });

  it("keeps what was saved when a read that started before the save answers after it", async () => {
    const { api, user, queryClient } = renderPage("admin", { [`PUT ${PATH}`]: (r: RecordedRequest) => r.body });
    const organist = await screen.findByLabelText("Organist");
    let answerGet: (body: unknown) => void = () => {};
    api.set(`GET ${PATH}`, () => new Promise((resolve) => (answerGet = resolve)));
    void queryClient.refetchQueries({ queryKey: keys.bulletinSettings(church().id) }); // a window-focus refetch
    await user.clear(organist);
    await user.type(organist, "Pat New");
    await user.click(screen.getByRole("button", { name: "Save settings" }));
    expect(await screen.findByText(SETTINGS_SAVED)).toBeInTheDocument();
    await act(async () => answerGet(filledBulletinSettings())); // read before the PUT was stored
    await act(() => new Promise((resolve) => setTimeout(resolve, 20)));
    expect(organist).toHaveValue("Pat New");
    expect(queryClient.getQueryData<BulletinSettings>(keys.bulletinSettings(church().id))?.organist).toBe("Pat New");
  });
});

/**
 * Settings → Church (slice 6a-1; 6a spec "Church profile"): admins edit and
 * save only what changed, members read. Rendered inside the Settings layout,
 * as the route is, with a Toaster.
 */
import { screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
import ChurchSettingsRoute from "@/app/(signed-in)/(church)/settings/church/page";
import { DISCARD_TITLE } from "@/components/app/leave-guard";
import { Toaster } from "@/components/ui/sonner";
import type { Church, ChurchProfile } from "@/lib/api/types";
import { authEvents } from "@/lib/queries/auth-events";
import { PROFILE_SAVED } from "@/lib/queries/church";
import { keys } from "@/lib/queries/keys";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { church, churchProfile, hymnals, me, translations } from "@/test/fixtures";
import { testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import { ADMINS_ONLY, BENEDICTION_HELP, HYMNAL_HELP, TIMEZONE_NOT_RECOGNIZED, TRANSLATION_HELP } from "./church-settings-page";

const ZONES = ["America/Chicago", "America/New_York", "Europe/London"];
const REAL_OPTIONS = new Intl.DateTimeFormat().resolvedOptions();

beforeEach(() => {
  vi.spyOn(Intl, "supportedValuesOf").mockReturnValue(ZONES);
  vi.spyOn(Intl.DateTimeFormat.prototype, "resolvedOptions").mockReturnValue({ ...REAL_OPTIONS, timeZone: "America/Chicago" });
});

afterEach(() => {
  toast.dismiss();
});

function renderPage(role: Church["role"] = "admin", profile: Partial<ChurchProfile> = {}, routes: Record<string, FakeHandler> = {}) {
  const active = church({ role });
  const api = installFakeApi({
    "GET /church": churchProfile({ role, ...profile }),
    "GET /translations": translations(),
    "GET /hymnals": hymnals(),
    ...routes,
  });
  const view = renderWithProviders(
    <>
      <SettingsLayout>
        <ChurchSettingsRoute />
      </SettingsLayout>
      <Toaster />
    </>,
    { me: me({ churches: [active] }), church: active, path: "/settings/church" },
  );
  return { ...view, api };
}

function patches(api: { requests: RecordedRequest[] }) {
  return api.requests.filter((r) => r.method === "PATCH" && r.path === "/church");
}

const echo = (r: RecordedRequest) => churchProfile(r.body as Partial<ChurchProfile>);

describe("Settings → Church (slice 6a-1)", () => {
  it("lets an admin change only the name: the request sends the name alone and the profile is cached", async () => {
    const { api, user, queryClient } = renderPage("admin", {}, { "PATCH /church": echo });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const name = await screen.findByLabelText("Church name");
    const save = screen.getByRole("button", { name: "Save profile" });
    expect(save).toBeDisabled();
    expect(screen.getByText(TRANSLATION_HELP)).toBeInTheDocument();
    expect(screen.getByText(BENEDICTION_HELP)).toBeInTheDocument();
    expect(await screen.findByText("GG2013 (your only hymnal)")).toBeInTheDocument();
    await user.clear(name);
    await user.type(name, " Example Church ");
    await user.click(save);
    expect(await screen.findByText(PROFILE_SAVED)).toBeInTheDocument();
    expect(patches(api)).toHaveLength(1);
    expect(patches(api)[0].body).toEqual({ name: "Example Church" }); // untouched selects send nothing
    expect(patches(api)[0].headers["x-church-id"]).toBe(church().id);
    expect(queryClient.getQueryData<ChurchProfile>(keys.churchProfile(church().id))?.name).toBe("Example Church");
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.me() });
    expect(invalidate).not.toHaveBeenCalledWith({ queryKey: keys.hymnals(church().id) });
    expect(save).toBeDisabled();
  });

  it("shows a member the profile as plain text, with the note and no Save", async () => {
    renderPage("member", { default_benediction: "" });
    expect(await screen.findByText(ADMINS_ONLY)).toBeInTheDocument();
    expect(screen.getByText("America/New York")).toBeInTheDocument();
    expect(screen.getByText("World English Bible (WEB)")).toBeInTheDocument();
    expect(screen.getByText("None. The AI writes the benediction.")).toBeInTheDocument();
    expect(screen.queryAllByRole("textbox")).toEqual([]);
    expect(screen.queryByRole("button", { name: "Save profile" })).toBeNull();
  });

  it("shows a member the hymnal the builder uses, noting a stored one the church no longer has", async () => {
    renderPage("member", { default_hymnal: "HL1955", effective_hymnal: "GG2013" });
    expect(await screen.findByText("GG2013 (the builder uses this; HL1955 is no longer in your hymnals)")).toBeInTheDocument();
    expect(screen.queryByText("HL1955")).toBeNull();
  });

  it("shows a field the server refuses under it and focuses it", async () => {
    const { user } = renderPage("admin", {}, {
      "PATCH /church": fakeError(422, "invalid_request", "Unknown timezone.", { fields: { timezone: "Unknown timezone." } }),
    });
    await user.type(await screen.findByLabelText("Church name"), " Church");
    await user.click(screen.getByRole("button", { name: "Save profile" }));
    const zone = screen.getByLabelText("Time zone");
    await waitFor(() => expect(zone).toHaveFocus());
    expect(zone).toHaveAttribute("aria-invalid", "true");
    expect(document.getElementById("church-timezone-error")).toHaveTextContent("Unknown timezone.");
  });

  it("shows a stored time zone it does not recognize, with the warning, and offers this device's zone", async () => {
    const { user } = renderPage("admin", { timezone: "Eastern", timezone_valid: false });
    const zone = await screen.findByLabelText("Time zone");
    expect(zone).toHaveValue("Eastern");
    expect(screen.getByText(TIMEZONE_NOT_RECOGNIZED)).toBeInTheDocument();
    const useDevice = screen.getByRole("button", { name: "Use this device's time zone (America/Chicago)" });
    // A long zone id wraps on a phone instead of overflowing (review m2): the button's nowrap and fixed height are lifted.
    expect(useDevice).toHaveClass("whitespace-normal", "h-auto", "min-h-11", "text-left");
    expect(useDevice).not.toHaveClass("whitespace-nowrap");
    await user.click(useDevice);
    expect(zone).toHaveValue("America/Chicago");
    expect(screen.queryByText(TIMEZONE_NOT_RECOGNIZED)).toBeNull();
  });

  it("keeps a stale stored translation or hymnal selectable, sends a new hymnal, and says when there are no hymnals", async () => {
    const two = hymnals({ items: [...hymnals().items, { code: "PH1990", hymn_count: 605, scripture_ref_count: 0 }] });
    const { api, user, queryClient, unmount } = renderPage(
      "admin",
      { bible_translation: "esv", default_hymnal: "HL1955" },
      { "GET /translations": translations({ items: [{ id: "web", label: "World English Bible (WEB)" }] }), "GET /hymnals": two, "PATCH /church": echo },
    );
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const translation = await screen.findByRole("combobox", { name: "Default Bible translation" });
    await waitFor(() => expect(translation).toHaveTextContent("ESV (not available on this server)"));
    const hymnal = screen.getByRole("combobox", { name: "Default hymnal" });
    await waitFor(() => expect(hymnal).toHaveTextContent("HL1955 (no longer in your hymnals)"));
    expect(screen.getByText(HYMNAL_HELP)).toBeInTheDocument();
    await user.click(hymnal);
    await user.click(await screen.findByRole("option", { name: "PH1990" }));
    await user.click(screen.getByRole("button", { name: "Save profile" }));
    await screen.findByText(PROFILE_SAVED);
    expect(patches(api)[0].body).toEqual({ default_hymnal: "PH1990" });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.hymnals(church().id) });
    unmount();

    renderPage("admin", { default_hymnal: null, effective_hymnal: null }, { "GET /hymnals": hymnals({ items: [], effective_hymnal: null }) });
    expect(await screen.findByText("Your church has no hymns yet, so there is no default hymnal.")).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "Default hymnal" })).toBeNull();
  });

  it("says there are no hymns when a stored default hymnal is left but the church has none (never \"your only hymnal\")", async () => {
    const { api } = renderPage(
      "admin",
      { default_hymnal: "GG2013", effective_hymnal: null },
      { "GET /hymnals": hymnals({ items: [], effective_hymnal: null, default_hymnal: "GG2013" }) },
    );
    await waitFor(() => expect(api.requests.some((r) => r.path === "/hymnals")).toBe(true));
    expect(await screen.findByText("Your church has no hymns yet, so there is no default hymnal.")).toBeInTheDocument();
    expect(screen.queryByText(/your only hymnal/)).toBeNull();
  });

  it("never labels a stored translation as another one when the translation list cannot be read", async () => {
    renderPage("admin", { bible_translation: "esv" }, { "GET /translations": fakeError(500, "internal_error", "Something went wrong.") });
    const translation = await screen.findByRole("combobox", { name: "Default Bible translation" });
    await waitFor(() => expect(translation).toHaveTextContent("ESV (not available on this server)"));
    expect(translation).not.toHaveTextContent("World English Bible");
  });

  it("rebases on newer data: another admin's rename shows, and the edited Benediction is kept and sent alone", async () => {
    const { api, user, queryClient } = renderPage("admin", {}, { "PATCH /church": echo });
    const benediction = await screen.findByLabelText("Default Benediction");
    await user.clear(benediction);
    await user.type(benediction, "Go in peace.");
    queryClient.setQueryData(keys.churchProfile(church().id), churchProfile({ name: "Grace Renamed" }));
    await waitFor(() => expect(screen.getByLabelText("Church name")).toHaveValue("Grace Renamed"));
    expect(benediction).toHaveValue("Go in peace.");
    await user.click(screen.getByRole("button", { name: "Save profile" }));
    await screen.findByText(PROFILE_SAVED);
    expect(patches(api)[0].body).toEqual({ default_benediction: "Go in peace." });
  });

  it("toasts a role 403, refetches the profile and does not report the church as lost", async () => {
    const lost = vi.fn();
    const off = authEvents.onChurchAccessLost(lost);
    const { user, queryClient } = renderPage("admin", {}, {
      "PATCH /church": fakeError(403, "forbidden", "Only church admins can do this."),
    });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    await user.type(await screen.findByLabelText("Church name"), " Church");
    await user.click(screen.getByRole("button", { name: "Save profile" }));
    expect(await screen.findByText("Only church admins can do this.")).toBeInTheDocument();
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.churchProfile(church().id) });
    expect(lost).not.toHaveBeenCalled();
    off();
  });

  it("asks before leaving with unsaved edits, through the Settings nav", async () => {
    const { user } = renderPage("admin");
    const name = await screen.findByLabelText("Church name");
    const bulletin = screen.getByRole("link", { name: "Bulletin" });
    await user.type(name, " Church");
    await user.click(bulletin);
    let dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Keep editing" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(name).toHaveValue("Grace Church");
    expect(testRouter.push).not.toHaveBeenCalled();
    await user.click(bulletin);
    dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Discard changes" }));
    expect(testRouter.push).toHaveBeenCalledWith("/bulletin-settings");
  });

  it("shows the error state with Retry when the profile cannot be read", async () => {
    renderPage("admin", {}, { "GET /church": fakeError(500, "internal_error", "Something went wrong.") });
    expect(await screen.findByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});

/**
 * Settings → Liturgy's Affirmation of Faith default (affirmation spec,
 * "Settings → Liturgy: the church default"): owners and admins change and
 * save it with PATCH /church; members read it and cannot change it. Rendered
 * as the route is, inside the Settings layout, with a Toaster.
 */
import { screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, describe, expect, it } from "vitest";

import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
import LiturgySettingsRoute from "@/app/(signed-in)/(church)/settings/liturgy/page";
import { DISCARD_TITLE } from "@/components/app/leave-guard";
import { Toaster } from "@/components/ui/sonner";
import type { Church, ChurchAffirmation, ChurchProfile } from "@/lib/api/types";
import { installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { church, churchProfile, liturgyConfig, liturgyPrompts, me } from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { AFFIRMATION_ADMINS_ONLY, AFFIRMATION_SAVED, OWN_TEXT_HELP, OWN_TEXT_REQUIRED } from "./affirmation-default-card";

const OWN = "We trust in God the Holy Spirit.";

afterEach(() => {
  toast.dismiss();
});

/** A fake `/church` whose PATCH stores the default, as the server does. */
function churchServer(role: Church["role"]) {
  let profile: ChurchProfile = churchProfile({ role });
  return {
    get: () => profile,
    patch: (req: RecordedRequest) => {
      const sent = (req.body as { default_affirmation: ChurchAffirmation }).default_affirmation;
      profile = { ...profile, default_affirmation: sent };
      return profile;
    },
  };
}

function renderPage(role: Church["role"] = "admin", routes: Record<string, FakeHandler> = {}) {
  const active = church({ role });
  const server = churchServer(role);
  const api = installFakeApi({
    "GET /church": server.get,
    "PATCH /church": server.patch,
    "GET /liturgy/config": liturgyConfig(),
    "GET /church/liturgy-prompts": liturgyPrompts({}, { can_edit: role !== "member" }),
    ...routes,
  });
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

const patches = (api: { requests: RecordedRequest[] }) => api.requests.filter((r) => r.method === "PATCH" && r.path === "/church");

async function form() {
  return screen.findByRole("form", { name: "Affirmation of Faith default" });
}

describe("Settings → Liturgy: the Affirmation of Faith default (affirmation spec)", () => {
  it("lets an admin choose the church's own text and save it", async () => {
    const { user, api } = renderPage("admin");
    const card = await form();
    expect(within(card).getByRole("radio", { name: "Apostles' Creed" })).toBeChecked();
    const save = within(card).getByRole("button", { name: "Save default" });
    expect(save).toBeDisabled();
    await user.click(within(card).getByRole("radio", { name: "Your own text" }));
    const box = within(card).getByRole("textbox", { name: "Your church's own text" });
    expect(box).toHaveAccessibleDescription(OWN_TEXT_REQUIRED);
    expect(save).toBeDisabled(); // own text with a blank box cannot be saved
    await user.type(box, `${OWN}  `);
    expect(box).toHaveAccessibleDescription(OWN_TEXT_HELP);
    await user.click(save);
    expect(await screen.findByText(AFFIRMATION_SAVED)).toBeInTheDocument();
    expect(patches(api).map((r) => r.body)).toEqual([{ default_affirmation: { choice: "own", text: OWN } }]);
    await waitFor(() => expect(save).toBeDisabled());
    expect(card.textContent).not.toContain("\u2014");
  });

  it("shows a creed's text and credit, and asks before leaving with an unsaved change", async () => {
    const { user, api } = renderPage("owner");
    const card = await form();
    await user.click(within(card).getByRole("radio", { name: "Nicene Creed" }));
    await user.click(within(card).getByRole("button", { name: "Show creed text" }));
    expect(within(card).getByText(/Consultation \(ELLC\), and used by permission\./)).toBeInTheDocument();
    await user.click(screen.getByRole("link", { name: "Church" }));
    expect(await screen.findByRole("alertdialog", { name: DISCARD_TITLE })).toBeInTheDocument();
    expect(patches(api)).toEqual([]);
  });

  it("leaves the card out when the API sends no card data (the pages ahead of the server side)", async () => {
    const older = { ...liturgyConfig(), affirmation: undefined } as unknown as ReturnType<typeof liturgyConfig>;
    renderPage("admin", { "GET /liturgy/config": older });
    expect(await screen.findByRole("form", { name: "Liturgy prompts" })).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("heading", { name: "Affirmation of Faith" })).toBeNull());
    expect(screen.queryByRole("form", { name: "Affirmation of Faith default" })).toBeNull();
  });

  it("shows a member the default read-only, with the note, and no way to change it", async () => {
    const { user, api } = renderPage("member", {
      "GET /church": churchProfile({ role: "member", default_affirmation: { choice: "own", text: OWN } }),
    });
    const card = await form();
    expect(within(card).getByText(AFFIRMATION_ADMINS_ONLY)).toBeInTheDocument();
    expect(within(card).getByRole("radio", { name: "Your own text" })).toBeChecked();
    for (const radio of within(card).getAllByRole("radio")) expect(radio).toHaveAttribute("aria-disabled", "true");
    const box = within(card).getByRole("textbox", { name: "Your church's own text" });
    expect(box).toHaveValue(OWN);
    expect(box).toHaveAttribute("readonly");
    expect(within(card).queryByRole("button", { name: "Save default" })).toBeNull();
    await user.click(within(card).getByRole("radio", { name: "Nicene Creed" }));
    expect(within(card).getByRole("radio", { name: "Your own text" })).toBeChecked();
    expect(patches(api)).toEqual([]);
  });
});

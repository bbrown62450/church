/**
 * Settings → Hymns, the Hymnals card (slice 6a-2; 6a spec UX §2a): every
 * member reads the hymnals, admins add a bundled one and remove any but the
 * default. Rendered inside the Settings layout, as the route is, with a Toaster.
 */
import { act, screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, describe, expect, it, vi } from "vitest";

import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
import HymnsSettingsRoute from "@/app/(signed-in)/(church)/settings/hymns/page";
import { Toaster } from "@/components/ui/sonner";
import type { Church, Hymnals } from "@/lib/api/types";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { church, hymnals, hymnalSource, hymnalSources, me } from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { MEMBER_HYMNALS_NOTE, NO_REFS_NOTE, STILL_WORKING } from "./hymnals-card";

afterEach(() => {
  toast.dismiss();
  vi.useRealTimers();
});

const GG = { code: "GG2013", label: "Glory to God (2013)", hymn_count: 853, scripture_ref_count: 795 };
const PH = { code: "PH1990", label: "The Presbyterian Hymnal (1990)", hymn_count: 605, scripture_ref_count: 0 };

/**
 * A fake `/hymnals`: `GET` answers with what the adds and removals left, as the
 * server would after a refetch. A source is present once the church has at
 * least as many hymns in its code (6a-2 build review M4).
 */
function hymnalsServer(items: Hymnals["items"] = [GG]) {
  let current = [...items];
  const has = (code: string, bundled: number) => (current.find((h) => h.code === code)?.hymn_count ?? 0) >= bundled;
  return {
    list: () => hymnals({ items: current }),
    sources: () => hymnalSources([
      hymnalSource({ code: "GG2013", label: "Glory to God (2013)", hymn_count: 853, has_scripture_refs: true, present: has("GG2013", 853) }),
      hymnalSource({ present: has("PH1990", 605) }),
    ]),
    add: () => {
      const before = current.find((h) => h.code === "PH1990")?.hymn_count ?? 0;
      current = [...current.filter((h) => h.code !== "PH1990"), PH];
      return { code: "PH1990", label: PH.label, inserted: 605 - before, updated: 0 };
    },
    remove: (code: string) => {
      current = current.filter((h) => h.code !== code);
      return { deleted: true, hymns_deleted: 605 };
    },
  };
}

function renderPage(role: Church["role"] = "admin", routes: Record<string, FakeHandler> = {}) {
  const active = church({ role });
  const api = installFakeApi({
    "GET /hymnals": hymnals(),
    "GET /hymnal-sources": hymnalSources(),
    "GET /hymns": { items: [], total: 0, limit: 50, offset: 0 },
    ...routes,
  });
  const view = renderWithProviders(
    <>
      <SettingsLayout>
        <HymnsSettingsRoute />
      </SettingsLayout>
      <Toaster />
    </>,
    { me: me({ churches: [active] }), church: active, path: "/settings/hymns" },
  );
  return { ...view, api };
}

function hymnalRows() {
  return within(screen.getByRole("list", { name: "Hymnals" })).getAllByRole("listitem");
}

function requests(api: { requests: RecordedRequest[] }, method: string, prefix: string) {
  return api.requests.filter((r) => r.method === method && r.path.startsWith(prefix));
}

describe("Settings → Hymns, the Hymnals card (slice 6a-2)", () => {
  it("shows a member the hymnals with their counts and the default, and no actions", async () => {
    const { api } = renderPage("member", { "GET /hymnals": hymnals({ items: [GG, PH], effective_hymnal: "GG2013" }) });
    await screen.findByText("Glory to God (2013) · 853 hymns");
    expect(hymnalRows().map((row) => row.textContent)).toEqual([
      "GG2013DefaultGlory to God (2013) · 853 hymns",
      "PH1990The Presbyterian Hymnal (1990) · 605 hymns",
    ]);
    expect(screen.getByText("1458 hymns in 2 hymnals.")).toBeInTheDocument();
    expect(screen.getByText(MEMBER_HYMNALS_NOTE)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^(Add a hymnal|Remove )/ })).toBeNull();
    expect(requests(api, "GET", "/hymnal-sources")).toHaveLength(0);
  });

  it("gives an admin Remove on every hymnal but the default, which says where to change it", async () => {
    renderPage("admin", { "GET /hymnals": hymnals({ items: [GG, PH], default_hymnal: "PH1990", effective_hymnal: "PH1990" }) });
    await screen.findByText("Glory to God (2013) · 853 hymns");
    const [gg, ph] = hymnalRows();
    expect(within(gg).getByRole("button", { name: "Remove GG2013" })).toHaveTextContent("Remove…");
    expect(within(ph).queryByRole("button")).toBeNull();
    expect(ph).toHaveTextContent("Default. Change it in Church profile.");
    expect(within(ph).getByRole("link", { name: "Church profile" })).toHaveAttribute("href", "/settings/church");
    expect(screen.queryByText(MEMBER_HYMNALS_NOTE)).toBeNull();
  });

  it("lets an admin add PH1990: the note, Added for a hymnal the church has, the toast, and every list refreshed", async () => {
    const server = hymnalsServer();
    const { api, user, queryClient } = renderPage("admin", {
      "GET /hymnals": server.list,
      "GET /hymnal-sources": server.sources,
      "POST /hymnals": server.add,
    });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    await user.click(await screen.findByRole("button", { name: "Add a hymnal" }));
    const dialog = await screen.findByRole("dialog", { name: "Add a hymnal" });
    const [gg, ph] = within(dialog).getAllByRole("listitem");
    expect(gg).toHaveTextContent("GG2013 · Glory to God (2013) · 853 hymns");
    expect(within(gg).getByRole("button", { name: "Added" })).toBeDisabled();
    expect(ph).toHaveTextContent(`PH1990 · The Presbyterian Hymnal (1990) · 605 hymns${NO_REFS_NOTE}`);
    await user.click(within(ph).getByRole("button", { name: "Add PH1990" }));
    expect(await screen.findByText("Added PH1990 (605 hymns).")).toBeInTheDocument();
    expect(requests(api, "POST", "/hymnals")[0].body).toEqual({ code: "PH1990" });
    expect(within(ph).getByRole("button", { name: "Added" })).toBeDisabled();
    expect(screen.getByRole("dialog", { name: "Add a hymnal" })).toBeInTheDocument();
    for (const key of [["church", church().id, "hymns"], ["church", church().id, "hymnals"], ["church", church().id, "hymnal-sources"], ["church", church().id, "profile"]]) {
      expect(invalidate).toHaveBeenCalledWith({ queryKey: key });
    }
    await user.click(within(dialog).getByRole("button", { name: "Done" }));
    await waitFor(() => expect(hymnalRows()).toHaveLength(2));
  });

  it("offers Add for a hymnal the church has only a few hand-entered hymns of, and adds the rest (6a-2 build review M4)", async () => {
    const server = hymnalsServer([GG, { ...PH, hymn_count: 1, scripture_ref_count: 0 }]);
    const { api, user } = renderPage("admin", {
      "GET /hymnals": server.list,
      "GET /hymnal-sources": server.sources,
      "POST /hymnals": server.add,
    });
    await user.click(await screen.findByRole("button", { name: "Add a hymnal" }));
    const dialog = await screen.findByRole("dialog", { name: "Add a hymnal" });
    const [gg, ph] = within(dialog).getAllByRole("listitem");
    expect(within(gg).getByRole("button", { name: "Added" })).toBeDisabled();
    await user.click(await within(ph).findByRole("button", { name: "Add PH1990" }));
    expect(await screen.findByText("Added PH1990 (604 hymns).")).toBeInTheDocument();
    expect(requests(api, "POST", "/hymnals")).toHaveLength(1);
    expect(within(ph).getByRole("button", { name: "Added" })).toBeDisabled();
  });

  it("keeps the add dialog open while an add runs, and says it is still working after 8 s", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true, toFake: ["setTimeout", "clearTimeout"] });
    let finish: (value: unknown) => void = () => {};
    const { user } = renderPage("admin", {
      "POST /hymnals": () => new Promise((resolve) => {
        finish = resolve;
      }),
    });
    await user.click(await screen.findByRole("button", { name: "Add a hymnal" }));
    const dialog = await screen.findByRole("dialog", { name: "Add a hymnal" });
    await user.click(await within(dialog).findByRole("button", { name: "Add PH1990" }));
    expect(within(dialog).getByRole("button", { name: "Add PH1990" })).toHaveTextContent("Adding…");
    expect(within(dialog).getByRole("button", { name: "Done" })).toBeDisabled();
    expect(screen.queryByText(STILL_WORKING)).toBeNull();
    act(() => {
      vi.advanceTimersByTime(8_000);
    });
    expect(await screen.findByText(STILL_WORKING)).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.getByRole("dialog", { name: "Add a hymnal" })).toBeInTheDocument();
    finish({ code: "PH1990", label: PH.label, inserted: 605, updated: 0 });
    expect(await screen.findByText("Added PH1990 (605 hymns).")).toBeInTheDocument();
    expect(screen.queryByText(STILL_WORKING)).toBeNull();
  });

  it("says when no bundled hymnal is available", async () => {
    const { user } = renderPage("admin", { "GET /hymnal-sources": hymnalSources([]) });
    await user.click(await screen.findByRole("button", { name: "Add a hymnal" }));
    expect(await screen.findByText("No bundled hymnals are available on this server.")).toBeInTheDocument();
  });

  it("says a hymnal is already added when the add brings nothing new", async () => {
    const { user } = renderPage("admin", { "POST /hymnals": { code: "PH1990", label: PH.label, inserted: 0, updated: 0 } });
    await user.click(await screen.findByRole("button", { name: "Add a hymnal" }));
    const dialog = await screen.findByRole("dialog", { name: "Add a hymnal" });
    await user.click(await within(dialog).findByRole("button", { name: "Add PH1990" }));
    expect(await screen.findByText("PH1990 is already added.")).toBeInTheDocument();
    expect(screen.queryByText(/^Added PH1990/)).toBeNull();
    expect(within(dialog).getAllByRole("button", { name: "Added" })).toHaveLength(2);
  });

  it("toasts a failed add and refreshes every list, since the add may have finished on the server", async () => {
    const server = hymnalsServer();
    const { user } = renderPage("admin", {
      "GET /hymnals": server.list,
      "GET /hymnal-sources": server.sources,
      // the server added PH1990, but its answer never arrived as a success
      "POST /hymnals": () => {
        server.add();
        return fakeError(500, "internal_error", "Internal server error.");
      },
    });
    await user.click(await screen.findByRole("button", { name: "Add a hymnal" }));
    const dialog = await screen.findByRole("dialog", { name: "Add a hymnal" });
    await user.click(await within(dialog).findByRole("button", { name: "Add PH1990" }));
    expect(await screen.findByText("Something went wrong. (Ref: 4f9a2c1e)")).toBeInTheDocument();
    await waitFor(() => expect(within(dialog).getAllByRole("button", { name: "Added" })).toHaveLength(2));
    await user.click(within(dialog).getByRole("button", { name: "Done" }));
    await waitFor(() => expect(hymnalRows()).toHaveLength(2));
  });

  it("asks before removing a hymnal, then removes it; focus goes to Add a hymnal", async () => {
    const server = hymnalsServer([GG, PH]);
    const { api, user } = renderPage("admin", {
      "GET /hymnals": server.list,
      "GET /hymnal-sources": server.sources,
      "DELETE /hymnals/PH1990": () => server.remove("PH1990"),
    });
    await screen.findByText("The Presbyterian Hymnal (1990) · 605 hymns");
    await waitFor(() => expect(requests(api, "GET", "/hymnal-sources")).toHaveLength(1));
    await user.click(screen.getByRole("button", { name: "Remove PH1990" }));
    const confirm = await screen.findByRole("alertdialog", { name: "Remove PH1990?" });
    expect(confirm).toHaveTextContent(
      "This deletes all 605 hymns in PH1990 from your church's hymnal, including hymns your church added to it. " +
        "Saved services keep their hymns. Services in progress will ask you to choose replacements. " +
        "You can add PH1990 again later, but edits you made to its hymns will be lost.",
    );
    await user.click(within(confirm).getByRole("button", { name: "Remove PH1990" }));
    expect(await screen.findByText("Removed PH1990.")).toBeInTheDocument();
    await waitFor(() => expect(hymnalRows()).toHaveLength(1));
    expect(requests(api, "DELETE", "/hymnals/")).toHaveLength(1);
    await waitFor(() => expect(screen.getByRole("button", { name: "Add a hymnal" })).toHaveFocus());
  });

  it("toasts a refused removal and closes the confirmation", async () => {
    const { user } = renderPage("admin", {
      "GET /hymnals": hymnals({ items: [GG, PH] }),
      "DELETE /hymnals/PH1990": fakeError(409, "conflict", "PH1990 is your default hymnal. Choose a different default in Church profile first."),
    });
    await user.click(await screen.findByRole("button", { name: "Remove PH1990" }));
    const confirm = await screen.findByRole("alertdialog", { name: "Remove PH1990?" });
    await user.click(within(confirm).getByRole("button", { name: "Remove PH1990" }));
    expect(await screen.findByText("PH1990 is your default hymnal. Choose a different default in Church profile first.")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
  });

  it("moves focus to Add a hymnal when the hymnal was already removed elsewhere (404)", async () => {
    const server = hymnalsServer([GG, PH]);
    const { user } = renderPage("admin", {
      "GET /hymnals": server.list,
      "GET /hymnal-sources": server.sources,
      "DELETE /hymnals/PH1990": fakeError(404, "not_found", "Your church doesn't have that hymnal."),
    });
    await user.click(await screen.findByRole("button", { name: "Remove PH1990" }));
    const confirm = await screen.findByRole("alertdialog", { name: "Remove PH1990?" });
    server.remove("PH1990"); // another tab removed it meanwhile
    await user.click(within(confirm).getByRole("button", { name: "Remove PH1990" }));
    expect(await screen.findByText("Your church doesn't have that hymnal.")).toBeInTheDocument();
    await waitFor(() => expect(hymnalRows()).toHaveLength(1));
    await waitFor(() => expect(screen.getByRole("button", { name: "Add a hymnal" })).toHaveFocus());
  });

  it("words the removal of a one-hymn hymnal in the singular, and says one outside the bundled list can't come back", async () => {
    const XX = { code: "XX2000", label: null, hymn_count: 1, scripture_ref_count: 0 };
    const { api, user } = renderPage("admin", { "GET /hymnals": hymnals({ items: [GG, XX] }) });
    await screen.findByText("1 hymn");
    await waitFor(() => expect(requests(api, "GET", "/hymnal-sources")).toHaveLength(1));
    await user.click(screen.getByRole("button", { name: "Remove XX2000" }));
    const confirm = await screen.findByRole("alertdialog", { name: "Remove XX2000?" });
    expect(confirm).toHaveTextContent(
      "This deletes the 1 hymn in XX2000 from your church's hymnal, including hymns your church added to it. " +
        "Saved services keep their hymns. Services in progress will ask you to choose replacements. " +
        "It can't be added back from the bundled list.",
    );
  });

  it("offers no Remove for a hymnal whose code the removal route cannot take", async () => {
    const odd = [
      { code: "PH 1990", label: null, hymn_count: 3, scripture_ref_count: 0 },
      { code: "X", label: null, hymn_count: 2, scripture_ref_count: 0 },
    ];
    renderPage("admin", { "GET /hymnals": hymnals({ items: [GG, ...odd, PH] }) });
    await screen.findByText("The Presbyterian Hymnal (1990) · 605 hymns");
    expect(hymnalRows().map((row) => within(row).queryByRole("button")?.getAttribute("aria-label") ?? null)).toEqual([
      null, null, null, "Remove PH1990",
    ]);
  });
});

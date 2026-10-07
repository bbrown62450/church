/**
 * Settings → Hymns, the Hymn library (slice 6a-2; 6a spec UX §2b): search,
 * hymnal chips, pages of 50 with Show more, and the add and edit dialog (any
 * member), with delete and the year and familiarity for admins. Rendered
 * inside the Settings layout, as the route is, with a Toaster.
 */
import { screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, describe, expect, it, vi } from "vitest";

import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
import HymnsSettingsRoute from "@/app/(signed-in)/(church)/settings/hymns/page";
import { Toaster } from "@/components/ui/sonner";
import type { Church, Hymn, HymnPage } from "@/lib/api/types";
import { keys } from "@/lib/queries/keys";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { church, hymn, hymnDetail, hymnals, hymnalSources, me } from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { ADMINS_ONLY_FIELD, DELETE_BODY, SAVED_SERVICES_NOTE } from "./hymn-dialog";
import { EMPTY_ADMIN, EMPTY_MEMBER, LIBRARY_CAPTION } from "./hymn-library";

afterEach(() => {
  toast.dismiss();
});

const THIS_YEAR = new Date().getFullYear();
const HOLY = hymn({ number: 138, title: "Holy, Holy, Holy", themes: ["Trinity"], scripture_refs: "Isaiah 6:3", text_year: 1826, hymnal_count: 12 });
const UNNUMBERED = hymn({ number: null, title: "Untitled Tune", link: null });
const PH_ONE = hymn({ number: 1, hymnal: "PH1990", title: "Come, Thou long-expected Jesus" });

/** A fake `/hymns`: `GET` filters and pages what the writes left, as the server would. */
function hymnsServer(initial: Hymn[] = [HOLY, hymn(), UNNUMBERED]) {
  let items = [...initial];
  return {
    list: (req: RecordedRequest): HymnPage => {
      const query = new URL(req.path, "http://localhost").searchParams;
      const q = (query.get("q") ?? "").toLowerCase();
      const code = query.get("hymnal");
      const matched = items.filter(
        (h) => (code === null || h.hymnal === code) && (q === "" || h.title.toLowerCase().includes(q) || String(h.number) === q),
      );
      const limit = Number(query.get("limit"));
      const offset = Number(query.get("offset"));
      return { items: matched.slice(offset, offset + limit), total: matched.length, limit, offset };
    },
    add: (req: RecordedRequest) => {
      const body = req.body as { title: string; number: number | null };
      items = [...items, hymn({ number: body.number, title: body.title })];
      return { status: 201, body: hymnDetail({ number: body.number, title: body.title }) };
    },
    save: (id: string) => (req: RecordedRequest) => {
      items = items.map((h) => (h.id === id ? { ...h, ...(req.body as Partial<Hymn>) } : h));
      return hymnDetail({ id, ...(req.body as object) });
    },
    remove: (id: string) => () => {
      items = items.filter((h) => h.id !== id);
      return { deleted: true };
    },
  };
}

function renderPage(role: Church["role"] = "admin", routes: Record<string, FakeHandler> = {}) {
  const active = church({ role });
  const server = hymnsServer();
  const api = installFakeApi({
    "GET /hymnals": hymnals(),
    "GET /hymnal-sources": hymnalSources(),
    "GET /hymns": server.list,
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

function hymnRows() {
  return within(screen.getByRole("list", { name: "Hymns" })).getAllByRole("button");
}

function listRequests(api: { requests: RecordedRequest[] }) {
  return api.requests.filter((r) => r.method === "GET" && r.path.startsWith("/hymns?")).map((r) => r.path);
}

function writes(api: { requests: RecordedRequest[] }, method: string) {
  return api.requests.filter((r) => r.method === method && r.path.startsWith("/hymns"));
}

async function openEdit(user: ReturnType<typeof renderPage>["user"], label: RegExp) {
  await user.click(await screen.findByRole("button", { name: label }));
  return screen.findByRole("dialog", { name: "Edit hymn" });
}

describe("Settings → Hymns, the Hymn library (slice 6a-2)", () => {
  it("lists the hymns in the server's order with the count, and a member edits one without the year or familiarity", async () => {
    const server = hymnsServer();
    const { api, user } = renderPage("member", { "GET /hymns": server.list, [`PATCH /hymns/${HOLY.id}`]: server.save(HOLY.id) });
    expect(await screen.findByText("3 hymns")).toBeInTheDocument();
    expect(screen.getByText(LIBRARY_CAPTION)).toBeInTheDocument();
    expect(hymnRows().map((row) => row.textContent)).toEqual(["#138 Holy, Holy, Holy", "#403 Come, Thou Almighty King", "Untitled Tune"]);
    expect(screen.queryByRole("group", { name: "Hymnal" })).toBeNull();
    expect(listRequests(api)[0]).toBe("/hymns?limit=50&offset=0");

    const dialog = await openEdit(user, /^#138 Holy/);
    expect(within(dialog).getByLabelText("Title")).toHaveValue("Holy, Holy, Holy");
    expect(within(dialog).getByLabelText("Themes")).toHaveValue("Trinity");
    expect(within(dialog).getByLabelText("Year the words were written")).toHaveAttribute("readonly");
    expect(within(dialog).getByLabelText("Number of hymnals (familiarity)")).toHaveValue("12");
    expect(within(dialog).getAllByText(ADMINS_ONLY_FIELD)).toHaveLength(2);
    expect(within(dialog).queryByRole("button", { name: "Delete hymn" })).toBeNull();
    expect(within(dialog).queryByLabelText("Hymnal")).toBeNull();
    expect(within(dialog).getByText(SAVED_SERVICES_NOTE)).toBeInTheDocument();
    await user.clear(within(dialog).getByLabelText("Scripture references"));
    await user.type(within(dialog).getByLabelText("Scripture references"), "Revelation 4:8");
    await user.click(within(dialog).getByRole("button", { name: "Save changes" }));
    expect(await screen.findByText("Hymn updated.")).toBeInTheDocument();
    expect(writes(api, "PATCH")[0].body).toEqual({ scripture_refs: "Revelation 4:8" });
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("searches 300 ms after typing, from the first page, and offers Clear search when nothing matches", async () => {
    const { api, user } = renderPage("member");
    await screen.findByText("3 hymns");
    const search = screen.getByRole("searchbox", { name: "Search by title or number" });
    await user.type(search, "holy");
    expect(await screen.findByText("1 matching hymn")).toBeInTheDocument();
    expect(listRequests(api)).toContain("/hymns?limit=50&offset=0&q=holy");
    expect(listRequests(api)).not.toContain("/hymns?limit=50&offset=0&q=h");
    await user.clear(search);
    await user.type(search, "zzz");
    expect(await screen.findByText("No hymns match “zzz”.")).toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: "Clear search" })[1]);
    expect(await screen.findByText("3 hymns")).toBeInTheDocument();
    expect(search).toHaveValue("");
    expect(search).toHaveFocus();
  });

  it("loads the next 50 with Show more", async () => {
    const many = Array.from({ length: 60 }, (_, i) => hymn({ number: i + 1, title: `Hymn ${i + 1}` }));
    const server = hymnsServer(many);
    const { api, user } = renderPage("member", { "GET /hymns": server.list });
    expect(await screen.findByText("60 hymns")).toBeInTheDocument();
    expect(hymnRows()).toHaveLength(50);
    await user.click(screen.getByRole("button", { name: "Show more" }));
    await waitFor(() => expect(hymnRows()).toHaveLength(60));
    expect(listRequests(api)).toContain("/hymns?limit=50&offset=50");
    expect(screen.queryByRole("button", { name: "Show more" })).toBeNull();
  });

  it("filters by hymnal with chips when the church has several, and badges each row", async () => {
    const server = hymnsServer([HOLY, PH_ONE]);
    const { api, user } = renderPage("member", {
      "GET /hymns": server.list,
      "GET /hymnals": hymnals({ items: [{ code: "GG2013", hymn_count: 1, scripture_ref_count: 1 }, { code: "PH1990", hymn_count: 1, scripture_ref_count: 0 }] }),
    });
    const group = await screen.findByRole("group", { name: "Hymnal" });
    expect(within(group).getAllByRole("button").map((b) => [b.textContent, b.getAttribute("aria-pressed")])).toEqual([
      ["All", "true"], ["GG2013", "false"], ["PH1990", "false"],
    ]);
    await waitFor(() => expect(hymnRows().map((row) => row.textContent)).toEqual(["#138 Holy, Holy, HolyGG2013", "#1 Come, Thou long-expected JesusPH1990"]));
    await user.click(within(group).getByRole("button", { name: "PH1990" }));
    expect(await screen.findByText("1 matching hymn")).toBeInTheDocument();
    expect(listRequests(api)).toContain("/hymns?limit=50&offset=0&hymnal=PH1990");
    expect(within(group).getByRole("button", { name: "PH1990" })).toHaveAttribute("aria-pressed", "true");
  });

  it("adds a hymn in the default hymnal: the body, the toast, and every hymn list refreshed", async () => {
    const server = hymnsServer();
    const { api, user, queryClient } = renderPage("admin", { "GET /hymns": server.list, "POST /hymns": server.add });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    await screen.findByText("3 hymns");
    await user.click(screen.getByRole("button", { name: "Add hymn" }));
    const dialog = await screen.findByRole("dialog", { name: "Add hymn" });
    expect(within(dialog).queryByText(SAVED_SERVICES_NOTE)).toBeNull();
    await user.type(within(dialog).getByLabelText("Title"), " Be Thou My Vision ");
    await user.type(within(dialog).getByLabelText("Number"), "339");
    await user.type(within(dialog).getByLabelText("Year the words were written"), "1905");
    await user.click(within(dialog).getByRole("button", { name: "Add hymn" }));
    expect(await screen.findByText("Hymn added.")).toBeInTheDocument();
    expect(writes(api, "POST")[0].body).toEqual({
      title: "Be Thou My Vision", number: 339, hymnal: null, scripture_refs: null, theme: null, link: null, text_year: 1905, hymnal_count: null,
    });
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    for (const key of [["church", church().id, "hymns"], ["church", church().id, "hymnals"], ["church", church().id, "profile"]]) {
      expect(invalidate).toHaveBeenCalledWith({ queryKey: key });
    }
    expect(await screen.findByText("4 hymns")).toBeInTheDocument();
  });

  it("checks the form before sending: the server's words under each field, the first one focused", async () => {
    const { api, user } = renderPage("admin");
    await screen.findByText("3 hymns");
    await user.click(screen.getByRole("button", { name: "Add hymn" }));
    const dialog = await screen.findByRole("dialog", { name: "Add hymn" });
    await user.type(within(dialog).getByLabelText("Number"), "12a");
    await user.type(within(dialog).getByLabelText("Year the words were written"), String(THIS_YEAR + 1));
    await user.click(within(dialog).getByRole("button", { name: "Add hymn" }));
    expect(within(dialog).getByText("Hymn title is required.")).toBeInTheDocument();
    expect(within(dialog).getByText("Hymn number must be a whole number.")).toBeInTheDocument();
    expect(within(dialog).getByText(`Year must be a whole number from 1 to ${THIS_YEAR}.`)).toBeInTheDocument();
    expect(within(dialog).getByLabelText("Title")).toHaveFocus();
    expect(writes(api, "POST")).toHaveLength(0);
  });

  it("shows the server's field error under its field, and a duplicate above the buttons", async () => {
    const { api, user } = renderPage("admin", {
      "POST /hymns": fakeError(422, "invalid_request", "Links can't contain spaces.", { fields: { link: "Links can't contain spaces." } }),
    });
    await screen.findByText("3 hymns");
    await user.click(screen.getByRole("button", { name: "Add hymn" }));
    const dialog = await screen.findByRole("dialog", { name: "Add hymn" });
    await user.type(within(dialog).getByLabelText("Title"), "Holy, Holy, Holy");
    await user.type(within(dialog).getByLabelText("Link"), "https://hymnary.org/a b");
    await user.click(within(dialog).getByRole("button", { name: "Add hymn" }));
    expect(await within(dialog).findByText("Links can't contain spaces.")).toBeInTheDocument();
    await waitFor(() => expect(within(dialog).getByLabelText("Link")).toHaveFocus());

    api.set("POST /hymns", fakeError(409, "conflict", "GG2013 already has #138 Holy, Holy, Holy."));
    await user.clear(within(dialog).getByLabelText("Link"));
    await user.type(within(dialog).getByLabelText("Number"), "138");
    await user.click(within(dialog).getByRole("button", { name: "Add hymn" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("GG2013 already has #138 Holy, Holy, Holy.");
    expect(screen.getByRole("dialog", { name: "Add hymn" })).toBeInTheDocument();
  });

  it("sends the chosen hymnal when the church has several (6a-2 build review I1)", async () => {
    const { api, user } = renderPage("member", {
      "POST /hymns": { status: 201, body: hymnDetail() },
      "GET /hymnals": hymnals({ items: [{ code: "GG2013", hymn_count: 1, scripture_ref_count: 1 }, { code: "PH1990", hymn_count: 1, scripture_ref_count: 0 }] }),
    });
    await screen.findByRole("group", { name: "Hymnal" });
    await user.click(screen.getByRole("button", { name: "Add hymn" }));
    const dialog = await screen.findByRole("dialog", { name: "Add hymn" });
    expect(within(dialog).getByLabelText("Hymnal")).toBeInTheDocument();
    await user.type(within(dialog).getByLabelText("Title"), "Be Thou My Vision");
    await user.click(within(dialog).getByRole("button", { name: "Add hymn" }));
    expect(await screen.findByText("Hymn added.")).toBeInTheDocument();
    expect((writes(api, "POST")[0].body as { hymnal: string | null }).hymnal).toBe("GG2013");
  });

  it("toasts a hymnal error the form has no Hymnal field to show (one hymnal, stale), and stays open (6a-2 build review I1)", async () => {
    const { user } = renderPage("member", {
      "POST /hymns": fakeError(422, "invalid_request", "Choose one of your church's hymnals.", { fields: { hymnal: "Choose one of your church's hymnals." } }),
    });
    await screen.findByText("3 hymns");
    await user.click(screen.getByRole("button", { name: "Add hymn" }));
    const dialog = await screen.findByRole("dialog", { name: "Add hymn" });
    expect(within(dialog).queryByLabelText("Hymnal")).toBeNull();
    await user.type(within(dialog).getByLabelText("Title"), "Be Thou My Vision");
    await user.click(within(dialog).getByRole("button", { name: "Add hymn" }));
    expect(await screen.findByText("Choose one of your church's hymnals.")).toBeInTheDocument();
    expect(within(dialog).queryByText("Choose one of your church's hymnals.")).toBeNull();
    expect(screen.getByRole("dialog", { name: "Add hymn" })).toBeInTheDocument();
  });

  it("lets an admin set the year and clear the familiarity, sending only those", async () => {
    const server = hymnsServer();
    const { api, user } = renderPage("admin", { "GET /hymns": server.list, [`PATCH /hymns/${HOLY.id}`]: server.save(HOLY.id) });
    const dialog = await openEdit(user, /^#138 Holy/);
    const year = within(dialog).getByLabelText("Year the words were written");
    expect(year).not.toHaveAttribute("readonly");
    await user.clear(year);
    await user.type(year, "1861");
    await user.clear(within(dialog).getByLabelText("Number of hymnals (familiarity)"));
    await user.click(within(dialog).getByRole("button", { name: "Save changes" }));
    expect(await screen.findByText("Hymn updated.")).toBeInTheDocument();
    expect(writes(api, "PATCH")[0].body).toEqual({ text_year: 1861, hymnal_count: null });
  });

  it("asks before an admin deletes a hymn, then deletes it, marks the builder's lists stale; focus goes to Add hymn", async () => {
    const server = hymnsServer();
    const { api, user, queryClient } = renderPage("admin", { "GET /hymns": server.list, [`DELETE /hymns/${HOLY.id}`]: server.remove(HOLY.id) });
    // what the builder's hymn picker and "Hymns for the readings" have cached (slice 3's keys)
    const picker = keys.hymns(church().id, { hymnal: "GG2013", limit: 2000, recent_for_date: null });
    const matches = keys.hymnMatches(church().id, { refs: ["Isaiah 6:1-8"], hymnal: "GG2013", recent_for_date: null });
    queryClient.setQueryData(picker, { items: [HOLY], total: 1, limit: 2000, offset: 0 });
    queryClient.setQueryData(matches, { hymnal: "GG2013", refs_used: [], unparsed_refs: [], total_matched: 0, items: [] });
    const dialog = await openEdit(user, /^#138 Holy/);
    await user.click(within(dialog).getByRole("button", { name: "Delete hymn" }));
    const confirm = await screen.findByRole("alertdialog", { name: "Delete “Holy, Holy, Holy”?" });
    expect(confirm).toHaveTextContent(DELETE_BODY);
    await user.click(within(confirm).getByRole("button", { name: "Delete hymn" }));
    expect(await screen.findByText("Hymn deleted.")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(writes(api, "DELETE")).toHaveLength(1);
    expect(queryClient.getQueryState(picker)?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(matches)?.isInvalidated).toBe(true);
    expect(await screen.findByText("2 hymns")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Add hymn" })).toHaveFocus());
  });

  it("closes the edit dialog when the hymn was deleted elsewhere, refetches, and focuses Add hymn", async () => {
    const server = hymnsServer();
    const { user } = renderPage("member", { "GET /hymns": server.list, [`PATCH /hymns/${HOLY.id}`]: fakeError(404, "not_found", "Hymn not found.") });
    const dialog = await openEdit(user, /^#138 Holy/);
    server.remove(HOLY.id)();
    await user.type(within(dialog).getByLabelText("Title"), "!");
    await user.click(within(dialog).getByRole("button", { name: "Save changes" }));
    expect(await screen.findByText("This hymn was already deleted.")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(await screen.findByText("2 hymns")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Add hymn" })).toHaveFocus());
  });

  it("keeps the dialog open while a save runs", async () => {
    let finish: (value: unknown) => void = () => {};
    const { user } = renderPage("member", {
      [`PATCH /hymns/${HOLY.id}`]: () => new Promise((resolve) => {
        finish = resolve;
      }),
    });
    const dialog = await openEdit(user, /^#138 Holy/);
    await user.type(within(dialog).getByLabelText("Title"), "!");
    await user.click(within(dialog).getByRole("button", { name: "Save changes" }));
    expect(within(dialog).getByRole("button", { name: "Cancel" })).toBeDisabled();
    await user.keyboard("{Escape}");
    expect(screen.getByRole("dialog", { name: "Edit hymn" })).toBeInTheDocument();
    finish(hymnDetail({ id: HOLY.id, title: "Holy, Holy, Holy!" }));
    expect(await screen.findByText("Hymn updated.")).toBeInTheDocument();
  });

  it("toasts a role 403, closes the dialog and refetches the church profile", async () => {
    const { user, queryClient } = renderPage("admin", {
      [`PATCH /hymns/${HOLY.id}`]: fakeError(403, "forbidden", "Only church admins can do this."),
    });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const dialog = await openEdit(user, /^#138 Holy/);
    await user.clear(within(dialog).getByLabelText("Year the words were written"));
    await user.type(within(dialog).getByLabelText("Year the words were written"), "1830");
    await user.click(within(dialog).getByRole("button", { name: "Save changes" }));
    expect(await screen.findByText("Only church admins can do this.")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["church", church().id, "profile"] });
  });

  it("shows each role its empty state", async () => {
    const empty = { "GET /hymns": { items: [], total: 0, limit: 50, offset: 0 }, "GET /hymnals": hymnals({ items: [], effective_hymnal: null }) };
    const { unmount } = renderPage("admin", empty);
    expect(await screen.findByText("No hymns yet")).toBeInTheDocument();
    expect(screen.getByText(EMPTY_ADMIN)).toBeInTheDocument();
    unmount();
    renderPage("member", empty);
    expect(await screen.findByText(EMPTY_MEMBER)).toBeInTheDocument();
  });
});

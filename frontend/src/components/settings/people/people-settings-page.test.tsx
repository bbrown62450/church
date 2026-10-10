/**
 * Settings → People (slice 6b-2a; 6b spec UX §1 and Testing → Frontend DOM):
 * every member reads the list; owners and admins change roles and remove
 * people. Rendered inside the Settings layout, as the route is, with a Toaster.
 */
import { screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from "vitest";

import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
import PeopleSettingsRoute from "@/app/(signed-in)/(church)/settings/people/page";
import { Toaster } from "@/components/ui/sonner";
import type { Church, Invite, Member, MemberList } from "@/lib/api/types";
import { authEvents } from "@/lib/queries/auth-events";
import { keys } from "@/lib/queries/keys";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { church, invite, inviteList, me, memberList, PEOPLE } from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { MEMBERS_NOTE } from "./members-list";

/** The invite codes in these tests' fixtures: none may reach the console (codes are never logged). */
const FIXTURE_CODES = ["abc", "r-123", "r-1"];
const CONSOLE_METHODS = ["debug", "error", "info", "log", "trace", "warn"] as const;
let consoleSpies: MockInstance[] = [];

function printable(value: unknown): string {
  if (typeof value === "string") return value;
  if (value instanceof Error) return `${value.message} ${value.stack ?? ""}`;
  try {
    return JSON.stringify(value) ?? String(value);
  } catch {
    return String(value);
  }
}

beforeEach(() => {
  consoleSpies = CONSOLE_METHODS.map((method) => vi.spyOn(console, method));
});

afterEach(() => {
  toast.dismiss();
  const printed = consoleSpies.flatMap((spy) => spy.mock.calls.map((args) => args.map(printable).join(" ")));
  consoleSpies.forEach((spy) => spy.mockRestore());
  for (const line of printed) {
    expect(line).not.toMatch(/code=/);
    for (const code of FIXTURE_CODES) expect(line).not.toMatch(new RegExp(`\\b${code}\\b`));
  }
});

const ANN = { user_id: PEOPLE.ann, name: "Ann Admin", email: "ann@example.com" };

/** A fake `/members` whose `GET` answers with what the writes left, as the server would. */
function membersServer(initial: MemberList) {
  let items = [...initial.items];
  return {
    list: () => ({ items }),
    patch: (userId: string) => (r: RecordedRequest) => {
      items = items.map((m) => (m.user_id === userId ? { ...m, ...(r.body as Partial<Member>) } : m));
      return items.find((m) => m.user_id === userId);
    },
    remove: (userId: string) => () => {
      items = items.filter((m) => m.user_id !== userId);
      return { removed: true, revoked_invites: 2 };
    },
  };
}

function renderPage(role: Church["role"] = "admin", routes: Record<string, FakeHandler> = {}) {
  const active = church({ role });
  const api = installFakeApi({ "GET /members": memberList(role), "GET /invites": inviteList(), ...routes });
  const view = renderWithProviders(
    <>
      <SettingsLayout>
        <PeopleSettingsRoute />
      </SettingsLayout>
      <Toaster />
    </>,
    { me: me({ churches: [active] }), church: active, path: "/settings/people" },
  );
  return { ...view, api };
}

function rows() {
  return within(screen.getByRole("list", { name: "Members" })).getAllByRole("listitem");
}

function row(name: string) {
  return rows().find((r) => within(r).queryByText(name, { exact: true }) !== null)!;
}

function sent(api: { requests: RecordedRequest[] }, method: string) {
  return api.requests.filter((r) => r.method === method && r.path.startsWith("/members"));
}

async function openRemove(user: { click(e: Element): Promise<void> }, name: string) {
  await user.click(await screen.findByRole("button", { name: `Actions for ${name}` }));
  await user.click(await screen.findByRole("menuitem", { name: "Remove from church" }));
  return screen.findByRole("alertdialog", { name: `Remove ${name}?` });
}

describe("Settings → People: Members (slice 6b-2a)", () => {
  it("shows a member everyone with emails, their own row marked, and no actions", async () => {
    const { api } = renderPage("member");
    expect(await screen.findByRole("heading", { name: "Members (5)" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "People" })).toBeInTheDocument();
    expect(screen.getByText("Everyone in Grace can see this list.")).toBeInTheDocument();
    expect(screen.getByText(MEMBERS_NOTE)).toBeInTheDocument();
    expect(MEMBERS_NOTE).toBe("Only admins can change roles or remove people. To add someone, ask an admin for an invite link.");
    expect(rows().map((r) => r.textContent)).toEqual([
      "OOOlive Ownerolive@example.comOwner",
      "AAAnn Adminann@example.comAdmin",
      "MMMo Membermo@example.comMember",
      "PPPat PastorYoupat@example.comMember",
      "Ssam@example.comMember",
    ]);
    expect(screen.queryByRole("button", { name: /^Actions for / })).toBeNull();
    expect(api.requests.map((r) => `${r.method} ${r.path}`)).toEqual(["GET /members"]);
  });

  it("gives an admin a menu on members' and other admins' rows, never on the owner's or their own", async () => {
    renderPage("admin");
    await screen.findByRole("heading", { name: "Members (5)" });
    expect(screen.getAllByRole("button", { name: /^Actions for / }).map((b) => b.getAttribute("aria-label"))).toEqual([
      "Actions for Ann Admin",
      "Actions for Mo Member",
      "Actions for sam@example.com",
    ]);
    expect(screen.getByRole("button", { name: "Actions for Mo Member" })).toHaveClass("size-11");
    expect(screen.queryByText(MEMBERS_NOTE)).toBeNull();
  });

  it("lets the owner make an admin a member at once, and the badge follows", async () => {
    const server = membersServer(memberList("owner"));
    const { api, user } = renderPage("owner", {
      "GET /members": server.list,
      [`PATCH /members/${PEOPLE.ann}`]: server.patch(PEOPLE.ann),
    });
    await user.click(await screen.findByRole("button", { name: "Actions for Ann Admin" }));
    expect((await screen.findAllByRole("menuitem")).map((i) => i.textContent)).toEqual(["Make member", "Remove from church"]);
    await user.click(screen.getByRole("menuitem", { name: "Make member" }));
    await waitFor(() => expect(within(row("Ann Admin")).getByText("Member")).toBeInTheDocument());
    expect(sent(api, "PATCH")).toHaveLength(1);
    expect(sent(api, "PATCH")[0].body).toEqual({ role: "member" });
    expect(sent(api, "PATCH")[0].headers["x-church-id"]).toBe(church().id);
    expect(screen.queryByRole("alertdialog")).toBeNull();
  });

  it("lets an admin make a member an admin, with the menu busy while it runs", async () => {
    let release: () => void = () => {};
    const server = membersServer(memberList("admin"));
    const { user } = renderPage("admin", {
      "GET /members": server.list,
      [`PATCH /members/${PEOPLE.mo}`]: async (r: RecordedRequest) => {
        await new Promise<void>((resolve) => (release = resolve));
        return server.patch(PEOPLE.mo)(r);
      },
    });
    await user.click(await screen.findByRole("button", { name: "Actions for Mo Member" }));
    await user.click(await screen.findByRole("menuitem", { name: "Make admin" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Actions for Mo Member" })).toBeDisabled());
    release();
    await waitFor(() => expect(within(row("Mo Member")).getByText("Admin")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Actions for Mo Member" })).toBeEnabled();
  });

  it("asks before removing, says which links stop working, and revokes the reusable ones when left checked", async () => {
    const server = membersServer(memberList("admin"));
    const invites: Invite[] = [
      invite({ id: "c0000000-0000-4000-8000-000000000001", created_by: ANN }),
      invite({ id: "c0000000-0000-4000-8000-000000000002", created_by: ANN, email: "x@example.com" }),
      invite({ id: "c0000000-0000-4000-8000-000000000003", reusable: true }),
    ];
    const { api, user } = renderPage("admin", {
      "GET /members": server.list,
      "GET /invites": inviteList(invites),
      [`DELETE /members/${PEOPLE.ann}`]: server.remove(PEOPLE.ann),
    });
    const dialog = await openRemove(user, "Ann Admin");
    expect(dialog).toHaveAccessibleDescription("Ann Admin will lose access to Grace. Services they saved stay in the archive.");
    await waitFor(() => expect(within(dialog).getByText("The 2 invite links Ann Admin created will stop working.")).toBeInTheDocument());
    const box = within(dialog).getByRole("checkbox", { name: "Also revoke the 1 reusable invite link" });
    expect(box).toBeChecked();
    expect(within(dialog).getByText(/Anyone with a reusable link, including Ann Admin, can use it to rejoin until it expires\./)).toBeInTheDocument();
    const invitesReads = api.requests.filter((r) => r.path === "/invites").length;
    await user.click(within(dialog).getByRole("button", { name: "Remove member" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(sent(api, "DELETE").map((r) => r.path)).toEqual([`/members/${PEOPLE.ann}?revoke_reusable=true`]);
    await waitFor(() => expect(rows()).toHaveLength(4));
    expect(screen.queryByText("Ann Admin")).toBeNull();
    await waitFor(() => expect(api.requests.filter((r) => r.path === "/invites").length).toBeGreaterThan(invitesReads));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Members (4)" })).toHaveFocus());
  });

  it("sends revoke_reusable=false when the box is unchecked, and shows no box when no other reusable link exists", async () => {
    const server = membersServer(memberList("admin"));
    const { api, user } = renderPage("admin", {
      "GET /members": server.list,
      "GET /invites": inviteList([invite({ reusable: true })]),
      [`DELETE /members/${PEOPLE.mo}`]: server.remove(PEOPLE.mo),
      [`DELETE /members/${PEOPLE.sam}`]: server.remove(PEOPLE.sam),
    });
    let dialog = await openRemove(user, "Mo Member");
    await user.click(await within(dialog).findByRole("checkbox", { name: "Also revoke the 1 reusable invite link" }));
    // what the list holds once Mo is removed (the removal refetches it): only a link sam made
    api.set("GET /invites", inviteList([invite({ created_by: { user_id: PEOPLE.sam, name: null, email: "sam@example.com" }, reusable: true })]));
    await user.click(within(dialog).getByRole("button", { name: "Remove member" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    await waitFor(() => expect(rows()).toHaveLength(4));
    dialog = await openRemove(user, "sam@example.com");
    await waitFor(() => expect(within(dialog).getByText("The 1 invite link sam@example.com created will stop working.")).toBeInTheDocument());
    expect(within(dialog).queryByRole("checkbox")).toBeNull();
    await user.click(within(dialog).getByRole("button", { name: "Remove member" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(sent(api, "DELETE").map((r) => r.path)).toEqual([
      `/members/${PEOPLE.mo}?revoke_reusable=false`,
      `/members/${PEOPLE.sam}?revoke_reusable=false`,
    ]);
  });

  it("speaks generally, with the box checked, when the invites could not be read", async () => {
    const { api, user } = renderPage("admin", {
      "GET /invites": fakeError(500, "internal_error", "Something went wrong."),
      [`DELETE /members/${PEOPLE.mo}`]: { removed: true, revoked_invites: 0 },
    });
    const dialog = await openRemove(user, "Mo Member");
    expect(within(dialog).getByText("Any invite links Mo Member created will stop working.")).toBeInTheDocument();
    expect(within(dialog).getByRole("checkbox", { name: "Also revoke every reusable invite link" })).toBeChecked();
    await user.click(within(dialog).getByRole("button", { name: "Remove member" }));
    await waitFor(() => expect(sent(api, "DELETE").map((r) => r.path)).toEqual([`/members/${PEOPLE.mo}?revoke_reusable=true`]));
  });

  it("checks Also revoke again each time the dialog opens, even after it was unchecked and cancelled", async () => {
    const { api, user } = renderPage("admin", { "GET /invites": inviteList([invite({ reusable: true })]) });
    let dialog = await openRemove(user, "Mo Member");
    const box = await within(dialog).findByRole("checkbox", { name: "Also revoke the 1 reusable invite link" });
    await user.click(box);
    expect(box).not.toBeChecked();
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    dialog = await openRemove(user, "Mo Member");
    expect(await within(dialog).findByRole("checkbox", { name: "Also revoke the 1 reusable invite link" })).toBeChecked();
    expect(sent(api, "DELETE")).toEqual([]);
  });

  it("Cancel keeps the person and sends nothing", async () => {
    const { api, user } = renderPage("admin");
    const dialog = await openRemove(user, "Mo Member");
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(sent(api, "DELETE")).toEqual([]);
    expect(rows()).toHaveLength(5);
  });

  it("toasts the server's refusal and refetches the role and the list, staying in the church", async () => {
    const lost = vi.fn();
    const unsubscribe = authEvents.onChurchAccessLost(lost);
    const { user, queryClient } = renderPage("admin", {
      [`DELETE /members/${PEOPLE.mo}`]: fakeError(403, "forbidden", "Only church admins can do this."),
    });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const dialog = await openRemove(user, "Mo Member");
    await user.click(within(dialog).getByRole("button", { name: "Remove member" }));
    expect(await screen.findByText("Only church admins can do this.")).toBeInTheDocument();
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.churchProfile(church().id) });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.members(church().id) });
    expect(lost).not.toHaveBeenCalled();
    unsubscribe();
  });

  it("toasts a role refusal of the invite list, refetches the role and the list, and stays in the church", async () => {
    const lost = vi.fn();
    const unsubscribe = authEvents.onChurchAccessLost(lost);
    const { queryClient } = renderPage("admin", {
      "GET /invites": fakeError(403, "forbidden", "Only church admins can do this."),
    });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    expect(await screen.findByText("Only church admins can do this.")).toBeInTheDocument();
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.churchProfile(church().id) });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.members(church().id) });
    expect(lost).not.toHaveBeenCalled();
    unsubscribe();
  });

  it("leaves a lost church to the app: a no_church_access 403 on a role change reports the church", async () => {
    const lost = vi.fn();
    const unsubscribe = authEvents.onChurchAccessLost(lost);
    const { user } = renderPage("admin", {
      [`PATCH /members/${PEOPLE.mo}`]: fakeError(403, "forbidden", "You don't have access to this church.", {
        details: { reason: "no_church_access" },
      }),
    });
    await user.click(await screen.findByRole("button", { name: "Actions for Mo Member" }));
    await user.click(await screen.findByRole("menuitem", { name: "Make admin" }));
    await waitFor(() => expect(lost).toHaveBeenCalledWith(church().id));
    expect(screen.queryByText("You don't have access to this church.")).toBeNull();
    unsubscribe();
  });

  it("never keeps the invite list as fresh, since its codes are secrets (staleTime 0)", async () => {
    const { queryClient } = renderPage("admin");
    await screen.findByRole("heading", { name: "Members (5)" });
    await waitFor(() => expect(queryClient.getQueryCache().find({ queryKey: keys.invites(church().id) })?.state.status).toBe("success"));
    const query = queryClient.getQueryCache().find({ queryKey: keys.invites(church().id) })!;
    expect(new Set(query.observers.map((observer) => observer.options.staleTime))).toEqual(new Set([0]));
  });

  it("shows the error state with Retry when the list cannot be read", async () => {
    const { api, user } = renderPage("member", { "GET /members": fakeError(500, "internal_error", "Something went wrong.") });
    expect(await screen.findByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(screen.queryByRole("list", { name: "Members" })).toBeNull();
    api.set("GET /members", memberList("member"));
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("heading", { name: "Members (5)" })).toBeInTheDocument();
  });
});

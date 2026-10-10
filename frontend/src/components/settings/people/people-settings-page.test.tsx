/**
 * Settings → People (slice 6b-2a; 6b spec UX §1 and Testing → Frontend DOM):
 * every member reads the list; owners and admins change roles and remove
 * people. Rendered inside the Settings layout, as the route is, with a Toaster.
 */
import { screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from "vitest";

import ChurchLayout from "@/app/(signed-in)/(church)/layout";
import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
import PeopleSettingsRoute from "@/app/(signed-in)/(church)/settings/people/page";
import { Toaster } from "@/components/ui/sonner";
import type { Church, Invite, Member, MemberList } from "@/lib/api/types";
import { authEvents } from "@/lib/queries/auth-events";
import { keys } from "@/lib/queries/keys";
import { ACTIVE_CHURCH_KEY } from "@/lib/storage";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { church, churchProfile, invite, inviteList, me, memberList, PEOPLE } from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { EMAIL_HELP, INVITE_CREATED, ONE_EMAIL_ONCE, REUSABLE_HELP, ROLE_HELP } from "./create-invite-form";
import { MEMBERS_NOTE } from "./members-list";

/** Breaks a long email anywhere, so it wraps at 375 px instead of widening the page (as the rows do). */
const WRAP = "[overflow-wrap:anywhere]";

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

  it("keeps each running role change's row busy, not only the latest one's", async () => {
    const releases: Record<string, () => void> = {};
    const server = membersServer(memberList("admin"));
    const held = (userId: string) => async (r: RecordedRequest) => {
      await new Promise<void>((resolve) => (releases[userId] = resolve));
      return server.patch(userId)(r);
    };
    const { user } = renderPage("admin", {
      "GET /members": server.list,
      [`PATCH /members/${PEOPLE.mo}`]: held(PEOPLE.mo),
      [`PATCH /members/${PEOPLE.sam}`]: held(PEOPLE.sam),
    });
    const busy = (name: string) => {
      const trigger = screen.getByRole("button", { name: `Actions for ${name}` });
      expect(trigger).toBeDisabled();
      expect(trigger).toHaveAttribute("aria-busy", "true");
      expect(trigger.querySelector(".animate-spin")).not.toBeNull();
    };
    await user.click(await screen.findByRole("button", { name: "Actions for Mo Member" }));
    await user.click(await screen.findByRole("menuitem", { name: "Make admin" }));
    await waitFor(() => busy("Mo Member"));
    await user.click(screen.getByRole("button", { name: "Actions for sam@example.com" }));
    await user.click(await screen.findByRole("menuitem", { name: "Make admin" }));
    await waitFor(() => busy("sam@example.com"));
    busy("Mo Member");
    expect(screen.getByRole("button", { name: "Actions for Ann Admin" })).toBeEnabled();
    releases[PEOPLE.sam]();
    await waitFor(() => expect(screen.getByRole("button", { name: "Actions for sam@example.com" })).toBeEnabled());
    busy("Mo Member");
    releases[PEOPLE.mo]();
    await waitFor(() => expect(screen.getByRole("button", { name: "Actions for Mo Member" })).toBeEnabled());
    expect(within(row("Mo Member")).getByText("Admin")).toBeInTheDocument();
    expect(within(row("sam@example.com")).getByText("Admin")).toBeInTheDocument();
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
    // an email-only name wraps anywhere in the title, the description and the body
    expect(within(dialog).getByText("Remove sam@example.com?")).toHaveClass(WRAP);
    expect(within(dialog).getByText("sam@example.com will lose access to Grace. Services they saved stay in the archive.")).toHaveClass(WRAP);
    expect(within(dialog).getByText("The 1 invite link sam@example.com created will stop working.").closest(`.${CSS.escape(WRAP)}`)).not.toBeNull();
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

  it("shows names and emails with markup in them as text, never as HTML", async () => {
    const list = memberList("admin");
    list.items = list.items.map((m) =>
      m.user_id === PEOPLE.mo ? { ...m, name: "<b>x</b>", email: "<i>y</i>@example.com" } : m,
    );
    const maker = { user_id: PEOPLE.mo, name: "<b>x</b>", email: "<i>y</i>@example.com" };
    renderPage("admin", {
      "GET /members": list,
      "GET /invites": inviteList([invite({ email: "<img src=x>@example.com", created_by: maker })]),
    });
    await screen.findByRole("heading", { name: "Pending invites (1)" });
    const mo = row("<b>x</b>");
    expect(within(mo).getByText("<i>y</i>@example.com")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Actions for <b>x</b>" })).toBeInTheDocument();
    const pending = inviteRows()[0];
    expect(within(pending).getByText("<img src=x>@example.com")).toBeInTheDocument();
    expect(pending.textContent).toContain("Created by <b>x</b>");
    expect(document.body.querySelectorAll("b, i, img")).toHaveLength(0);
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

const CODE_FREE = invite();
const NEW_LINK = "http://localhost:3000/join?code=abc";

function invitesSent(api: { requests: RecordedRequest[] }, method: string) {
  return api.requests.filter((r) => r.method === method && r.path.startsWith("/invites"));
}

function inviteRows() {
  return within(screen.getByRole("list", { name: "Pending invites" })).getAllByRole("listitem");
}

/** A fake `/invites`: `POST` adds the answer first, `DELETE` revokes, `GET` lists what is left. */
function invitesServer(initial: Invite[] = []) {
  let items = [...initial];
  return {
    list: () => inviteList(items),
    add: (made: Invite) => () => {
      items = [made, ...items.filter((i) => i.id !== made.id)];
      return { status: 201, body: made };
    },
    revoke: (id: string) => () => {
      items = items.filter((i) => i.id !== id);
      return { revoked: true };
    },
  };
}

describe("Settings → People: Invite someone and Pending invites (slice 6b-2a)", () => {
  it("shows a member neither the invite form nor the pending invites", async () => {
    renderPage("member");
    await screen.findByRole("heading", { name: "Members (5)" });
    expect(screen.queryByRole("heading", { name: "Invite someone" })).toBeNull();
    expect(screen.queryByRole("heading", { name: /^Pending invites/ })).toBeNull();
    expect(screen.queryByRole("button", { name: "Create invite link" })).toBeNull();
  });

  it("puts Invite someone, Members and Pending invites in that order for an admin", async () => {
    renderPage("admin");
    await screen.findByRole("heading", { name: "Pending invites (0)" });
    expect(screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual([
      "Invite someone",
      "Members (5)",
      "Pending invites (0)",
    ]);
    expect(screen.getByText("No pending invites")).toBeInTheDocument();
    expect(screen.getByText("Create an invite link above to add someone to Grace.")).toBeInTheDocument();
  });

  it("creates a single-use member link, shows it with Copy link focused, and copies it", async () => {
    const server = invitesServer();
    const { api, user } = renderPage("admin", { "GET /invites": server.list, "POST /invites": server.add(CODE_FREE) });
    const form = within((await screen.findByRole("heading", { name: "Invite someone" })).closest("section")!);
    expect(form.getByRole("radio", { name: /^Member/ })).toBeChecked();
    expect(form.getByRole("radio", { name: /^Member/ })).toHaveAccessibleDescription(ROLE_HELP.member);
    expect(form.getByRole("radio", { name: /^Admin/ })).toHaveAccessibleDescription(ROLE_HELP.admin);
    expect(form.getByLabelText("Email (optional)")).toHaveAccessibleDescription(EMAIL_HELP);
    expect(form.getByRole("checkbox", { name: "Reusable for 7 days" })).toHaveAccessibleDescription(REUSABLE_HELP);
    await user.click(form.getByRole("button", { name: "Create invite link" }));

    const panel = await screen.findByRole("group", { name: "Invite link ready" });
    expect(within(panel).getByLabelText("Invite link")).toHaveValue(NEW_LINK);
    await waitFor(() => expect(within(panel).getByRole("button", { name: "Copy link" })).toHaveFocus());
    expect(screen.getByText(INVITE_CREATED).closest('[aria-live="polite"]')).not.toBeNull();
    expect(within(panel).getByText(/^Anyone who opens this link can join Grace as a member\. It works once and expires .+\.$/)).toBeInTheDocument();
    const post = invitesSent(api, "POST")[0];
    expect(post.body).toEqual({ role: "member", email: null, reusable: false });
    expect(post.headers["idempotency-key"]).toMatch(/^[0-9a-f-]{36}$/);
    expect(post.headers["x-church-id"]).toBe(church().id);

    await user.click(within(panel).getByRole("button", { name: "Copy link" }));
    expect(await screen.findByText("Link copied")).toBeInTheDocument();
    expect(await navigator.clipboard.readText()).toBe(NEW_LINK);
    expect(within(panel).getByRole("button", { name: "Copied ✓" })).toBeInTheDocument();
    expect(within(panel).queryByRole("button", { name: "Share…" })).toBeNull();

    await waitFor(() => expect(inviteRows()).toHaveLength(1));
    await user.click(within(panel).getByRole("button", { name: "Done" }));
    expect(screen.queryByRole("group", { name: "Invite link ready" })).toBeNull();
    expect(form.getByRole("button", { name: "Create invite link" })).toHaveFocus();
    expect(inviteRows()).toHaveLength(1);
  });

  it("lets the created link's code leave the mutation cache once the form is gone (gcTime 0)", async () => {
    const server = invitesServer();
    const { user, queryClient, unmount } = renderPage("admin", { "GET /invites": server.list, "POST /invites": server.add(CODE_FREE) });
    await user.click(await screen.findByRole("button", { name: "Create invite link" }));
    await screen.findByRole("group", { name: "Invite link ready" });
    const created = () => queryClient.getMutationCache().getAll().filter((m) => (m.state.data as Invite | undefined)?.code === "abc");
    expect(created().map((m) => m.options.gcTime)).toEqual([0]);
    unmount();
    await waitFor(() => expect(created()).toEqual([]));
  });

  it("sends an admin, reusable link with a new key each time, and says who can use it", async () => {
    const reusable = invite({ id: "c0000000-0000-4000-8000-000000000009", code: "r-123", role: "admin", reusable: true });
    const server = invitesServer();
    const { api, user } = renderPage("admin", { "GET /invites": server.list, "POST /invites": server.add(reusable) });
    const form = within((await screen.findByRole("heading", { name: "Invite someone" })).closest("section")!);
    await user.click(form.getByRole("radio", { name: /^Admin/ }));
    await user.click(form.getByRole("checkbox", { name: "Reusable for 7 days" }));
    await user.click(form.getByRole("button", { name: "Create invite link" }));
    const panel = await screen.findByRole("group", { name: "Invite link ready" });
    expect(within(panel).getByText(/^Anyone with this link can join Grace as an admin until .+\. Share it only with people you trust\.$/)).toBeInTheDocument();
    expect(form.getByRole("radio", { name: /^Member/ })).toBeChecked();
    expect(form.getByRole("checkbox", { name: "Reusable for 7 days" })).not.toBeChecked();
    await user.click(form.getByRole("button", { name: "Create invite link" }));
    await waitFor(() => expect(invitesSent(api, "POST")).toHaveLength(2));
    const [first, second] = invitesSent(api, "POST");
    expect(first.body).toEqual({ role: "admin", email: null, reusable: true });
    expect(second.body).toEqual({ role: "member", email: null, reusable: false });
    expect(first.headers["idempotency-key"]).not.toBe(second.headers["idempotency-key"]);
  });

  it("turns Reusable off while an email is typed, and sends the email trimmed", async () => {
    const bound = invite({ email: "b@example.com" });
    const server = invitesServer();
    const { api, user } = renderPage("admin", { "GET /invites": server.list, "POST /invites": server.add(bound) });
    const form = within((await screen.findByRole("heading", { name: "Invite someone" })).closest("section")!);
    const box = form.getByRole("checkbox", { name: "Reusable for 7 days" });
    await user.click(box);
    expect(box).toBeChecked();
    await user.type(form.getByLabelText("Email (optional)"), " b@example.com ");
    expect(box).toBeDisabled();
    expect(box).not.toBeChecked();
    expect(box).toHaveAccessibleDescription(ONE_EMAIL_ONCE);
    await user.click(form.getByRole("button", { name: "Create invite link" }));
    const panel = await screen.findByRole("group", { name: "Invite link ready" });
    expect(invitesSent(api, "POST")[0].body).toEqual({ role: "member", email: "b@example.com", reusable: false });
    expect(within(panel).getByText(/^Only b@example\.com can use this link to join Grace as a member\. It works once and expires .+\.$/)).toHaveClass(WRAP);
    expect(form.getByLabelText("Email (optional)")).toHaveValue("");
  });

  it("says under Email when the address has a pending invite or is a member, and focuses it", async () => {
    const pending = "There's already a pending invite for b@example.com. Copy its link below or revoke it first.";
    const { api, user } = renderPage("admin", { "POST /invites": fakeError(409, "invite_exists", pending) });
    const form = within((await screen.findByRole("heading", { name: "Invite someone" })).closest("section")!);
    const email = form.getByLabelText("Email (optional)");
    await user.type(email, "b@example.com");
    await user.click(form.getByRole("button", { name: "Create invite link" }));
    expect(await form.findByRole("alert")).toHaveTextContent(pending);
    expect(form.getByRole("alert")).toHaveClass(WRAP);
    await waitFor(() => expect(email).toHaveFocus());
    expect(email).toHaveAttribute("aria-invalid", "true");
    expect(email).toHaveValue("b@example.com");
    expect(screen.queryByText(pending, { selector: "[data-sonner-toast] *" })).toBeNull();

    api.set("POST /invites", fakeError(409, "conflict", "b@example.com is already a member of this church."));
    await user.click(form.getByRole("button", { name: "Create invite link" }));
    expect(await form.findByText("b@example.com is already a member of this church.")).toBeInTheDocument();

    api.set("POST /invites", fakeError(422, "invalid_request", "Enter a valid email address.", { fields: { email: "Enter a valid email address." } }));
    await user.click(form.getByRole("button", { name: "Create invite link" }));
    expect(await form.findByText("Enter a valid email address.")).toBeInTheDocument();
    await user.type(email, "x");
    expect(form.queryByRole("alert")).toBeNull();
  });

  it("offers Share on a device that can share, with the church's words and the link", async () => {
    const share = vi.fn(async () => {});
    Object.defineProperty(navigator, "share", { value: share, configurable: true });
    try {
      const server = invitesServer();
      const { user } = renderPage("admin", { "GET /invites": server.list, "POST /invites": server.add(CODE_FREE) });
      await user.click(await screen.findByRole("button", { name: "Create invite link" }));
      const panel = await screen.findByRole("group", { name: "Invite link ready" });
      await user.click(within(panel).getByRole("button", { name: "Share…" }));
      expect(share).toHaveBeenCalledWith({
        title: "Join Grace",
        text: "You're invited to plan worship with Grace.",
        url: NEW_LINK,
      });
    } finally {
      delete (navigator as { share?: unknown }).share;
    }
  });

  it("lists pending invites with their role, type, expiry and maker, and copies a row's link", async () => {
    const items = [
      invite({ id: "c0000000-0000-4000-8000-000000000001", email: "b@example.com", role: "admin", created_by: ANN }),
      invite({ id: "c0000000-0000-4000-8000-000000000002", code: "r-1", reusable: true, created_by: null }),
    ];
    const { user } = renderPage("admin", { "GET /invites": inviteList(items) });
    await screen.findByRole("heading", { name: "Pending invites (2)" });
    expect(inviteRows().map((r) => r.textContent)).toEqual([
      "b@example.comAdminSingle useExpires in 7 days · Created by Ann AdminCopy linkRevoke",
      "Anyone with the linkMemberReusableExpires in 7 days · Created by a former memberCopy linkRevoke",
    ]);
    const expiry = within(inviteRows()[0]).getByText("Expires in 7 days");
    expect(expiry).toHaveAttribute("title", expect.stringMatching(/^[A-Z][a-z]{2} \d{1,2}, \d{4}, \d{1,2}:\d{2} [AP]M$/));
    expect(expiry).toHaveAttribute("aria-label", `Expires ${expiry.getAttribute("title")}`);
    await user.click(screen.getByRole("button", { name: "Copy link for Anyone with the link" }));
    expect(await navigator.clipboard.readText()).toBe("http://localhost:3000/join?code=r-1");
    expect(within(inviteRows()[1]).getByRole("button", { name: "Copied ✓" })).toBeInTheDocument();
  });

  it("shows a row's link, selected, when copying is refused", async () => {
    const { user } = renderPage("admin", { "GET /invites": inviteList([CODE_FREE]) });
    const copy = await screen.findByRole("button", { name: "Copy link for Anyone with the link" });
    vi.spyOn(navigator.clipboard, "writeText").mockRejectedValue(new DOMException("Not allowed", "NotAllowedError"));
    const realExecCommand = document.execCommand;
    document.execCommand = vi.fn(() => false);
    try {
      await user.click(copy);
      const link = await screen.findByRole("textbox", { name: "Invite link for Anyone with the link" });
      expect(link).toHaveValue(NEW_LINK);
      await waitFor(() => expect(link).toHaveFocus());
      expect(await screen.findByText("Couldn't copy. The link is selected; copy it from there.")).toBeInTheDocument();
    } finally {
      document.execCommand = realExecCommand;
    }
  });

  it("revokes an invite after asking, and the list empties", async () => {
    const server = invitesServer([CODE_FREE]);
    const { api, user } = renderPage("admin", {
      "GET /invites": server.list,
      [`DELETE /invites/${CODE_FREE.id}`]: server.revoke(CODE_FREE.id),
    });
    await user.click(await screen.findByRole("button", { name: "Revoke the invite for Anyone with the link" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Revoke this invite?" });
    expect(dialog).toHaveAccessibleDescription("The link will stop working. People who already joined stay in the church.");
    await user.click(within(dialog).getByRole("button", { name: "Revoke invite" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(invitesSent(api, "DELETE").map((r) => r.path)).toEqual([`/invites/${CODE_FREE.id}`]);
    expect(await screen.findByText("No pending invites")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("heading", { name: "Pending invites (0)" })).toHaveFocus());
  });

  it("clears the link panel when its invite is revoked", async () => {
    const server = invitesServer();
    const { user } = renderPage("admin", {
      "GET /invites": server.list,
      "POST /invites": server.add(CODE_FREE),
      [`DELETE /invites/${CODE_FREE.id}`]: server.revoke(CODE_FREE.id),
    });
    await user.click(await screen.findByRole("button", { name: "Create invite link" }));
    await screen.findByRole("group", { name: "Invite link ready" });
    await user.click(await screen.findByRole("button", { name: "Revoke the invite for Anyone with the link" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Revoke this invite?" });
    await user.click(within(dialog).getByRole("button", { name: "Revoke invite" }));
    await waitFor(() => expect(screen.queryByRole("group", { name: "Invite link ready" })).toBeNull());
    expect(screen.queryByDisplayValue(NEW_LINK)).toBeNull();
    expect(screen.queryByText(INVITE_CREATED)).toBeNull();
  });

  it("turns read-only inside the church layout once GET /church says member after a refusal, and drops the codes", async () => {
    window.localStorage.setItem(ACTIVE_CHURCH_KEY, church().id);
    let role: Church["role"] = "admin";
    const api = installFakeApi({
      "GET /church": () => churchProfile({ role }),
      "GET /members": () => memberList(role),
      "GET /invites": inviteList([CODE_FREE]),
      [`DELETE /invites/${CODE_FREE.id}`]: () => {
        role = "member"; // demoted elsewhere just before
        return fakeError(403, "forbidden", "Only church admins can do this.");
      },
    });
    const { user, queryClient } = renderWithProviders(
      <>
        <ChurchLayout>
          <SettingsLayout>
            <PeopleSettingsRoute />
          </SettingsLayout>
        </ChurchLayout>
        <Toaster />
      </>,
      { me: me(), path: "/settings/people" },
    );
    await user.click(await screen.findByRole("button", { name: "Revoke the invite for Anyone with the link" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Revoke this invite?" });
    await user.click(within(dialog).getByRole("button", { name: "Revoke invite" }));
    expect(await screen.findByText("Only church admins can do this.")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(MEMBERS_NOTE)).toBeInTheDocument());
    expect(screen.getByRole("heading", { level: 2, name: "People" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Invite someone" })).toBeNull();
    expect(screen.queryByRole("button", { name: /^Actions for / })).toBeNull();
    expect(screen.queryByRole("heading", { name: /^Pending invites/ })).toBeNull();
    expect(api.requests.filter((r) => r.path === "/church")).toHaveLength(2);
    expect(queryClient.getQueryData(keys.invites(church().id))).toBeUndefined();
  });
});

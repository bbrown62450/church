/**
 * Settings → Danger zone (slice 6b-2b; 6b spec UX §2 and Testing → Frontend
 * DOM): everyone may leave; only the owner transfers ownership or deletes the
 * church. Rendered inside the Settings layout, as the route is, with a
 * Toaster; the leave and delete exits also inside the real `(signed-in)` and
 * `(church)` layouts, so the switch to the next church and the absence of the
 * "no longer have access" toast are the app's own.
 */
import { act, screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, describe, expect, it, vi } from "vitest";

import SignedInLayout from "@/app/(signed-in)/layout";
import ChurchLayout from "@/app/(signed-in)/(church)/layout";
import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
import DangerZoneRoute from "@/app/(signed-in)/(church)/settings/danger/page";
import { Toaster } from "@/components/ui/sonner";
import type { Church, Member } from "@/lib/api/types";
import { EXIT_ME_FAILED } from "@/lib/church-exit";
import { authEvents } from "@/lib/queries/auth-events";
import { CHURCH_DELETED, leftChurch, TRANSFERRED } from "@/lib/queries/church";
import { keys } from "@/lib/queries/keys";
import { ACTIVE_CHURCH_KEY } from "@/lib/storage";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { CHURCH_IDS, USER_ID, church, member, memberList, me, PEOPLE } from "@/test/fixtures";
import { testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import { OWNER_ONLY_NOTE } from "./danger-zone-page";
import { deleteBody, deleteText } from "./delete-church-card";
import { leaveText, OWNER_MUST_TRANSFER, ownerAloneText } from "./leave-church-card";
import { INVITE_FIRST, TRANSFER_TEXT } from "./transfer-ownership-card";

/** Breaks a long name anywhere, so it wraps at 375 px instead of widening the page. */
const WRAP = "[overflow-wrap:anywhere]";

const GRACE_DRAFT = `wsb:draft:${USER_ID}:${CHURCH_IDS.grace}`;
const GRACE_CORRUPT = `wsb:draft-corrupt:${USER_ID}:${CHURCH_IDS.grace}`;

afterEach(() => {
  toast.dismiss();
});

/** Pat (`USER_ID`) as the only person in the church: the owner alone. */
function alone(): { items: Member[] } {
  return { items: [member({ user_id: USER_ID, email: "pat@example.com", name: "Pat Pastor", role: "owner", is_me: true })] };
}

/** The page inside the Settings layout, for Grace with `role` (a static church; no exit layouts). */
function renderPage(role: Church["role"] = "owner", routes: Record<string, FakeHandler> = {}, name = "Grace") {
  const active = church({ role, name });
  const api = installFakeApi({ "GET /members": memberList(role), ...routes });
  const view = renderWithProviders(
    <>
      <SettingsLayout>
        <DangerZoneRoute />
      </SettingsLayout>
      <Toaster />
    </>,
    { me: me({ churches: [active] }), church: active, path: "/settings/danger" },
  );
  return { ...view, api };
}

/**
 * The page inside the real `(signed-in)` and `(church)` layouts, Grace shown
 * (Pat is `role` there) and Hope (member) the other church. `POST
 * /church/leave` and `DELETE /church` take Grace out of `/me`, as the server
 * does; `GET /church` then refuses Grace.
 */
function renderShell(role: Church["role"], routes: Record<string, FakeHandler> = {}) {
  const grace = church({ role });
  const hope = church({ id: CHURCH_IDS.hope, name: "Hope", role: "member" });
  let graceGone = false;
  const gone = (answer: unknown) => () => {
    graceGone = true;
    return answer;
  };
  window.localStorage.setItem(ACTIVE_CHURCH_KEY, grace.id);
  window.localStorage.setItem(GRACE_DRAFT, "{}");
  window.localStorage.setItem(GRACE_CORRUPT, "{}");
  const api = installFakeApi({
    "GET /me": () => me({ churches: graceGone ? [hope] : [grace, hope] }),
    "GET /church": (r: RecordedRequest) => {
      if (r.headers["X-Church-Id"] === hope.id) return hope;
      return graceGone
        ? fakeError(403, "forbidden", "You don't have access to this church.", { details: { reason: "no_church_access" } })
        : grace;
    },
    "GET /members": memberList(role),
    "POST /church/leave": gone({ left: true }),
    "DELETE /church": gone({ deleted: true }),
    ...routes,
  });
  const view = renderWithProviders(
    <>
      <SignedInLayout>
        <ChurchLayout>
          <SettingsLayout>
            <DangerZoneRoute />
          </SettingsLayout>
        </ChurchLayout>
      </SignedInLayout>
      <Toaster />
    </>,
    { path: "/settings/danger" },
  );
  return { ...view, api };
}

function sent(api: { requests: RecordedRequest[] }, method: string, path: string) {
  return api.requests.filter((r) => r.method === method && r.path === path);
}

/** Everything the page and its open dialogs say. */
function allText(): string {
  return document.body.textContent ?? "";
}

describe("Settings → Danger zone: admins and members (slice 6b-2b)", () => {
  it.each(["member", "admin"] as const)("shows %s the owner-only note and Leave church only", async (role) => {
    const { api } = renderPage(role);
    expect(await screen.findByRole("heading", { level: 2, name: "Danger zone" })).toBeInTheDocument();
    expect(screen.getByRole("note")).toHaveTextContent(OWNER_ONLY_NOTE);
    expect(OWNER_ONLY_NOTE).toBe("Only the owner can transfer ownership or delete the church.");
    expect(screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual(["Leave Grace"]);
    expect(screen.getByText(leaveText("Grace"))).toBeInTheDocument();
    expect(leaveText("Grace")).toBe(
      "You'll lose access to Grace's services, hymns and settings. To come back you'll need a new invite.",
    );
    expect(screen.getByRole("button", { name: "Leave church…" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: "Transfer ownership…" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Delete church…" })).toBeNull();
    expect(api.requests).toEqual([]);
  });

  it("leaves after asking, says so, drops the draft and moves to the next church with no access toast", async () => {
    const error = vi.spyOn(toast, "error");
    const { api, user } = renderShell("member");
    await user.click(await screen.findByRole("button", { name: "Leave church…" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Leave Grace?" });
    expect(dialog).toHaveAccessibleDescription(
      "You'll lose access right away. Your unsaved draft for Grace on this device will be discarded.",
    );
    await user.click(within(dialog).getByRole("button", { name: "Leave church" }));
    expect(await screen.findByText(leftChurch("Grace"))).toBeInTheDocument();
    expect(leftChurch("Grace")).toBe("You left Grace.");
    expect(await screen.findByRole("heading", { level: 3, name: "Leave Hope" })).toBeInTheDocument();
    expect(sent(api, "POST", "/church/leave")).toHaveLength(1);
    expect(sent(api, "POST", "/church/leave")[0].headers["x-church-id"]).toBe(CHURCH_IDS.grace);
    expect(testRouter.replace).toHaveBeenCalledWith("/");
    expect(window.localStorage.getItem(GRACE_DRAFT)).toBeNull();
    expect(window.localStorage.getItem(GRACE_CORRUPT)).toBeNull();
    await waitFor(() => expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBe(CHURCH_IDS.hope));
    expect(screen.queryByText(/no longer have access/)).toBeNull();
    expect(error).not.toHaveBeenCalled();
    error.mockRestore();
  });

  it("sends one leave for a double tap", async () => {
    let release: () => void = () => {};
    const { api, user } = renderPage("member", {
      "POST /church/leave": () => new Promise((resolve) => (release = () => resolve({ left: true }))),
      "GET /me": me(),
    });
    await user.click(await screen.findByRole("button", { name: "Leave church…" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Leave Grace?" });
    await user.dblClick(within(dialog).getByRole("button", { name: "Leave church" }));
    expect(sent(api, "POST", "/church/leave")).toHaveLength(1);
    expect(await within(dialog).findByRole("button", { name: "Leaving…" })).toHaveAttribute("aria-disabled", "true");
    await user.click(within(dialog).getByRole("button", { name: "Leaving…" }));
    expect(sent(api, "POST", "/church/leave")).toHaveLength(1);
    release();
    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/"));
    expect(sent(api, "POST", "/church/leave")).toHaveLength(1);
  });

  it("toasts the server's refusal, closes the dialog and stays", async () => {
    const message = "You're the last admin. Make someone else an admin before you leave.";
    const { user } = renderPage("admin", { "POST /church/leave": fakeError(409, "last_admin", message) });
    await user.click(await screen.findByRole("button", { name: "Leave church…" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Leave Grace?" });
    await user.click(within(dialog).getByRole("button", { name: "Leave church" }));
    expect(await screen.findByText(message)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(testRouter.replace).not.toHaveBeenCalled();
    expect(screen.getByRole("heading", { level: 3, name: "Leave Grace" })).toBeInTheDocument();
  });

  it("keeps the dialog on Leaving… until the exit is done", async () => {
    let release: () => void = () => {};
    const { api, user } = renderPage("member", {
      "POST /church/leave": { left: true },
      "GET /me": () => new Promise((resolve) => (release = () => resolve(me()))),
    });
    await user.click(await screen.findByRole("button", { name: "Leave church…" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Leave Grace?" });
    await user.click(within(dialog).getByRole("button", { name: "Leave church" }));
    expect(await screen.findByText(leftChurch("Grace"))).toBeInTheDocument();
    await waitFor(() => expect(sent(api, "GET", "/me")).toHaveLength(1));
    expect(within(dialog).getByRole("button", { name: "Leaving…" })).toHaveAttribute("aria-disabled", "true");
    expect(testRouter.replace).not.toHaveBeenCalled();
    release();
    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/"));
  });

  it("leaves a lost church to the app's one message, with no toast of its own", async () => {
    const error = vi.spyOn(toast, "error");
    const refused = "You don't have access to this church.";
    const { user } = renderShell("member", {
      "POST /church/leave": fakeError(403, "forbidden", refused, { details: { reason: "no_church_access" } }),
    });
    await user.click(await screen.findByRole("button", { name: "Leave church…" }));
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Leave church" }));
    expect(await screen.findByText("You no longer have access to Grace.")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { level: 3, name: "Leave Hope" })).toBeInTheDocument();
    expect(error.mock.calls).toEqual([["You no longer have access to Grace."]]);
    expect(screen.queryByText(refused)).toBeNull();
    error.mockRestore();
  });

  it("says when /me does not come back after leaving", async () => {
    const { user } = renderPage("member", {
      "POST /church/leave": { left: true },
      "GET /me": fakeError(503, "db_unavailable", "The database is unavailable."),
    });
    await user.click(await screen.findByRole("button", { name: "Leave church…" }));
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Leave church" }));
    expect(await screen.findByText(EXIT_ME_FAILED)).toBeInTheDocument();
    expect(EXIT_ME_FAILED).toBe("Can't reach the server. Check your connection and try again.");
    expect(screen.getByText("You left Grace.")).toBeInTheDocument();
    expect(testRouter.replace).toHaveBeenCalledWith("/");
  });
});

describe("Settings → Danger zone: the owner (slice 6b-2b)", () => {
  it("shows Leave off with why, Transfer and Delete, and no owner-only note", async () => {
    renderPage("owner");
    expect(await screen.findByRole("heading", { level: 3, name: "Transfer ownership" })).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual([
      "Leave Grace",
      "Transfer ownership",
      "Delete Grace",
    ]);
    expect(screen.queryByRole("note")).toBeNull();
    expect(screen.getByRole("button", { name: "Leave church…" })).toBeDisabled();
    expect(screen.getByText(OWNER_MUST_TRANSFER)).toBeInTheDocument();
    expect(OWNER_MUST_TRANSFER).toBe("You're the owner. Transfer ownership below before you leave.");
    expect(screen.getByText(TRANSFER_TEXT)).toBeInTheDocument();
    expect(screen.getByText(deleteText("Grace"))).toBeInTheDocument();
    expect(deleteText("Grace")).toBe("Deleting Grace removes it for everyone. Pending invite links stop working.");
    for (const id of ["leave-title", "delete-title"]) {
      expect(document.getElementById(id)!.closest("section")).toHaveClass("border-destructive/40");
    }
  });

  it("tells the owner alone to delete instead of leaving, and to invite someone before a transfer", async () => {
    renderPage("owner", { "GET /members": alone() });
    expect(await screen.findByText(ownerAloneText("Grace"))).toBeInTheDocument();
    expect(ownerAloneText("Grace")).toBe("You're the only person in Grace. To stop using it, delete the church below.");
    expect(screen.getByRole("button", { name: "Leave church…" })).toBeDisabled();
    expect(screen.getByText(INVITE_FIRST, { exact: false })).toBeInTheDocument();
    expect(INVITE_FIRST).toBe("Invite another member first to transfer ownership.");
    expect(screen.getByRole("link", { name: "Invite someone" })).toHaveAttribute("href", "/settings/people");
    expect(screen.queryByRole("button", { name: "Transfer ownership…" })).toBeNull();
  });

  it("transfers to the person chosen, admins listed first, after asking", async () => {
    const { api, user, queryClient } = renderPage("owner", { "POST /church/transfer-ownership": memberList("admin") });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const start = await screen.findByRole("button", { name: "Transfer ownership…" });
    expect(start).toBeDisabled();
    await user.click(screen.getByRole("combobox", { name: "New owner" }));
    expect((await screen.findAllByRole("option")).map((o) => o.textContent)).toEqual([
      "Ann Admin (ann@example.com)",
      "Mo Member (mo@example.com)",
      "sam@example.com",
    ]);
    await user.click(screen.getByRole("option", { name: "Mo Member (mo@example.com)" }));
    expect(start).toBeEnabled();
    await user.click(start);
    const dialog = await screen.findByRole("alertdialog", { name: "Make Mo Member the owner?" });
    expect(dialog).toHaveAccessibleDescription(
      "Mo Member will become the owner of Grace and you'll become an admin. Only the new owner can transfer ownership back.",
    );
    await user.click(within(dialog).getByRole("button", { name: "Transfer ownership" }));
    expect(await screen.findByText(TRANSFERRED)).toBeInTheDocument();
    expect(TRANSFERRED).toBe("Ownership transferred. You are now an admin.");
    expect(sent(api, "POST", "/church/transfer-ownership").map((r) => r.body)).toEqual([{ user_id: PEOPLE.mo }]);
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.churchProfile(church().id) });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.me() });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.members(church().id) });
  });

  it("turns to the admin form inside the church layout once the transfer is done, focus on the heading", async () => {
    window.localStorage.setItem(ACTIVE_CHURCH_KEY, church().id);
    let role: Church["role"] = "owner";
    installFakeApi({
      "GET /church": () => church({ role }),
      "GET /members": () => memberList(role),
      "POST /church/transfer-ownership": () => {
        role = "admin";
        return memberList("admin");
      },
    });
    const { user } = renderWithProviders(
      <>
        <ChurchLayout>
          <SettingsLayout>
            <DangerZoneRoute />
          </SettingsLayout>
        </ChurchLayout>
        <Toaster />
      </>,
      { me: me(), path: "/settings/danger" },
    );
    await user.click(await screen.findByRole("combobox", { name: "New owner" }));
    await user.click(await screen.findByRole("option", { name: "Ann Admin (ann@example.com)" }));
    await user.click(screen.getByRole("button", { name: "Transfer ownership…" }));
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Transfer ownership" }));
    expect(await screen.findByRole("note")).toHaveTextContent(OWNER_ONLY_NOTE);
    expect(screen.getByText("You're an admin of Grace.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete church…" })).toBeNull();
    expect(screen.getByRole("button", { name: "Leave church…" })).toBeEnabled();
    await waitFor(() =>
      expect(document.activeElement).toBe(screen.getByRole("heading", { level: 2, name: "Danger zone" })),
    );
  });

  it("toasts a role refusal of the transfer and refetches the role and the members, staying in the church", async () => {
    const lost = vi.fn();
    const unsubscribe = authEvents.onChurchAccessLost(lost);
    const { user, queryClient } = renderPage("owner", {
      "POST /church/transfer-ownership": fakeError(403, "forbidden", "Only the owner can do that."),
    });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    await user.click(await screen.findByRole("combobox", { name: "New owner" }));
    await user.click(await screen.findByRole("option", { name: "Ann Admin (ann@example.com)" }));
    await user.click(screen.getByRole("button", { name: "Transfer ownership…" }));
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Transfer ownership" }));
    expect(await screen.findByText("Only the owner can do that.")).toBeInTheDocument();
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.churchProfile(church().id) });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.members(church().id) });
    expect(lost).not.toHaveBeenCalled();
    unsubscribe();
  });

  it("toasts a transfer to someone who has left and refetches the members", async () => {
    const { user, queryClient } = renderPage("owner", {
      "POST /church/transfer-ownership": fakeError(404, "not_found", "Member not found."),
    });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    await user.click(await screen.findByRole("combobox", { name: "New owner" }));
    await user.click(await screen.findByRole("option", { name: "Mo Member (mo@example.com)" }));
    await user.click(screen.getByRole("button", { name: "Transfer ownership…" }));
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Transfer ownership" }));
    expect(await screen.findByText("Member not found.")).toBeInTheDocument();
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.members(church().id) });
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
  });

  it("sends one transfer for a double tap", async () => {
    let release: () => void = () => {};
    const { api, user } = renderPage("owner", {
      "POST /church/transfer-ownership": () => new Promise((resolve) => (release = () => resolve(memberList("admin")))),
    });
    await user.click(await screen.findByRole("combobox", { name: "New owner" }));
    await user.click(await screen.findByRole("option", { name: "Ann Admin (ann@example.com)" }));
    await user.click(screen.getByRole("button", { name: "Transfer ownership…" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Make Ann Admin the owner?" });
    await user.dblClick(within(dialog).getByRole("button", { name: "Transfer ownership" }));
    expect(sent(api, "POST", "/church/transfer-ownership")).toHaveLength(1);
    expect(await within(dialog).findByRole("button", { name: "Transferring…" })).toHaveAttribute("aria-disabled", "true");
    release();
    expect(await screen.findByText(TRANSFERRED)).toBeInTheDocument();
    expect(sent(api, "POST", "/church/transfer-ownership")).toHaveLength(1);
  });

  it("un-chooses a new owner who has left meanwhile, and turns Transfer off again", async () => {
    const { api, user, queryClient } = renderPage("owner");
    await user.click(await screen.findByRole("combobox", { name: "New owner" }));
    await user.click(await screen.findByRole("option", { name: "Mo Member (mo@example.com)" }));
    const start = screen.getByRole("button", { name: "Transfer ownership…" });
    expect(start).toBeEnabled();
    api.set("GET /members", { items: memberList("owner").items.filter((m) => m.user_id !== PEOPLE.mo) });
    await act(async () => {
      await queryClient.invalidateQueries({ queryKey: keys.members(church().id) });
    });
    await waitFor(() => expect(start).toBeDisabled());
    expect(screen.getByRole("combobox", { name: "New owner" })).toHaveTextContent("Choose a person");
  });

  it("toasts a role refusal of the delete and refetches the role and the members, staying in the church", async () => {
    const lost = vi.fn();
    const unsubscribe = authEvents.onChurchAccessLost(lost);
    const { user, queryClient } = renderPage("owner", {
      "DELETE /church": fakeError(403, "forbidden", "Only the owner can do that."),
    });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    await user.click(await screen.findByRole("button", { name: "Delete church…" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Delete Grace?" });
    await user.type(within(dialog).getByRole("textbox", { name: "Type Grace to confirm" }), "Grace");
    await user.click(within(dialog).getByRole("button", { name: "Delete church" }));
    expect(await screen.findByText("Only the owner can do that.")).toBeInTheDocument();
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.churchProfile(church().id) });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.members(church().id) });
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(lost).not.toHaveBeenCalled();
    expect(testRouter.replace).not.toHaveBeenCalled();
    unsubscribe();
  });

  it("deletes only after the exact name is typed, then says so and moves on with no access toast", async () => {
    const error = vi.spyOn(toast, "error");
    const { api, user } = renderShell("owner");
    await user.click(await screen.findByRole("button", { name: "Delete church…" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Delete Grace?" });
    expect(dialog).toHaveAccessibleDescription(deleteBody("Grace", 4));
    expect(deleteBody("Grace", 4)).toBe(
      "This removes Grace for all 4 people in it. They'll lose access to its services, hymns, contacts and settings. " +
        "Your unsaved draft for Grace on this device will be discarded. This can't be undone.",
    );
    const box = within(dialog).getByRole("textbox", { name: "Type Grace to confirm" });
    expect(box).toHaveAttribute("autocomplete", "off");
    expect(box).toHaveAttribute("autocapitalize", "off");
    const confirm = within(dialog).getByRole("button", { name: "Delete church" });
    expect(confirm).toBeDisabled();
    for (const wrong of ["grace", "GRACE", "Grac", "Grace."]) {
      await user.clear(box);
      await user.type(box, wrong);
      expect(confirm).toBeDisabled();
    }
    await user.click(confirm);
    expect(sent(api, "DELETE", "/church")).toEqual([]);
    await user.clear(box);
    await user.type(box, " Grace ");
    expect(confirm).toBeEnabled();
    await user.click(confirm);
    expect(await screen.findByText(CHURCH_DELETED)).toBeInTheDocument();
    expect(CHURCH_DELETED).toBe("Church deleted.");
    expect(await screen.findByRole("heading", { level: 3, name: "Leave Hope" })).toBeInTheDocument();
    expect(sent(api, "DELETE", "/church").map((r) => r.body)).toEqual([{ confirm_name: " Grace " }]);
    expect(testRouter.replace).toHaveBeenCalledWith("/");
    expect(window.localStorage.getItem(GRACE_DRAFT)).toBeNull();
    expect(screen.queryByText(/no longer have access/)).toBeNull();
    expect(error).not.toHaveBeenCalled();
    error.mockRestore();
  });

  it("says when the server finds the name does not match, under the box only, focuses it and refetches the name", async () => {
    const error = vi.spyOn(toast, "error");
    const { user, queryClient } = renderPage("owner", {
      "DELETE /church": fakeError(422, "invalid_request", "Church name did not match.", {
        fields: { confirm_name: "Church name did not match." },
      }),
    });
    await user.click(await screen.findByRole("button", { name: "Delete church…" }));
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const dialog = await screen.findByRole("alertdialog", { name: "Delete Grace?" });
    const box = within(dialog).getByRole("textbox", { name: "Type Grace to confirm" });
    await user.type(box, "Grace");
    await user.click(within(dialog).getByRole("button", { name: "Delete church" }));
    expect(await within(dialog).findByText("Church name did not match.")).toBeInTheDocument();
    expect(box).toHaveFocus();
    expect(box).toHaveAttribute("aria-invalid", "true");
    expect(box).toHaveAccessibleDescription("Church name did not match.");
    expect(testRouter.replace).not.toHaveBeenCalled();
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.churchProfile(church().id) });
    expect(screen.getAllByText("Church name did not match.")).toHaveLength(1);
    expect(error).not.toHaveBeenCalled();
    error.mockRestore();
  });

  it("sends one delete for a double tap, stays on Deleting… through the exit, and says so for the owner alone in the singular", async () => {
    let release: () => void = () => {};
    let releaseMe: () => void = () => {};
    const { api, user } = renderPage("owner", {
      "GET /members": alone(),
      "GET /me": () => new Promise((resolve) => (releaseMe = () => resolve(me({ churches: [] })))),
      "DELETE /church": () => new Promise((resolve) => (release = () => resolve({ deleted: true }))),
    });
    await user.click(await screen.findByRole("button", { name: "Delete church…" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Delete Grace?" });
    expect(dialog).toHaveAccessibleDescription(deleteBody("Grace", 1));
    expect(deleteBody("Grace", 1)).toBe(
      "This removes Grace. You're the only person in it, and you'll lose access to its services, hymns, contacts and settings. " +
        "Your unsaved draft for Grace on this device will be discarded. This can't be undone.",
    );
    await user.type(within(dialog).getByRole("textbox", { name: "Type Grace to confirm" }), "Grace");
    await user.dblClick(within(dialog).getByRole("button", { name: "Delete church" }));
    expect(sent(api, "DELETE", "/church")).toHaveLength(1);
    expect(await within(dialog).findByRole("button", { name: "Deleting…" })).toHaveAttribute("aria-disabled", "true");
    release();
    expect(await screen.findByText(CHURCH_DELETED)).toBeInTheDocument();
    await waitFor(() => expect(sent(api, "GET", "/me")).toHaveLength(1));
    expect(within(dialog).getByRole("button", { name: "Deleting…" })).toHaveAttribute("aria-disabled", "true");
    expect(testRouter.replace).not.toHaveBeenCalled();
    releaseMe();
    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/welcome"));
    expect(sent(api, "DELETE", "/church")).toHaveLength(1);
  });

  it("shows the error state with Retry when the members cannot be read", async () => {
    const { api, user } = renderPage("owner", { "GET /members": fakeError(500, "internal_error", "Something went wrong.") });
    expect(await screen.findByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete church…" })).toBeNull();
    api.set("GET /members", memberList("owner"));
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("button", { name: "Delete church…" })).toBeInTheDocument();
  });
});

describe("Settings → Danger zone: the copy and the phone screen (slice 6b-2b)", () => {
  it("lets a long church name wrap at 375 px in the cards, the dialogs and the typed-name label", async () => {
    const long = "TheVeryLongChurchNameThatNeverEndsWithoutASingleSpaceAnywhereInItsWholeLengthAtAll";
    const { user } = renderPage("owner", {}, long);
    expect((await screen.findByRole("heading", { level: 3, name: `Leave ${long}` }))).toHaveClass(WRAP);
    expect(screen.getByRole("heading", { level: 3, name: `Delete ${long}` })).toHaveClass(WRAP);
    expect(screen.getByText(deleteText(long))).toHaveClass(WRAP);
    expect(screen.getByText(OWNER_MUST_TRANSFER)).toHaveClass(WRAP);
    expect(screen.getByRole("combobox", { name: "New owner" })).toHaveClass("w-full", "min-w-0", "overflow-hidden");
    await user.click(screen.getByRole("button", { name: "Delete church…" }));
    const dialog = await screen.findByRole("alertdialog");
    expect(within(dialog).getByRole("heading", { name: `Delete ${long}?` })).toHaveClass(WRAP);
    expect(within(dialog).getByText(deleteBody(long, 4))).toHaveClass(WRAP);
    expect(within(dialog).getByText(`Type ${long} to confirm`)).toHaveClass(WRAP);
  });

  it("lets a long church name wrap in the Leave dialog too", async () => {
    const long = "AnotherVeryLongChurchNameWithoutSpacesSoItMustBreakAnywhereToFitOnAPhone";
    const { user } = renderPage("member", {}, long);
    await user.click(await screen.findByRole("button", { name: "Leave church…" }));
    const dialog = await screen.findByRole("alertdialog");
    expect(within(dialog).getByRole("heading", { name: `Leave ${long}?` })).toHaveClass(WRAP);
    expect(screen.getByText(leaveText(long))).toHaveClass(WRAP);
  });

  it("has no em dash in anything it says, for any role or dialog", async () => {
    const seen: string[] = [];
    const member = renderPage("member");
    await member.user.click(await screen.findByRole("button", { name: "Leave church…" }));
    await screen.findByRole("alertdialog");
    seen.push(allText());
    member.unmount();

    const owner = renderPage("owner");
    await owner.user.click(await screen.findByRole("combobox", { name: "New owner" }));
    await owner.user.click(await screen.findByRole("option", { name: "Ann Admin (ann@example.com)" }));
    await owner.user.click(screen.getByRole("button", { name: "Transfer ownership…" }));
    await screen.findByRole("alertdialog");
    seen.push(allText());
    owner.unmount();

    const deleting = renderPage("owner", { "GET /members": alone() });
    await deleting.user.click(await screen.findByRole("button", { name: "Delete church…" }));
    await screen.findByRole("alertdialog");
    seen.push(allText());

    const copy = [
      OWNER_ONLY_NOTE, OWNER_MUST_TRANSFER, TRANSFER_TEXT, INVITE_FIRST, TRANSFERRED, CHURCH_DELETED, EXIT_ME_FAILED,
      leaveText("Grace"), ownerAloneText("Grace"), deleteText("Grace"), deleteBody("Grace", 1), deleteBody("Grace", 3),
      leftChurch("Grace"),
    ];
    for (const text of [...seen, ...copy]) expect(text).not.toContain("\u2014");
    expect(seen.join(" ")).toContain("Leave Grace?");
    expect(seen.join(" ")).toContain("Make Ann Admin the owner?");
    expect(seen.join(" ")).toContain("Delete Grace?");
  });
});

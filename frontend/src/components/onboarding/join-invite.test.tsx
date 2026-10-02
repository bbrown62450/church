/**
 * `JoinInvite` against the fake API (S Flow A Join tab, Flow B steps 4-6, Loading
 * table rows "Preview" and "Accept / Create"; AC10 code side). The first four
 * tests are the AC16 ports of `streamlit_tests/test_onboarding.py`'s three
 * `pick_invite_code` tests (clarification 35): blank or whitespace-only sends
 * nothing, an edited field wins, an untouched prefilled code is used.
 */
import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import type { ComponentProps } from "react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from "vitest";

import { NETWORK_MESSAGE } from "@/lib/api/client";
import { makeQueryClient } from "@/lib/queries/client";
import { ACTIVE_CHURCH_KEY, SESSION_KEYS } from "@/lib/storage";
import { type FakeApi, fakeError, installFakeApi } from "@/test/fake-api";
import { CHURCH_IDS, church, inviteAccepted, invitePreview, me } from "@/test/fixtures";
import { supabaseAuth, testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import { JoinInvite } from "./join-invite";

const EMAIL = "pat@example.com";
const CODE = "GRACE-CODE-1";
const BLANK = "Enter an invite code, or open your invite link again.";
/** Midday UTC, so the date reads the same in every runner time zone. */
const EXPIRES_AT = "2026-10-05T12:00:00Z";

const MEMBER_PREVIEW = invitePreview({
  church_name: "Grace",
  role: "member",
  expires_at: EXPIRES_AT,
  email_bound: false,
  already_member: false,
});
const JOINED = inviteAccepted({
  church: church({ role: "member" }),
  already_member: false,
  message: "Joined Grace.",
});

const REJECTIONS = [
  ["unknown", "Invalid invite code."],
  ["revoked", "This invite has been revoked."],
  ["expired", "This invite has expired."],
  ["used", "This invite has already been used."],
  ["church_unavailable", "This church is no longer available."],
] as const;

function rejected(reason: string, message: string) {
  return fakeError(400, "invite_rejected", message, { details: { reason } });
}

type Props = ComponentProps<typeof JoinInvite>;

/** `/join`'s use unless overridden: the captured code, previewed on mount, no field. */
function renderJoin(props: Partial<Props> = {}) {
  return renderWithProviders(
    <JoinInvite email={EMAIL} initialCode={CODE} autoPreview showEntry={false} {...props} />,
  );
}

function sent(api: FakeApi, path: string): unknown[] {
  return api.requests.filter((r) => r.method === "POST" && r.path === path).map((r) => r.body);
}

/** The last `router.replace` went to `/login?next=/join&select_account=1` (parsed: 1a encodes `next`). */
function expectAccountChooserLogin(): void {
  const target = testRouter.replace.mock.calls.at(-1)?.[0];
  expect(typeof target).toBe("string");
  const url = new URL(target as string, "http://localhost");
  expect(url.pathname).toBe("/login");
  expect(url.searchParams.get("next")).toBe("/join");
  expect(url.searchParams.get("select_account")).toBe("1");
}

describe("JoinInvite", () => {
  let toastSuccess: MockInstance<typeof toast.success>;
  let toastError: MockInstance<typeof toast.error>;

  beforeEach(() => {
    toastSuccess = vi.spyOn(toast, "success").mockImplementation(() => 0);
    toastError = vi.spyOn(toast, "error").mockImplementation(() => 0);
  });

  afterEach(() => {
    toastSuccess.mockRestore();
    toastError.mockRestore();
  });

  it("a blank field shows the client message, focuses the field and sends nothing", async () => {
    const api = installFakeApi({});
    const { user } = renderJoin({ initialCode: undefined, autoPreview: false, showEntry: true });

    await user.click(screen.getByRole("button", { name: "Continue" }));

    expect(screen.getByText(BLANK)).toBeInTheDocument();
    const field = screen.getByLabelText("Invite link or code");
    expect(field).toHaveAttribute("aria-invalid", "true");
    expect(field).toHaveFocus();
    expect(api.requests).toHaveLength(0);
  });

  it("whitespace-only pending code and field send nothing (port: blank when neither)", async () => {
    const api = installFakeApi({});
    const { user } = renderJoin({ initialCode: "  ", autoPreview: true, showEntry: true });

    expect(screen.queryByRole("status", { name: "Loading invite" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Continue" }));

    expect(screen.getByText(BLANK)).toBeInTheDocument();
    expect(api.requests).toHaveLength(0);
  });

  it("an edited field wins over the prefilled pending code (port: typed wins over pending)", async () => {
    const api = installFakeApi({ "POST /invites/preview": MEMBER_PREVIEW });
    const { user } = renderJoin({ initialCode: "PENDING", autoPreview: false, showEntry: true });

    const field = screen.getByLabelText("Invite link or code");
    expect(field).toHaveValue("PENDING");
    await user.clear(field);
    await user.type(field, "TYPED");
    await user.click(screen.getByRole("button", { name: "Continue" }));

    expect(await screen.findByRole("heading", { name: "Grace" })).toBeInTheDocument();
    expect(sent(api, "/invites/preview")).toEqual([{ code: "TYPED" }]);
  });

  it("an untouched prefilled code is previewed once, even in StrictMode (port: falls back to pending)", async () => {
    const api = installFakeApi({ "POST /invites/preview": MEMBER_PREVIEW });
    // StrictMode at the root: React double-invokes effects only there, not for a
    // <StrictMode> nested inside renderWithProviders' wrapper.
    render(
      <QueryClientProvider client={makeQueryClient({ queries: { retry: false } })}>
        <JoinInvite email={EMAIL} initialCode="PENDING" autoPreview showEntry />
      </QueryClientProvider>,
      { reactStrictMode: true },
    );

    expect(await screen.findByRole("heading", { name: "Grace" })).toBeInTheDocument();
    expect(sent(api, "/invites/preview")).toEqual([{ code: "PENDING" }]);
  });

  it("a pasted invite link sends only its code", async () => {
    const api = installFakeApi({ "POST /invites/preview": MEMBER_PREVIEW });
    const { user } = renderJoin({ initialCode: undefined, autoPreview: false, showEntry: true });

    await user.type(
      screen.getByLabelText("Invite link or code"),
      "https://worship-service-builder.vercel.app/join?code=ABC123",
    );
    await user.click(screen.getByRole("button", { name: "Continue" }));

    expect(await screen.findByRole("heading", { name: "Grace" })).toBeInTheDocument();
    expect(sent(api, "/invites/preview")).toEqual([{ code: "ABC123" }]);
  });

  it("shows a skeleton card while the preview loads (S Loading table)", async () => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    installFakeApi({
      "POST /invites/preview": async () => {
        await gate;
        return MEMBER_PREVIEW;
      },
    });
    renderJoin();

    expect(screen.getByRole("status", { name: "Loading invite" })).toBeInTheDocument();
    release();
    expect(await screen.findByRole("heading", { name: "Grace" })).toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "Loading invite" })).not.toBeInTheDocument();
  });

  it("member preview: role line and expiry, no email line, Join and Not now, footer", async () => {
    installFakeApi({ "POST /invites/preview": MEMBER_PREVIEW });
    renderJoin();

    expect(await screen.findByRole("heading", { name: "Grace" })).toBeInTheDocument();
    expect(screen.getByText("You're invited to join as a member.")).toBeInTheDocument();
    expect(screen.getByText("Invite expires October 5, 2026.")).toBeInTheDocument();
    expect(screen.queryByText(/This invite is for/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Join Grace" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Not now" })).toBeEnabled();
    expect(screen.getByText(`Signed in as ${EMAIL} ·`)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Use a different account" })).toBeInTheDocument();
  });

  it("admin, email-bound preview: admin role line and the email line", async () => {
    installFakeApi({
      "POST /invites/preview": invitePreview({ ...MEMBER_PREVIEW, role: "admin", email_bound: true }),
    });
    renderJoin();

    expect(await screen.findByText("You're invited to join as an admin.")).toBeInTheDocument();
    expect(screen.getByText(`This invite is for ${EMAIL}.`)).toBeInTheDocument();
    expect(screen.getByText("Invite expires October 5, 2026.")).toBeInTheDocument();
  });

  it("already a member: one line, and Open Grace accepts, selects the church and toasts the server message", async () => {
    const api = installFakeApi({
      "POST /invites/preview": invitePreview({ ...MEMBER_PREVIEW, role: "admin", already_member: true }),
      "POST /invites/accept": inviteAccepted({
        church: church(),
        already_member: true,
        message: "You're already a member of Grace.",
      }),
      "GET /me": me(),
    });
    const { user } = renderJoin();

    expect(await screen.findByText("You're already a member of Grace.")).toBeInTheDocument();
    expect(screen.queryByText(/You're invited to join/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Invite expires/)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Open Grace" }));

    await waitFor(() => expect(toastSuccess).toHaveBeenCalledWith("You're already a member of Grace."));
    expect(sent(api, "/invites/accept")).toEqual([{ code: CODE }]);
    expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBe(CHURCH_IDS.grace);
    expect(testRouter.replace).toHaveBeenCalledWith("/");
  });

  it("Join Grace: pending while accepting, then clears the code, selects the church and toasts", async () => {
    window.sessionStorage.setItem(SESSION_KEYS.pendingInviteCode, CODE);
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const api = installFakeApi({
      "POST /invites/preview": MEMBER_PREVIEW,
      "POST /invites/accept": async () => {
        await gate;
        return JOINED;
      },
      "GET /me": me(),
    });
    const { user } = renderJoin();

    await user.click(await screen.findByRole("button", { name: "Join Grace" }));
    expect(screen.getByRole("button", { name: "Joining…" })).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByRole("button", { name: "Not now" })).toBeDisabled();
    release();

    await waitFor(() => expect(toastSuccess).toHaveBeenCalledWith("Joined Grace."));
    expect(sent(api, "/invites/accept")).toEqual([{ code: CODE }]);
    expect(api.requests.some((r) => r.method === "GET" && r.path === "/me")).toBe(true);
    expect(window.sessionStorage.getItem(SESSION_KEYS.pendingInviteCode)).toBeNull();
    expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBe(CHURCH_IDS.grace);
    expect(testRouter.replace).toHaveBeenCalledWith("/");
  });

  it.each(REJECTIONS)("preview rejected (%s): message, ask for a new link, code cleared, Go to home", async (reason, message) => {
    window.sessionStorage.setItem(SESSION_KEYS.pendingInviteCode, CODE);
    installFakeApi({ "POST /invites/preview": rejected(reason, message) });
    const { user } = renderJoin();

    const card = await screen.findByRole("alert");
    expect(within(card).getByRole("heading", { name: message })).toBeInTheDocument();
    expect(within(card).getByText("Ask for a new invite link.")).toBeInTheDocument();
    expect(window.sessionStorage.getItem(SESSION_KEYS.pendingInviteCode)).toBeNull();
    await user.click(within(card).getByRole("button", { name: "Go to home" }));
    expect(testRouter.replace).toHaveBeenCalledWith("/");
  });

  it("an accept that loses the race (400 used) shows the rejection card and clears the code", async () => {
    window.sessionStorage.setItem(SESSION_KEYS.pendingInviteCode, CODE);
    installFakeApi({
      "POST /invites/preview": MEMBER_PREVIEW,
      "POST /invites/accept": rejected("used", "This invite has already been used."),
    });
    const { user } = renderJoin();

    await user.click(await screen.findByRole("button", { name: "Join Grace" }));

    const card = await screen.findByRole("alert");
    expect(within(card).getByRole("heading", { name: "This invite has already been used." })).toBeInTheDocument();
    expect(within(card).getByText("Ask for a new invite link.")).toBeInTheDocument();
    expect(window.sessionStorage.getItem(SESSION_KEYS.pendingInviteCode)).toBeNull();
    expect(toastSuccess).not.toHaveBeenCalled();
    expect(toastError).not.toHaveBeenCalled();
    expect(testRouter.replace).not.toHaveBeenCalled();
  });

  it("email_mismatch keeps the code and switches Google accounts (local sign-out, account chooser)", async () => {
    window.sessionStorage.setItem(SESSION_KEYS.pendingInviteCode, CODE);
    installFakeApi({
      "POST /invites/preview": rejected("email_mismatch", "This invite was issued for a different email address."),
    });
    const { user } = renderJoin();

    const card = await screen.findByRole("alert");
    expect(
      within(card).getByRole("heading", { name: "This invite was issued for a different email address." }),
    ).toBeInTheDocument();
    expect(within(card).getByText(`You're signed in as ${EMAIL}.`)).toBeInTheDocument();
    expect(within(card).queryByText("Ask for a new invite link.")).not.toBeInTheDocument();
    expect(window.sessionStorage.getItem(SESSION_KEYS.pendingInviteCode)).toBe(CODE);

    await user.click(within(card).getByRole("button", { name: "Use a different Google account" }));

    await waitFor(() => expect(supabaseAuth.signOut).toHaveBeenCalledWith({ scope: "local" }));
    await waitFor(() => expectAccountChooserLogin());
    expect(window.sessionStorage.getItem(SESSION_KEYS.pendingInviteCode)).toBe(CODE);
  });

  it("a preview network error shows an inline Retry, keeps the code, and Retry sends it again", async () => {
    window.sessionStorage.setItem(SESSION_KEYS.pendingInviteCode, CODE);
    const api = installFakeApi({
      "POST /invites/preview": () => {
        throw new TypeError("Failed to fetch");
      },
    });
    const { user } = renderJoin();

    expect(await screen.findByText("Can't reach the server.")).toBeInTheDocument();
    expect(window.sessionStorage.getItem(SESSION_KEYS.pendingInviteCode)).toBe(CODE);
    expect(toastError).not.toHaveBeenCalled();

    api.set("POST /invites/preview", MEMBER_PREVIEW);
    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByRole("heading", { name: "Grace" })).toBeInTheDocument();
    expect(sent(api, "/invites/preview")).toEqual([{ code: CODE }, { code: CODE }]);
  });

  it("an accept network error or 5xx toasts and stays on the preview", async () => {
    window.sessionStorage.setItem(SESSION_KEYS.pendingInviteCode, CODE);
    const api = installFakeApi({
      "POST /invites/preview": MEMBER_PREVIEW,
      "POST /invites/accept": () => {
        throw new TypeError("Failed to fetch");
      },
    });
    const { user } = renderJoin();

    await user.click(await screen.findByRole("button", { name: "Join Grace" }));
    await waitFor(() => expect(toastError).toHaveBeenCalledWith(NETWORK_MESSAGE));
    expect(screen.getByRole("button", { name: "Join Grace" })).toBeEnabled();

    api.set("POST /invites/accept", fakeError(500, "internal_error", "Something went wrong."));
    await user.click(screen.getByRole("button", { name: "Join Grace" }));
    await waitFor(() => expect(toastError).toHaveBeenCalledWith("Something went wrong. (Ref: 4f9a2c1e)"));

    expect(screen.getByRole("button", { name: "Join Grace" })).toBeEnabled();
    expect(window.sessionStorage.getItem(SESSION_KEYS.pendingInviteCode)).toBe(CODE);
    expect(toastSuccess).not.toHaveBeenCalled();
    expect(testRouter.replace).not.toHaveBeenCalled();
  });

  it("Not now clears the pending code and goes home without accepting", async () => {
    window.sessionStorage.setItem(SESSION_KEYS.pendingInviteCode, CODE);
    const api = installFakeApi({ "POST /invites/preview": MEMBER_PREVIEW });
    const { user } = renderJoin();

    await user.click(await screen.findByRole("button", { name: "Not now" }));

    expect(window.sessionStorage.getItem(SESSION_KEYS.pendingInviteCode)).toBeNull();
    expect(testRouter.replace).toHaveBeenCalledWith("/");
    expect(sent(api, "/invites/accept")).toEqual([]);
  });

  it("the footer's Use a different account signs out locally and keeps the code for the next sign-in", async () => {
    installFakeApi({ "POST /invites/preview": MEMBER_PREVIEW });
    const { user } = renderJoin();

    await user.click(await screen.findByRole("button", { name: "Use a different account" }));

    await waitFor(() => expect(supabaseAuth.signOut).toHaveBeenCalledWith({ scope: "local" }));
    await waitFor(() => expectAccountChooserLogin());
    expect(window.sessionStorage.getItem(SESSION_KEYS.pendingInviteCode)).toBe(CODE);
  });
});

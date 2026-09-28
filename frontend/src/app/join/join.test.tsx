import { AuthRetryableFetchError } from "@supabase/supabase-js";
import { QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from "vitest";

import { Toaster } from "@/components/ui/sonner";
import { readStoredChurchId, storeChurchId } from "@/lib/church";
import { makeQueryClient } from "@/lib/queries/client";
import { readSession, SESSION_KEYS, writeSession } from "@/lib/storage";
import { fakeError, installFakeApi } from "@/test/fake-api";
import { CHURCH_IDS, church, inviteAccepted, invitePreview, me } from "@/test/fixtures";
import { setTestPath, supabaseAuth, testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import JoinPage, { metadata } from "./page";

const CODE = "Xy7-invite-CODE";

// This file's own hygiene (setup-dom.ts keeps the one global afterEach): the capture
// calls jsdom's real `replaceState`, which changes `window.location` for later tests,
// and sonner replays still-active toasts to a newly mounted Toaster.
let replaceState: MockInstance<History["replaceState"]>;

beforeEach(() => {
  toast.dismiss();
  replaceState = vi.spyOn(window.history, "replaceState");
});

afterEach(() => {
  replaceState.mockRestore();
  window.history.replaceState(null, "", "/");
});

/** `/join` as the app renders it (the page's Suspense included), with a Toaster for toast text. */
function joinTree() {
  return (
    <>
      <JoinPage />
      <Toaster />
    </>
  );
}

/** Arrive at `path`: the address bar and the router both show it; the spy starts clean. */
function openJoin(path: string) {
  window.history.replaceState(null, "", path);
  replaceState.mockClear();
  return renderWithProviders(joinTree(), { path });
}

function signedOut(): void {
  supabaseAuth.getSession.mockResolvedValue({ data: { session: null }, error: null });
}

/**
 * The parsed href of a link-styled Button. Base UI gives `<Button render={<Link />}
 * nativeButton={false}>` the `button` role, so it is found by that role and checked to be an `<a>`.
 */
function hrefOf(name: string): URL {
  const link = screen.getByRole("button", { name });
  expect(link.tagName).toBe("A");
  return new URL(link.getAttribute("href") ?? "", "http://localhost");
}

describe("/join (slice 1b)", () => {
  it("signed out: stores the code, takes it out of the address bar and shows the sign-in card", async () => {
    signedOut();
    installFakeApi({});
    openJoin(`/join?code=${CODE}`);

    expect(await screen.findByText("You're invited")).toBeInTheDocument();
    expect(
      screen.getByText("Sign in with Google to see and accept your invite to Worship Service Builder."),
    ).toBeInTheDocument();
    const signIn = hrefOf("Sign in with Google");
    expect(signIn.pathname).toBe("/login");
    expect([...signIn.searchParams]).toEqual([["next", "/join"]]);

    expect(readSession(SESSION_KEYS.pendingInviteCode)).toBe(CODE);
    expect(replaceState).toHaveBeenCalledTimes(1);
    expect(replaceState).toHaveBeenCalledWith(null, "", "/join");
    expect(window.location.pathname + window.location.search).toBe("/join");

    expect(metadata).toEqual({
      title: "Join a church",
      robots: { index: false, follow: false },
      referrer: "no-referrer",
    });
  });

  it("clears the stored post-login path on mount", async () => {
    signedOut();
    installFakeApi({});
    writeSession(SESSION_KEYS.postLoginPath, JSON.stringify({ path: "/join", at: Date.now() }));
    openJoin(`/join?code=${CODE}`);

    expect(await screen.findByText("You're invited")).toBeInTheDocument();
    expect(readSession(SESSION_KEYS.postLoginPath)).toBeNull();
  });

  it("keeps the captured code when the router's URL loses ?code= after replaceState", async () => {
    signedOut();
    installFakeApi({});
    window.history.replaceState(null, "", `/join?code=${CODE}`);
    replaceState.mockClear();
    setTestPath(`/join?code=${CODE}`);
    // StrictMode at the root (as in Task 14): the capture effect runs twice, and the ref
    // keeps it to one replaceState without losing the first run's code.
    const queryClient = makeQueryClient({ queries: { retry: false } });
    const { rerender } = render(<QueryClientProvider client={queryClient}>{joinTree()}</QueryClientProvider>, {
      reactStrictMode: true,
    });
    expect(await screen.findByText("You're invited")).toBeInTheDocument();

    // What Next's router reports once the native replaceState has run.
    setTestPath("/join");
    rerender(<QueryClientProvider client={queryClient}>{joinTree()}</QueryClientProvider>);

    expect(screen.getByText("You're invited")).toBeInTheDocument();
    expect(screen.queryByText("This invite link is incomplete.")).not.toBeInTheDocument();
    expect(readSession(SESSION_KEYS.pendingInviteCode)).toBe(CODE);
    expect(replaceState).toHaveBeenCalledTimes(1);
  });

  it("signed in: previews the invite; Join accepts it, selects the church and toasts", async () => {
    const api = installFakeApi({
      "GET /me": me({ churches: [] }),
      "POST /invites/preview": invitePreview({ church_name: "Grace", role: "member" }),
      "POST /invites/accept": inviteAccepted({
        church: church({ role: "member" }),
        already_member: false,
        message: "Joined Grace.",
      }),
    });
    const { user } = openJoin(`/join?code=${CODE}`);

    const join = await screen.findByRole("button", { name: "Join Grace" });
    api.set("GET /me", me({ churches: [church({ role: "member" })] }));
    await user.click(join);

    expect(await screen.findByText("Joined Grace.")).toBeInTheDocument();
    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/"));
    expect(readStoredChurchId()).toBe(CHURCH_IDS.grace);
    expect(readSession(SESSION_KEYS.pendingInviteCode)).toBeNull();
    expect(
      api.requests.filter((r) => r.method === "POST").map((r) => [r.path, r.body]),
    ).toEqual([
      ["/invites/preview", { code: CODE }],
      ["/invites/accept", { code: CODE }],
    ]);
  });

  it("previews a code stored before sign-in when the URL has none", async () => {
    writeSession(SESSION_KEYS.pendingInviteCode, CODE);
    const api = installFakeApi({
      "GET /me": me({ churches: [] }),
      "POST /invites/preview": invitePreview({ church_name: "Grace" }),
    });
    openJoin("/join");

    expect(await screen.findByRole("button", { name: "Join Grace" })).toBeInTheDocument();
    expect(api.requests.filter((r) => r.path === "/invites/preview").map((r) => r.body)).toEqual([
      { code: CODE },
    ]);
    expect(replaceState).not.toHaveBeenCalled();
  });

  it("shows the incomplete-link card when there is no code in the URL or in storage", async () => {
    const api = installFakeApi({});
    const { user } = openJoin("/join");

    expect(await screen.findByText("This invite link is incomplete.")).toBeInTheDocument();
    expect(
      screen.getByText("Open the link from your invite again, or ask for a new one."),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Go to home" }));
    expect(testRouter.replace).toHaveBeenCalledWith("/");
    expect(api.requests).toEqual([]);
  });

  it("a 401 from the preview signs out locally, keeps the code and returns to /join after sign-in", async () => {
    installFakeApi({
      "GET /me": me({ churches: [] }),
      "POST /invites/preview": fakeError(401, "unauthenticated", "Please sign in."),
    });
    openJoin(`/join?code=${CODE}`);

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/login?next=%2Fjoin"));
    expect(testRouter.replace).toHaveBeenCalledTimes(1);
    expect(supabaseAuth.signOut).toHaveBeenCalledTimes(1);
    expect(supabaseAuth.signOut).toHaveBeenCalledWith({ scope: "local" });
    expect(readSession(SESSION_KEYS.pendingInviteCode)).toBe(CODE);
  });

  it("a session check that cannot reach Supabase shows ErrorState, not the sign-in card; Retry checks again", async () => {
    supabaseAuth.getSession.mockResolvedValueOnce({
      data: { session: null },
      error: new AuthRetryableFetchError("Failed to fetch", 0),
    });
    const api = installFakeApi({
      "GET /me": me({ churches: [] }),
      "POST /invites/preview": invitePreview({ church_name: "Grace" }),
    });
    const { user } = openJoin(`/join?code=${CODE}`);

    expect(await screen.findByText("Can't reach the server.")).toBeInTheDocument();
    expect(screen.queryByText("You're invited")).not.toBeInTheDocument();
    expect(api.requests).toEqual([]);

    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByRole("button", { name: "Join Grace" })).toBeInTheDocument();
    expect(readSession(SESSION_KEYS.pendingInviteCode)).toBe(CODE);
  });

  it("signed out: loads no /me, so nothing signs out and the invited card stays", async () => {
    signedOut();
    const api = installFakeApi({});
    openJoin(`/join?code=${CODE}`);

    expect(await screen.findByText("You're invited")).toBeInTheDocument();
    // Let any query that would start on mount run to its end.
    await act(() => new Promise((resolve) => setTimeout(resolve, 0)));

    expect(supabaseAuth.getSession).toHaveBeenCalledTimes(1);
    expect(api.requests).toEqual([]);
    expect(supabaseAuth.signOut).not.toHaveBeenCalled();
    expect(testRouter.replace).not.toHaveBeenCalled();
    expect(screen.getByText("You're invited")).toBeInTheDocument();
  });

  it("a /me 5xx shows ErrorState with Retry, and Retry goes on to the preview", async () => {
    const api = installFakeApi({
      "GET /me": fakeError(500, "internal_error", "Something went wrong."),
      "POST /invites/preview": invitePreview({ church_name: "Grace" }),
    });
    const { user } = openJoin(`/join?code=${CODE}`);

    expect(await screen.findByText("Something went wrong. (Ref: 4f9a2c1e)")).toBeInTheDocument();
    expect(api.requests.filter((r) => r.path === "/invites/preview")).toHaveLength(0);

    api.set("GET /me", me({ churches: [] }));
    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByRole("button", { name: "Join Grace" })).toBeInTheDocument();
    expect(api.requests.filter((r) => r.path === "/me")).toHaveLength(2);
  });

  it("a member of Grace who joins Hope ends with Hope selected", async () => {
    storeChurchId(CHURCH_IDS.grace);
    const hope = church({ id: CHURCH_IDS.hope, name: "Hope", role: "member" });
    const api = installFakeApi({
      "GET /me": me(),
      "POST /invites/preview": invitePreview({ church_name: "Hope" }),
      "POST /invites/accept": inviteAccepted({ church: hope, message: "Joined Hope." }),
    });
    const { user } = openJoin(`/join?code=${CODE}`);

    const join = await screen.findByRole("button", { name: "Join Hope" });
    api.set("GET /me", me({ churches: [church(), hope] }));
    await user.click(join);

    expect(await screen.findByText("Joined Hope.")).toBeInTheDocument();
    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/"));
    expect(readStoredChurchId()).toBe(CHURCH_IDS.hope);
  });

  it("the code travels only in POST bodies: never in a request path, query or header, nor the address bar", async () => {
    const api = installFakeApi({
      "GET /me": me({ churches: [] }),
      "POST /invites/preview": invitePreview({ church_name: "Grace" }),
      "POST /invites/accept": inviteAccepted(),
    });
    const { user } = openJoin(`/join?code=${CODE}`);

    const join = await screen.findByRole("button", { name: "Join Grace" });
    api.set("GET /me", me({ churches: [church({ role: "member" })] }));
    await user.click(join);
    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/"));

    expect(api.requests.map((r) => `${r.method} ${r.path}`)).toEqual([
      "GET /me",
      "POST /invites/preview",
      "POST /invites/accept",
      "GET /me",
    ]);
    for (const request of api.requests) {
      expect(decodeURIComponent(request.path)).not.toContain(CODE);
      expect(JSON.stringify({ ...request.headers })).not.toContain(CODE);
    }
    expect(api.requests.filter((r) => r.body !== undefined).map((r) => r.body)).toEqual([
      { code: CODE },
      { code: CODE },
    ]);
    expect(window.location.href).not.toContain(CODE);
  });
});

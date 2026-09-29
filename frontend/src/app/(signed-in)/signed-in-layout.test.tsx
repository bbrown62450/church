import { QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { draftKey } from "@/lib/draft/schema";
import { useMeContext } from "@/lib/me-context";
import { storePostLoginPath } from "@/lib/post-login";
import { makeQueryClient } from "@/lib/queries/client";
import { keys } from "@/lib/queries/keys";
import { fakeError, installFakeApi } from "@/test/fake-api";
import { CHURCH_IDS, me, USER_ID } from "@/test/fixtures";
import { setTestPath, supabaseAuth, TEST_ACCESS_TOKEN, testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import SignedInLayout from "./layout";

/** Stands in for a page under the layout: it reads MeContext. */
function WhoAmI() {
  const current = useMeContext();
  return <p>{current.user.email}</p>;
}

function renderLayout(path = "/") {
  return renderWithProviders(
    <SignedInLayout>
      <WhoAmI />
    </SignedInLayout>,
    { path },
  );
}

/** The raw post-login entry in sessionStorage (`lib/post-login.ts`). */
function storedPostLoginPath(): string | null {
  return window.sessionStorage.getItem("wsb:postLoginPath");
}

describe("(signed-in) layout", () => {
  it("shows the shell skeleton until /me loads, then gives the children MeContext", async () => {
    const api = installFakeApi({ "GET /me": me() });
    renderLayout();

    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    expect(screen.queryByText("pat@example.com")).not.toBeInTheDocument();

    expect(await screen.findByText("pat@example.com")).toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "Loading" })).not.toBeInTheDocument();
    expect(api.requests).toHaveLength(1);
    expect(api.requests[0]).toMatchObject({ method: "GET", path: "/me" });
    expect(api.requests[0].headers["Authorization"]).toBe(`Bearer ${TEST_ACCESS_TOKEN}`);
  });

  it("shows a full-page ErrorState on a 5xx from /me; Retry stays busy while it runs and refetches once", async () => {
    const api = installFakeApi({
      "GET /me": fakeError(500, "internal_error", "Something went wrong."),
    });
    const { user } = renderLayout();

    expect(await screen.findByText("Something went wrong. (Ref: 4f9a2c1e)")).toBeInTheDocument();
    expect(screen.queryByText("pat@example.com")).not.toBeInTheDocument();
    expect(api.requests).toHaveLength(1);

    let answer!: () => void;
    const answered = new Promise<void>((resolve) => {
      answer = resolve;
    });
    api.set("GET /me", async () => {
      await answered;
      return me();
    });
    await user.click(screen.getByRole("button", { name: "Retry" }));

    // The error stays on screen with a busy Retry; a second tap sends nothing.
    const retry = await screen.findByRole("button", { name: "Retry" });
    await waitFor(() => expect(retry).toBeDisabled());
    expect(retry).toHaveAttribute("aria-busy", "true");
    expect(screen.getByText("Something went wrong. (Ref: 4f9a2c1e)")).toBeInTheDocument();
    await user.click(retry);

    answer();
    expect(await screen.findByText("pat@example.com")).toBeInTheDocument();
    expect(api.requests.filter((r) => r.path === "/me")).toHaveLength(2);
    expect(supabaseAuth.signOut).not.toHaveBeenCalled();
  });

  it("signs out locally on a 401 from /me, keeping a pending invite and the current path", async () => {
    window.sessionStorage.setItem("wsb:pendingInviteCode", "code-123");
    const api = installFakeApi({
      "GET /me": fakeError(401, "unauthenticated", "Please sign in."),
    });
    renderLayout("/welcome");

    await waitFor(() =>
      expect(testRouter.replace).toHaveBeenCalledWith("/login?next=%2Fwelcome"),
    );
    expect(testRouter.replace).toHaveBeenCalledTimes(1);
    expect(supabaseAuth.signOut).toHaveBeenCalledTimes(1);
    expect(supabaseAuth.signOut).toHaveBeenCalledWith({ scope: "local" });
    expect(window.sessionStorage.getItem("wsb:pendingInviteCode")).toBe("code-123");
    expect(api.requests).toHaveLength(1);
    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
  });

  it("follows a stored /join once, before any child renders, even under StrictMode", async () => {
    storePostLoginPath("/join");
    installFakeApi({ "GET /me": me() });
    setTestPath("/");
    // StrictMode at the root: React double-invokes effects only there, not for a
    // <StrictMode> nested inside renderWithProviders' wrapper (see Task 14).
    const queryClient = makeQueryClient({ queries: { retry: false } });
    render(
      <QueryClientProvider client={queryClient}>
        <SignedInLayout>
          <WhoAmI />
        </SignedInLayout>
      </QueryClientProvider>,
      { reactStrictMode: true },
    );

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/join"));
    await waitFor(() => expect(queryClient.getQueryData(keys.me())).toBeDefined());
    expect(testRouter.replace).toHaveBeenCalledTimes(1);
    expect(storedPostLoginPath()).toBeNull();
    // /me has loaded, but the page being left never renders.
    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    expect(screen.queryByText("pat@example.com")).not.toBeInTheDocument();
  });

  it("clears a stored path that is the current one and renders the children", async () => {
    storePostLoginPath("/welcome");
    installFakeApi({ "GET /me": me() });
    renderLayout("/welcome");

    expect(await screen.findByText("pat@example.com")).toBeInTheDocument();
    expect(testRouter.replace).not.toHaveBeenCalled();
    expect(storedPostLoginPath()).toBeNull();
  });

  it("clears the stored path before following it, so coming back to / does not redirect again", async () => {
    storePostLoginPath("/welcome");
    installFakeApi({ "GET /me": me() });
    const { rerender } = renderLayout("/");

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/welcome"));
    expect(storedPostLoginPath()).toBeNull();
    expect(screen.queryByText("pat@example.com")).not.toBeInTheDocument();

    // The redirect arrives: the same layout instance now sees /welcome.
    setTestPath("/welcome");
    rerender(
      <SignedInLayout>
        <WhoAmI />
      </SignedInLayout>,
    );
    expect(await screen.findByText("pat@example.com")).toBeInTheDocument();

    // Back to /: nothing is stored any more, so nothing redirects.
    setTestPath("/");
    rerender(
      <SignedInLayout>
        <WhoAmI />
      </SignedInLayout>,
    );
    expect(screen.getByText("pat@example.com")).toBeInTheDocument();
    expect(testRouter.replace).toHaveBeenCalledTimes(1);
  });

  it("keeps the children and shows no Retry when a background /me refetch fails", async () => {
    const api = installFakeApi({ "GET /me": me() });
    const { queryClient } = renderLayout();
    expect(await screen.findByText("pat@example.com")).toBeInTheDocument();

    api.set("GET /me", fakeError(500, "internal_error", "Something went wrong."));
    await act(() => queryClient.refetchQueries({ queryKey: keys.me() }));

    expect(api.requests.filter((r) => r.path === "/me")).toHaveLength(2);
    expect(queryClient.getQueryState(keys.me())?.status).toBe("error");
    expect(screen.getByText("pat@example.com")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "Loading" })).not.toBeInTheDocument();
  });

  it("prunes the user's drafts for churches they left once /me loads (F §4.6 item 4)", async () => {
    const left = draftKey(USER_ID, CHURCH_IDS.hope); // Pat is a member of Grace only
    const kept = draftKey(USER_ID, CHURCH_IDS.grace);
    const draft = JSON.stringify({ version: 1, updated_at: new Date().toISOString() });
    window.localStorage.setItem(left, draft);
    window.localStorage.setItem(kept, draft);
    installFakeApi({ "GET /me": me() });
    renderLayout();

    expect(await screen.findByText("pat@example.com")).toBeInTheDocument();
    await waitFor(() => expect(window.localStorage.getItem(left)).toBeNull());
    expect(window.localStorage.getItem(kept)).toBe(draft);
  });
});

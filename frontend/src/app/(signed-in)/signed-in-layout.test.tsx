import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useMeContext } from "@/lib/me-context";
import { fakeError, installFakeApi } from "@/test/fake-api";
import { me } from "@/test/fixtures";
import { supabaseAuth, TEST_ACCESS_TOKEN, testRouter } from "@/test/mocks";
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

  it("shows a full-page ErrorState on a 5xx from /me, and Retry refetches it", async () => {
    const api = installFakeApi({
      "GET /me": fakeError(500, "internal_error", "Something went wrong."),
    });
    const { user } = renderLayout();

    expect(await screen.findByText("Something went wrong. (Ref: 4f9a2c1e)")).toBeInTheDocument();
    expect(screen.queryByText("pat@example.com")).not.toBeInTheDocument();
    expect(api.requests).toHaveLength(1);

    api.set("GET /me", me());
    await user.click(screen.getByRole("button", { name: "Retry" }));

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
});

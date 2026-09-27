import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { installFakeApi } from "@/test/fake-api";
import { me } from "@/test/fixtures";
import { supabaseAuth, testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import SignedInLayout from "../layout";
import WelcomePage from "./page";

describe("/welcome stub (slice 1a)", () => {
  it("shows the No church yet card under the header, and Log out signs out locally", async () => {
    const api = installFakeApi({ "GET /me": me({ churches: [] }) });
    const { user } = renderWithProviders(
      <SignedInLayout>
        <WelcomePage />
      </SignedInLayout>,
      { path: "/welcome" },
    );

    expect(await screen.findByText("No church yet")).toBeInTheDocument();
    expect(
      screen.getByText("Creating or joining a church is coming in the next update."),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Account menu" }));
    await user.click(await screen.findByRole("menuitem", { name: "Log out" }));

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/login"));
    expect(supabaseAuth.signOut).toHaveBeenCalledTimes(1);
    expect(supabaseAuth.signOut).toHaveBeenCalledWith({ scope: "local" });
    expect(api.requests.filter((r) => r.path === "/me")).toHaveLength(1);
    expect(screen.queryByText("No church yet")).not.toBeInTheDocument();
  });
});

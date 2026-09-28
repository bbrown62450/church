import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { installFakeApi } from "@/test/fake-api";
import { CHURCH_IDS, church, invitePreview, me } from "@/test/fixtures";
import { supabaseAuth, testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import SignedInLayout from "../layout";
import WelcomePage from "./page";

const PENDING_CODE_KEY = "wsb:pendingInviteCode";

function renderWelcome(path = "/welcome") {
  return renderWithProviders(
    <SignedInLayout>
      <WelcomePage />
    </SignedInLayout>,
    { path },
  );
}

describe("/welcome (S Flow A, Flow C)", () => {
  afterEach(() => {
    // Test 7 spies on Intl; put the real functions back for the next test.
    vi.restoreAllMocks();
  });

  it("zero churches: welcome copy, a header without the switcher, Join tab by default, and Log out clears the keys", async () => {
    const api = installFakeApi({ "GET /me": me({ churches: [] }) });
    const { user } = renderWelcome();

    expect(
      await screen.findByRole("heading", { level: 1, name: "Welcome to Worship Service Builder" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Signed in as pat@example.com. You don't belong to a church yet."),
    ).toBeInTheDocument();
    expect(screen.getByText("Worship Service Builder")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^(Active church|Choose a church)/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Back to/ })).not.toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Join a church" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Create a church" })).toHaveAttribute("aria-selected", "false");
    expect(screen.getByLabelText("Invite link or code")).toBeInTheDocument();

    // Stored after the page read them, so nothing previews: Log out must remove both.
    window.sessionStorage.setItem(PENDING_CODE_KEY, "abc123");
    window.localStorage.setItem("activeChurchId", CHURCH_IDS.grace);

    await user.click(screen.getByRole("button", { name: "Account menu" }));
    await user.click(await screen.findByRole("menuitem", { name: "Log out" }));

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/login"));
    expect(supabaseAuth.signOut).toHaveBeenCalledWith({ scope: "local" });
    expect(window.sessionStorage.getItem(PENDING_CODE_KEY)).toBeNull();
    expect(window.localStorage.getItem("activeChurchId")).toBeNull();
    expect(api.requests.filter((r) => r.path === "/me")).toHaveLength(1);
  });

  it("with churches: join-or-create copy and a link back to the stored church", async () => {
    window.localStorage.setItem("activeChurchId", CHURCH_IDS.hope);
    installFakeApi({
      "GET /me": me({
        churches: [church(), church({ id: CHURCH_IDS.hope, name: "Hope", role: "member" })],
      }),
    });
    renderWelcome();

    expect(
      await screen.findByRole("heading", { level: 1, name: "Join or create a church" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Signed in as pat@example.com.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "← Back to Hope" })).toHaveAttribute("href", "/");
    expect(screen.queryByRole("link", { name: "← Back to Grace" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^(Active church|Choose a church)/ })).not.toBeInTheDocument();
  });

  it("?tab=create opens on the Create tab", async () => {
    installFakeApi({ "GET /me": me({ churches: [] }) });
    renderWelcome("/welcome?tab=create");

    expect(await screen.findByRole("tab", { name: "Create a church" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(
      screen.getByText("Start a new church. You'll be its owner and can invite others."),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Invite link or code")).not.toBeInTheDocument();
  });

  it("an unknown ?tab= value opens on the Join tab", async () => {
    installFakeApi({ "GET /me": me({ churches: [] }) });
    renderWelcome("/welcome?tab=foo");

    expect(await screen.findByRole("tab", { name: "Join a church" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByLabelText("Invite link or code")).toBeInTheDocument();
    expect(testRouter.replace).not.toHaveBeenCalled();
  });

  it("changing the tab replaces the URL without scrolling", async () => {
    installFakeApi({ "GET /me": me({ churches: [] }) });
    const { user } = renderWelcome();

    await user.click(await screen.findByRole("tab", { name: "Create a church" }));

    expect(testRouter.replace).toHaveBeenCalledWith("/welcome?tab=create", { scroll: false });
    expect(screen.getByRole("tab", { name: "Create a church" })).toHaveAttribute("aria-selected", "true");
    expect(
      screen.getByText("Start a new church. You'll be its owner and can invite others."),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Join a church" }));

    expect(testRouter.replace).toHaveBeenLastCalledWith("/welcome?tab=join", { scroll: false });
    expect(screen.getByLabelText("Invite link or code")).toBeInTheDocument();
  });

  it("a pending invite code shows the info alert and previews it once", async () => {
    window.sessionStorage.setItem(PENDING_CODE_KEY, "abc123");
    const api = installFakeApi({
      "GET /me": me({ churches: [] }),
      "POST /invites/preview": invitePreview(),
    });
    renderWelcome();

    expect(
      await screen.findByText("You opened an invite link. Review and accept it below."),
    ).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Join Grace" })).toBeInTheDocument();

    const previews = api.requests.filter((r) => r.path === "/invites/preview");
    expect(previews).toHaveLength(1);
    expect(previews[0].method).toBe("POST");
    expect(previews[0].body).toEqual({ code: "abc123" });
    expect(api.requests.filter((r) => r.path === "/invites/accept")).toHaveLength(0);
  });

  it("the Create tab preselects the browser's time zone", async () => {
    const realOptions = new Intl.DateTimeFormat().resolvedOptions();
    vi.spyOn(Intl, "supportedValuesOf").mockReturnValue([
      "America/Chicago",
      "America/New_York",
      "Europe/London",
    ]);
    vi.spyOn(Intl.DateTimeFormat.prototype, "resolvedOptions").mockReturnValue({
      ...realOptions,
      timeZone: "America/Chicago",
    });
    installFakeApi({ "GET /me": me({ churches: [] }) });
    renderWelcome("/welcome?tab=create");

    expect(await screen.findByRole("combobox", { name: "Time zone" })).toHaveValue("America/Chicago");
  });
});

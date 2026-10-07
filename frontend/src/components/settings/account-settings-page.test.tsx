/**
 * Settings → Account (slice 5b spec, UX "/settings/account"; slice 5b-2): who
 * is signed in, Log out, and the Gmail card's five states. Rendered inside the
 * Settings layout, as the route is, with a Toaster. Leaving for Google is
 * `browser.assign`, spied (jsdom cannot navigate).
 */
import { screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import AccountSettingsRoute from "@/app/(signed-in)/(church)/settings/account/page";
import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
import { Toaster } from "@/components/ui/sonner";
import { browser, GMAIL_RETURN_KEY } from "@/lib/gmail";
import { fakeError, installFakeApi, type FakeHandler } from "@/test/fake-api";
import { church, gmailConnection, gmailDisconnected, me } from "@/test/fixtures";
import { supabaseAuth } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import { GMAIL_EVERY_CHURCH, GMAIL_INTRO, GMAIL_NOT_CONFIGURED, GMAIL_STATUS_ERROR, SIGNED_IN_WITH_GOOGLE } from "./account-settings-page";

const GOOGLE_URL = "https://accounts.google.com/o/oauth2/v2/auth?state=s1";
let assign: ReturnType<typeof vi.spyOn>;

function renderPage(routes: Record<string, FakeHandler> = {}) {
  const api = installFakeApi({ "GET /gmail-connection": gmailConnection(), ...routes });
  const view = renderWithProviders(
    <>
      <SettingsLayout>
        <AccountSettingsRoute />
      </SettingsLayout>
      <Toaster />
    </>,
    { me: me(), church: church({ role: "member" }), path: "/settings/account" },
  );
  return { ...view, api };
}

async function gmailCard() {
  return screen.findByRole("region", { name: "Gmail" });
}

beforeEach(() => {
  assign = vi.spyOn(browser, "assign").mockImplementation(() => {});
});

afterEach(() => {
  toast.dismiss();
});

describe("Settings → Account (slice 5b-2)", () => {
  it("shows who is signed in, and Log out signs out", async () => {
    const { user } = renderPage();
    const account = screen.getByRole("region", { name: "Account" });
    expect(within(account).getByText("Pat Pastor")).toBeInTheDocument();
    expect(within(account).getByText("pat@example.com")).toBeInTheDocument();
    expect(within(account).getByText(SIGNED_IN_WITH_GOOGLE)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Account" })).toHaveAttribute("aria-current", "page");
    await user.click(within(account).getByRole("button", { name: "Log out" }));
    await waitFor(() => expect(supabaseAuth.signOut).toHaveBeenCalledTimes(1));
  });

  it("shows the connected address, and Disconnect shows the Connect button with no toast", async () => {
    const { api, user } = renderPage({ "DELETE /gmail-connection": gmailDisconnected() });
    const card = await gmailCard();
    expect(await within(card).findByText("pat@example.com")).toBeInTheDocument();
    expect(card).toHaveTextContent("Connected as pat@example.com.");
    expect(within(card).getByText(GMAIL_EVERY_CHURCH)).toBeInTheDocument();
    await user.click(within(card).getByRole("button", { name: "Disconnect" }));
    expect(await within(card).findByRole("button", { name: "Connect Gmail" })).toBeInTheDocument();
    expect(within(card).getByText(GMAIL_INTRO)).toBeInTheDocument();
    expect(GMAIL_INTRO).toBe(
      "Connect the Gmail account you sign in with. The app gets permission only to send email for you; it can't read your mail.",
    ); // 5b-2a: true before emailing exists (5b-2b says what it is for)
    expect(api.requests.filter((r) => r.method === "DELETE").map((r) => r.path)).toEqual(["/gmail-connection"]);
    expect(api.requests.find((r) => r.path === "/gmail-connection")?.headers["x-church-id"]).toBeUndefined();
    expect(document.querySelectorAll("[data-sonner-toast]")).toHaveLength(0);
  });

  it("Connect Gmail leaves for Google in this tab, to come back to Account", async () => {
    const { api, user } = renderPage({
      "GET /gmail-connection": gmailDisconnected(),
      "POST /gmail-connection/auth-url": { auth_url: GOOGLE_URL },
    });
    const card = await gmailCard();
    await user.click(await within(card).findByRole("button", { name: "Connect Gmail" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith(GOOGLE_URL));
    expect(window.sessionStorage.getItem(GMAIL_RETURN_KEY)).toBe("/settings/account");
    expect(api.requests.filter((r) => r.method === "POST").map((r) => r.path)).toEqual(["/gmail-connection/auth-url"]);
  });

  it("refuses a consent URL that is not Google's", async () => {
    const { user } = renderPage({
      "GET /gmail-connection": gmailDisconnected(),
      "POST /gmail-connection/auth-url": { auth_url: "https://evil.example/consent" },
    });
    const card = await gmailCard();
    await user.click(await within(card).findByRole("button", { name: "Connect Gmail" }));
    expect(await screen.findByText("Something went wrong.")).toBeInTheDocument();
    expect(assign).not.toHaveBeenCalled();
    expect(window.sessionStorage.getItem(GMAIL_RETURN_KEY)).toBeNull();
  });

  it("says when Gmail is not set up here, with no button", async () => {
    renderPage({ "GET /gmail-connection": gmailConnection({ configured: false, connected: false, google_email: null }) });
    const card = await gmailCard();
    expect(await within(card).findByText(GMAIL_NOT_CONFIGURED)).toBeInTheDocument();
    expect(within(card).queryByRole("button")).toBeNull();
  });

  it("shows a failed check with Retry, and a failed disconnect is toasted", async () => {
    let fail = true;
    const { user } = renderPage({
      "GET /gmail-connection": () => (fail ? fakeError(500, "internal_error", "Something went wrong.") : gmailConnection()),
      "DELETE /gmail-connection": fakeError(500, "internal_error", "Something went wrong."),
    });
    const card = await gmailCard();
    expect(await within(card).findByText(GMAIL_STATUS_ERROR)).toBeInTheDocument();
    fail = false;
    await user.click(within(card).getByRole("button", { name: "Retry" }));
    await user.click(await within(card).findByRole("button", { name: "Disconnect" }));
    expect(await screen.findByText("Something went wrong. (Ref: 4f9a2c1e)")).toBeInTheDocument();
  });
});

/**
 * `/gmail/callback` (slice 5b spec, flow C; slice 5b-2): rendered under
 * StrictMode, as Next runs it in development, with a Toaster. The address bar
 * is set with `history.replaceState` before each render.
 */
import { screen, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import GmailCallbackPage from "@/app/(signed-in)/gmail/callback/page";
import { Toaster } from "@/components/ui/sonner";
import { browser, GMAIL_RETURN_KEY } from "@/lib/gmail";
import { keys } from "@/lib/queries/keys";
import { fakeError, installFakeApi, type FakeHandler } from "@/test/fake-api";
import { me } from "@/test/fixtures";
import { testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import { CANCELLED, CONNECTED, GOOGLE_REFUSED, NOT_FINISHED } from "./gmail-callback";

const CONNECTED_STATUS = { configured: true, connected: true, google_email: "owner@example.com" };
let n = 0;

function renderCallback(search: string, routes: Record<string, FakeHandler> = {}) {
  window.history.replaceState(null, "", `/gmail/callback${search}`);
  const api = installFakeApi(routes);
  const view = renderWithProviders(
    <StrictMode>
      <GmailCallbackPage />
      <Toaster />
    </StrictMode>,
    { me: me(), path: "/gmail/callback" },
  );
  return { ...view, api };
}

/** A unique state per test: connectGmailOnce remembers each state for the life of the module. */
function nextState(): string {
  n += 1;
  return `state-${n}`;
}

beforeEach(() => {
  window.sessionStorage.setItem(GMAIL_RETURN_KEY, "/builder/review");
});

afterEach(() => {
  toast.dismiss();
  window.history.replaceState(null, "", "/");
});

describe("/gmail/callback (slice 5b-2)", () => {
  it("connects once, never shows the didn't-finish card, cleans the address bar and goes back", async () => {
    let release: (value: unknown) => void = () => {};
    const held = new Promise((resolve) => {
      release = resolve;
    });
    const seen: string[] = [];
    const observer = new MutationObserver(() => seen.push(document.body.textContent ?? ""));
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    const state = nextState();
    const { api, queryClient } = renderCallback(`?code=4%2F0Ab&state=${state}&scope=email`, {
      "POST /gmail-connection": async () => {
        await held;
        return CONNECTED_STATUS;
      },
    });
    expect(screen.getByRole("status")).toHaveTextContent("Connecting your Gmail…");
    await waitFor(() => expect(api.requests).toHaveLength(1));
    expect(window.location.pathname + window.location.search).toBe("/gmail/callback");
    release(undefined);
    expect(await screen.findByText(CONNECTED)).toBeInTheDocument();
    expect(testRouter.replace).toHaveBeenCalledWith("/builder/review");
    observer.disconnect();
    expect(api.requests.map((r) => [r.method, r.path, r.body])).toEqual([
      ["POST", "/gmail-connection", { code: "4/0Ab", state }],
    ]);
    expect(queryClient.getQueryData(keys.gmailConnection())).toEqual(CONNECTED_STATUS);
    expect(window.sessionStorage.getItem(GMAIL_RETURN_KEY)).toBeNull();
    expect(seen.some((text) => text.includes(NOT_FINISHED))).toBe(false);
  });

  it("goes back with a note when the user cancelled at Google, without calling the API", async () => {
    const { api } = renderCallback(`?error=access_denied&state=${nextState()}`);
    expect(await screen.findByText(CANCELLED)).toBeInTheDocument();
    expect(testRouter.replace).toHaveBeenCalledWith("/builder/review");
    expect(api.requests).toEqual([]);
    expect(window.location.search).toBe("");
  });

  it("never shows Google's error value", async () => {
    renderCallback("?error=%3Cb%3Eserver_error%3C%2Fb%3E");
    expect(await screen.findByRole("alert")).toHaveTextContent(GOOGLE_REFUSED);
    expect(document.body.textContent).not.toContain("server_error");
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Go back" })).toBeInTheDocument();
  });

  it("says the connection didn't finish when the address bar has no answer", async () => {
    const { api, user } = renderCallback("");
    expect(await screen.findByRole("alert")).toHaveTextContent(NOT_FINISHED);
    await user.click(screen.getByRole("button", { name: "Go back" }));
    expect(testRouter.replace).toHaveBeenCalledWith("/builder/review");
    expect(api.requests).toEqual([]);
  });

  it("shows the server's message, and Try again leaves for Google again with the same way back", async () => {
    const assign = vi.spyOn(browser, "assign").mockImplementation(() => {});
    const { api, user } = renderCallback(`?code=c&state=${nextState()}`, {
      "POST /gmail-connection": fakeError(400, "gmail_state_invalid",
        "This Gmail connection request expired or was already used. Try connecting again."),
      "POST /gmail-connection/auth-url": { auth_url: "https://accounts.google.com/o/oauth2/v2/auth?state=new" },
    });
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This Gmail connection request expired or was already used. Try connecting again.",
    );
    await user.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("https://accounts.google.com/o/oauth2/v2/auth?state=new"));
    expect(window.sessionStorage.getItem(GMAIL_RETURN_KEY)).toBe("/builder/review");
    expect(api.requests.map((r) => `${r.method} ${r.path}`)).toEqual([
      "POST /gmail-connection",
      "POST /gmail-connection/auth-url",
    ]);
  });

  it("offers only Go back when Gmail is not set up here, with the server's words for a Google failure", async () => {
    renderCallback(`?code=c&state=${nextState()}`, {
      "POST /gmail-connection": fakeError(503, "gmail_not_configured", "Gmail sending isn't set up correctly on this deployment."),
    });
    expect(await screen.findByRole("alert")).toHaveTextContent("Gmail sending isn't set up correctly on this deployment.");
    expect(screen.queryByRole("button", { name: "Try again" })).toBeNull();
    expect(screen.getByRole("button", { name: "Go back" })).toBeInTheDocument();
  });
});

/**
 * The `(church)` layout inside the real `(signed-in)` layout, against the fake
 * API (S Flow D, Layouts steps 1-7, Testing "(church) layout"; AC12, AC13, the
 * 1a part of AC14; F §5.2 error-state test).
 *
 * `ChurchProbe` stands in for a church page: it shows `useChurch().name` and
 * keeps local state, so a remount is visible as its counter going back to 0.
 */
import { useState, type ReactElement, type ReactNode } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from "vitest";

import type { Church } from "@/lib/church";
import { useChurch } from "@/lib/church-context";
import { makeQueryClient, useApi } from "@/lib/queries/client";
import { keys } from "@/lib/queries/keys";
import { ACTIVE_CHURCH_KEY, SESSION_KEYS } from "@/lib/storage";
import { type FakeApi, type RecordedRequest, fakeError, installFakeApi } from "@/test/fake-api";
import { CHURCH_IDS, church, me } from "@/test/fixtures";
import { supabaseAuth, testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import SignedInLayout from "../layout";
import ChurchLayout from "./layout";
import HomePage from "./page";

const GRACE = church();
const HOPE = church({ id: CHURCH_IDS.hope, name: "Hope", role: "member" });

/** `require_church`'s 403 for a church the user no longer belongs to. */
const NO_ACCESS = fakeError(403, "forbidden", "You don't have access to this church.", {
  details: { reason: "no_church_access" },
});

function ChurchProbe() {
  const active = useChurch();
  const [clicks, setClicks] = useState(0);
  return (
    <div>
      <p>Showing {active.name}</p>
      <button type="button" onClick={() => setClicks((n) => n + 1)}>
        Clicked {clicks}
      </button>
    </div>
  );
}

function renderShell(
  page: ReactElement = <ChurchProbe />,
  options: Parameters<typeof renderWithProviders>[1] = {},
) {
  return renderWithProviders(
    <SignedInLayout>
      <ChurchLayout>{page}</ChurchLayout>
    </SignedInLayout>,
    options,
  );
}

/** `GET /church` as the API answers it: the church named by `X-Church-Id`, else 403. */
function churchById(...churches: Church[]) {
  return (req: RecordedRequest) =>
    churches.find((c) => c.id === req.headers["X-Church-Id"]) ?? NO_ACCESS;
}

/** The same answer, 20 ms later. */
function slowly(answer: (req: RecordedRequest) => unknown) {
  return async (req: RecordedRequest) => {
    await new Promise((resolve) => setTimeout(resolve, 20));
    return answer(req);
  };
}

/** A promise the test resolves by hand. */
function gate(): { wait: Promise<void>; open: () => void } {
  let open = () => {};
  const wait = new Promise<void>((resolve) => {
    open = resolve;
  });
  return { wait, open };
}

/** The `X-Church-Id` of every `GET /church`, in order. */
function churchRequests(api: FakeApi): string[] {
  return api.requests
    .filter((req) => req.method === "GET" && req.path === "/church")
    .map((req) => req.headers["X-Church-Id"]);
}

function meRequests(api: FakeApi): RecordedRequest[] {
  return api.requests.filter((req) => req.method === "GET" && req.path === "/me");
}

function header(): HTMLElement {
  return screen.getByRole("banner");
}

/** The header's church switcher: its one button besides the account menu. */
function switcherTrigger(): HTMLElement {
  const account = screen.getByRole("button", { name: "Account menu" });
  const trigger = within(header())
    .getAllByRole("button")
    .find((button) => button !== account);
  if (!trigger) throw new Error("The header has no church switcher.");
  return trigger;
}

describe("(church) layout", () => {
  let toastError: MockInstance<typeof toast.error>;

  beforeEach(() => {
    toastError = vi.spyOn(toast, "error").mockImplementation(() => 0);
  });

  afterEach(() => {
    toastError.mockRestore();
  });

  it("confirms the stored church when the user still belongs to it", async () => {
    window.localStorage.setItem(ACTIVE_CHURCH_KEY, HOPE.id);
    const api = installFakeApi({
      "GET /me": me({ churches: [GRACE, HOPE] }),
      "GET /church": churchById(GRACE, HOPE),
    });

    renderShell();

    expect(await screen.findByText("Showing Hope")).toBeInTheDocument();
    expect(header()).toHaveTextContent("Hope");
    expect(churchRequests(api)).toEqual([HOPE.id]);
    expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBe(HOPE.id);
  });

  it("falls back to the first church by name when the stored id is stale, and stores it", async () => {
    window.localStorage.setItem(ACTIVE_CHURCH_KEY, CHURCH_IDS.trinity);
    const api = installFakeApi({
      "GET /me": me({ churches: [GRACE, HOPE] }),
      "GET /church": churchById(GRACE, HOPE),
    });

    renderShell();

    expect(await screen.findByText("Showing Grace")).toBeInTheDocument();
    await waitFor(() => expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBe(GRACE.id));
    expect(churchRequests(api)).toEqual([GRACE.id]);
  });

  it("never asks for or shows a cached church other than the stored one", async () => {
    window.localStorage.setItem(ACTIVE_CHURCH_KEY, HOPE.id);
    const queryClient = makeQueryClient({ queries: { retry: false } });
    queryClient.setQueryData(keys.churchProfile(GRACE.id), GRACE);
    const hopeAnswer = gate();
    const api = installFakeApi({
      "GET /me": me({ churches: [GRACE, HOPE] }),
      "GET /church": async (req: RecordedRequest) => {
        await hopeAnswer.wait;
        return churchById(GRACE, HOPE)(req);
      },
    });

    renderShell(<ChurchProbe />, { queryClient });

    // While Hope is being confirmed, the header shows Hope (the candidate), never Grace.
    await waitFor(() => expect(churchRequests(api)).toEqual([HOPE.id]));
    expect(header()).toHaveTextContent("Hope");
    expect(header()).not.toHaveTextContent("Grace");
    expect(screen.queryByText("Showing Grace")).not.toBeInTheDocument();

    await act(async () => hopeAnswer.open());

    expect(await screen.findByText("Showing Hope")).toBeInTheDocument();
    expect(header()).not.toHaveTextContent("Grace");
    expect(churchRequests(api)).toEqual([HOPE.id]);
    expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBe(HOPE.id);
  });

  it("on 403 no_church_access says so, refetches /me and confirms the next church", async () => {
    const api = installFakeApi({
      "GET /me": me({ churches: [GRACE, HOPE] }),
      "GET /church": churchById(HOPE),
    });

    renderShell();

    expect(await screen.findByText("Showing Hope")).toBeInTheDocument();
    expect(toastError).toHaveBeenCalledTimes(1);
    expect(toastError).toHaveBeenCalledWith("You no longer have access to Grace.");
    await waitFor(() => expect(meRequests(api)).toHaveLength(2));
    expect(churchRequests(api)).toEqual([GRACE.id, HOPE.id]);
    await waitFor(() => expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBe(HOPE.id));
  });

  it("on refocus, a /me that no longer lists the shown church says so and confirms the next one", async () => {
    let meCalls = 0;
    const api = installFakeApi({
      "GET /me": () => {
        meCalls += 1;
        return meCalls === 1 ? me({ churches: [GRACE, HOPE] }) : me({ churches: [HOPE] });
      },
      "GET /church": churchById(GRACE, HOPE),
    });
    const { queryClient } = renderShell();
    expect(await screen.findByText("Showing Grace")).toBeInTheDocument();

    await act(async () => {
      await queryClient.invalidateQueries({ queryKey: keys.me() });
    });

    expect(await screen.findByText("Showing Hope")).toBeInTheDocument();
    expect(toastError).toHaveBeenCalledTimes(1);
    expect(toastError).toHaveBeenCalledWith("You no longer have access to Grace.");
    expect(churchRequests(api)).toEqual([GRACE.id, HOPE.id]);
    await waitFor(() => expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBe(HOPE.id));
  });

  it("goes to /welcome when the last church is lost", async () => {
    let meCalls = 0;
    const api = installFakeApi({
      "GET /me": () => {
        meCalls += 1;
        return meCalls === 1 ? me({ churches: [GRACE] }) : me({ churches: [] });
      },
      "GET /church": NO_ACCESS,
    });

    renderShell();

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/welcome"));
    expect(toastError).toHaveBeenCalledWith("You no longer have access to Grace.");
    await waitFor(() => expect(meRequests(api)).toHaveLength(2));
    expect(churchRequests(api)).toEqual([GRACE.id]);
  });

  it("sends a user with no church to /welcome without asking for a church", async () => {
    const api = installFakeApi({ "GET /me": me({ churches: [] }) });

    renderShell();

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/welcome"));
    expect(churchRequests(api)).toEqual([]);
  });

  it("switching remounts the page and removes the old church's queries", async () => {
    const api = installFakeApi({
      "GET /me": me({ churches: [GRACE, HOPE] }),
      "GET /church": churchById(GRACE, HOPE),
    });
    const { user, queryClient } = renderShell();
    expect(await screen.findByText("Showing Grace")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Clicked 0" }));
    expect(screen.getByRole("button", { name: "Clicked 1" })).toBeInTheDocument();

    await user.click(switcherTrigger());
    await user.click(await screen.findByRole("menuitemradio", { name: /Hope/ }));

    expect(await screen.findByText("Showing Hope")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Clicked 0" })).toBeInTheDocument();
    expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBe(HOPE.id);
    await waitFor(() =>
      expect(queryClient.getQueryCache().findAll({ queryKey: keys.church(GRACE.id) })).toHaveLength(0),
    );
    expect(queryClient.getQueryData(keys.churchProfile(HOPE.id))).toEqual(HOPE);
    expect(churchRequests(api)).toEqual([GRACE.id, HOPE.id]);
  });

  it("a role 403 shows the error state and does not fall back", async () => {
    const api = installFakeApi({
      "GET /me": me({ churches: [GRACE, HOPE] }),
      "GET /church": fakeError(403, "forbidden", "Only church admins can do this."),
    });

    renderShell();

    expect(await screen.findByText("Only church admins can do this.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(header()).toHaveTextContent("Grace");
    expect(toastError).not.toHaveBeenCalled();
    expect(meRequests(api)).toHaveLength(1);
    expect(churchRequests(api)).toEqual([GRACE.id]);
  });

  it("GET /church 500 shows the error state with its reference, and Retry refetches", async () => {
    const api = installFakeApi({
      "GET /me": me(),
      "GET /church": fakeError(500, "internal_error", "Something went wrong."),
    });
    const { user } = renderShell();

    expect(await screen.findByText("Something went wrong. (Ref: 4f9a2c1e)")).toBeInTheDocument();

    api.set("GET /church", GRACE);
    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByText("Showing Grace")).toBeInTheDocument();
    expect(churchRequests(api)).toEqual([GRACE.id, GRACE.id]);
  });

  it("Log out clears the cache, the stored church and the wsb: keys, and signs out locally", async () => {
    window.sessionStorage.setItem(SESSION_KEYS.pendingInviteCode, "invite-code-1");
    window.sessionStorage.setItem(SESSION_KEYS.postLoginPath, "/builder");
    installFakeApi({ "GET /me": me(), "GET /church": GRACE });
    const { user, queryClient } = renderShell();
    expect(await screen.findByText("Showing Grace")).toBeInTheDocument();
    await waitFor(() => expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBe(GRACE.id));

    await user.click(screen.getByRole("button", { name: "Account menu" }));
    await user.click(await screen.findByRole("menuitem", { name: "Log out" }));

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/login"));
    expect(supabaseAuth.signOut).toHaveBeenCalledWith({ scope: "local" });
    expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBeNull();
    expect(window.sessionStorage.getItem(SESSION_KEYS.pendingInviteCode)).toBeNull();
    expect(window.sessionStorage.getItem(SESSION_KEYS.postLoginPath)).toBeNull();
    expect(queryClient.getQueryData(keys.me())).toBeUndefined();
    expect(queryClient.getQueryData(keys.churchProfile(GRACE.id))).toBeUndefined();
  });

  it("signing out sends no request and stores no church, even with slow answers in flight", async () => {
    const api = installFakeApi({
      "GET /me": slowly(() => me({ churches: [GRACE, HOPE] })),
      "GET /church": slowly(churchById(GRACE, HOPE)),
    });
    const { user } = renderShell();
    expect(await screen.findByText("Showing Grace")).toBeInTheDocument();
    await waitFor(() => expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBe(GRACE.id));
    await user.click(screen.getByRole("button", { name: "Account menu" }));
    const logOut = await screen.findByRole("menuitem", { name: "Log out" });
    const sent = api.requests.length;

    await user.click(logOut);
    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/login"));
    // Longer than a slow answer: a refetch started by the sign-out would have landed by now.
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 60));
    });

    expect(api.requests.slice(sent)).toEqual([]);
    expect(supabaseAuth.signOut).toHaveBeenCalledTimes(1);
    expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBeNull();
  });

  it("a 401 from a church query signs out locally and keeps the pending invite", async () => {
    window.localStorage.setItem(ACTIVE_CHURCH_KEY, GRACE.id);
    window.sessionStorage.setItem(SESSION_KEYS.pendingInviteCode, "invite-code-1");
    installFakeApi({
      "GET /me": me(),
      "GET /church": fakeError(401, "unauthenticated", "Please sign in."),
    });

    renderShell();

    await waitFor(() =>
      expect(testRouter.replace).toHaveBeenCalledWith(expect.stringMatching(/^\/login/)),
    );
    expect(supabaseAuth.signOut).toHaveBeenCalledTimes(1);
    expect(supabaseAuth.signOut).toHaveBeenCalledWith({ scope: "local" });
    expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBeNull();
    expect(window.sessionStorage.getItem(SESSION_KEYS.pendingInviteCode)).toBe("invite-code-1");
  });

  it("the home page shows the confirmed church from useChurch()", async () => {
    installFakeApi({ "GET /me": me(), "GET /church": GRACE });

    renderShell(<HomePage />);

    expect(
      await screen.findByText(
        "Readings, hymns, and liturgy for Grace are coming soon. Until then, keep using the current app.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Church profile, members, and invites are coming later.")).toBeInTheDocument();
  });

  it("useApi().church refuses to run outside ChurchProvider", async () => {
    const api = installFakeApi({});
    const queryClient = makeQueryClient({ queries: { retry: false } });
    function Wrapper({ children }: { children: ReactNode }) {
      return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
    }
    const { result } = renderHook(() => useApi(), { wrapper: Wrapper });

    await expect(Promise.resolve().then(() => result.current.church("/church"))).rejects.toThrow();
    expect(api.requests).toEqual([]);
  });
});

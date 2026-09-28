import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from "vitest";

import { NETWORK_MESSAGE } from "@/lib/api/client";
import { readStoredChurchId } from "@/lib/church";
import { fakeError, installFakeApi, type FakeApi, type FakeResponse, type RecordedRequest } from "@/test/fake-api";
import { CHURCH_IDS, church, me } from "@/test/fixtures";
import { testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import { CreateChurchForm } from "./create-church-form";

const NEW_LIFE = church({ id: CHURCH_IDS.hope, name: "New Life", role: "owner" });
const ZONES = ["America/Chicago", "America/New_York", "Europe/London"];
const REAL_OPTIONS = new Intl.DateTimeFormat().resolvedOptions();
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const STILL_WORKING = "Still working — this can take up to a minute.";
const LIMIT_MESSAGE = "You've created 5 churches in the last 24 hours. Try again later.";

/** The browser lists three zones and reports `America/Chicago` (never the runner's own zone). */
function stubZones(): void {
  vi.spyOn(Intl, "supportedValuesOf").mockReturnValue(ZONES);
  vi.spyOn(Intl.DateTimeFormat.prototype, "resolvedOptions").mockReturnValue({
    ...REAL_OPTIONS,
    timeZone: "America/Chicago",
  });
}

/** A browser without `Intl.supportedValuesOf`: the time zone is a plain text input. */
function stubNoZoneList(): void {
  vi.stubGlobal("Intl", Object.assign(Object.create(Intl) as typeof Intl, { supportedValuesOf: undefined }));
}

function posts(api: FakeApi) {
  return api.requests.filter((req) => req.method === "POST" && req.path === "/churches");
}

function renderForm() {
  return renderWithProviders(<CreateChurchForm />);
}

describe("CreateChurchForm", () => {
  let toastSuccess: MockInstance<typeof toast.success>;
  let toastError: MockInstance<typeof toast.error>;

  beforeEach(() => {
    toastSuccess = vi.spyOn(toast, "success").mockImplementation(() => 0);
    toastError = vi.spyOn(toast, "error").mockImplementation(() => 0);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("creates the church with a UUID Idempotency-Key, refetches /me, selects it and goes home", async () => {
    stubZones();
    const api = installFakeApi({
      "POST /churches": { status: 201, body: NEW_LIFE },
      "GET /me": me({ churches: [church(), NEW_LIFE] }),
    });
    let requestsAtReplace: string[] = [];
    testRouter.replace.mockImplementation(() => {
      requestsAtReplace = api.requests.map((req) => `${req.method} ${req.path}`);
    });
    const { user } = renderForm();

    await user.type(screen.getByLabelText("Church name"), "  New Life ");
    await user.click(screen.getByRole("button", { name: "Create church" }));

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/"));
    expect(requestsAtReplace).toEqual(["POST /churches", "GET /me"]);
    const [post] = posts(api);
    expect(post.body).toEqual({ name: "New Life", timezone: "America/Chicago" });
    expect(post.headers["Idempotency-Key"]).toMatch(UUID);
    expect(post.headers["X-Church-Id"]).toBeUndefined();
    expect(readStoredChurchId()).toBe(CHURCH_IDS.hope);
    expect(toastSuccess).toHaveBeenCalledWith("Created New Life. You're the owner.");
    expect(toastError).not.toHaveBeenCalled();
  });

  it("checks a blank name on the client: inline message, focus, no request", async () => {
    stubZones();
    const api = installFakeApi({});
    const { user } = renderForm();

    await user.type(screen.getByLabelText("Church name"), "   ");
    await user.click(screen.getByRole("button", { name: "Create church" }));

    expect(screen.getByText("Church name is required.")).toBeInTheDocument();
    expect(screen.getByLabelText("Church name")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText("Church name")).toHaveFocus();
    expect(api.requests).toHaveLength(0);
  });

  it("checks an empty time zone on the client when the browser has no zone list", async () => {
    stubNoZoneList();
    const api = installFakeApi({});
    const { user } = renderForm();

    await user.type(screen.getByLabelText("Church name"), "New Life");
    await user.clear(screen.getByLabelText("Time zone"));
    await user.click(screen.getByRole("button", { name: "Create church" }));

    expect(screen.getByText("Timezone is required.")).toBeInTheDocument();
    expect(screen.getByLabelText("Time zone")).toHaveFocus();
    expect(screen.queryByText("Church name is required.")).not.toBeInTheDocument();
    expect(api.requests).toHaveLength(0);
  });

  it("shows a 422 'Unknown timezone.' under the field, then a fixed resubmit gets a new key", async () => {
    stubNoZoneList();
    const api = installFakeApi({
      "POST /churches": (req: RecordedRequest) =>
        (req.body as { timezone: string }).timezone === "Mars/Base"
          ? fakeError(422, "invalid_request", "Unknown timezone.", { fields: { timezone: "Unknown timezone." } })
          : { status: 201, body: NEW_LIFE },
      "GET /me": me({ churches: [NEW_LIFE] }),
    });
    const { user } = renderForm();
    const zone = screen.getByLabelText("Time zone");

    await user.type(screen.getByLabelText("Church name"), "New Life");
    await user.clear(zone);
    await user.type(zone, "Mars/Base");
    await user.click(screen.getByRole("button", { name: "Create church" }));

    expect(await screen.findByText("Unknown timezone.")).toBeInTheDocument();
    expect(zone).toHaveFocus();
    expect(toastError).not.toHaveBeenCalled();

    await user.clear(zone);
    await user.type(zone, "Europe/London");
    await user.click(screen.getByRole("button", { name: "Create church" }));

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/"));
    const [first, second] = posts(api);
    expect(second.body).toEqual({ name: "New Life", timezone: "Europe/London" });
    expect(second.headers["Idempotency-Key"]).toMatch(UUID);
    expect(second.headers["Idempotency-Key"]).not.toBe(first.headers["Idempotency-Key"]);
    expect(screen.queryByText("Unknown timezone.")).not.toBeInTheDocument();
  });

  it("retries an unchanged body after a network error with the same key", async () => {
    stubZones();
    let calls = 0;
    const api = installFakeApi({
      "POST /churches": () => {
        calls += 1;
        if (calls === 1) throw new TypeError("Failed to fetch");
        return { status: 201, body: NEW_LIFE };
      },
      "GET /me": me({ churches: [NEW_LIFE] }),
    });
    const { user } = renderForm();

    await user.type(screen.getByLabelText("Church name"), "New Life");
    await user.click(screen.getByRole("button", { name: "Create church" }));
    await waitFor(() => expect(toastError).toHaveBeenCalledTimes(1));
    await user.click(screen.getByRole("button", { name: "Create church" }));

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/"));
    const [first, second] = posts(api);
    expect(first.headers["Idempotency-Key"]).toMatch(UUID);
    expect(second.headers["Idempotency-Key"]).toBe(first.headers["Idempotency-Key"]);
    expect(second.body).toEqual(first.body);
  });

  it("gets a new key when the body changes after a network error", async () => {
    stubZones();
    let calls = 0;
    const api = installFakeApi({
      "POST /churches": () => {
        calls += 1;
        if (calls === 1) throw new TypeError("Failed to fetch");
        return { status: 201, body: church({ id: CHURCH_IDS.hope, name: "New Life Church", role: "owner" }) };
      },
      "GET /me": me({ churches: [NEW_LIFE] }),
    });
    const { user } = renderForm();

    await user.type(screen.getByLabelText("Church name"), "New Life");
    await user.click(screen.getByRole("button", { name: "Create church" }));
    await waitFor(() => expect(toastError).toHaveBeenCalledTimes(1));
    await user.type(screen.getByLabelText("Church name"), " Church");
    await user.click(screen.getByRole("button", { name: "Create church" }));

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/"));
    const [first, second] = posts(api);
    expect(second.body).toEqual({ name: "New Life Church", timezone: "America/Chicago" });
    expect(second.headers["Idempotency-Key"]).toMatch(UUID);
    expect(second.headers["Idempotency-Key"]).not.toBe(first.headers["Idempotency-Key"]);
  });

  it("toasts a 5xx with its Ref and retries with the same key", async () => {
    stubZones();
    let calls = 0;
    const api = installFakeApi({
      "POST /churches": () => {
        calls += 1;
        return calls === 1
          ? fakeError(500, "internal_error", "Something went wrong.")
          : { status: 201, body: NEW_LIFE };
      },
      "GET /me": me({ churches: [NEW_LIFE] }),
    });
    const { user } = renderForm();

    await user.type(screen.getByLabelText("Church name"), "New Life");
    await user.click(screen.getByRole("button", { name: "Create church" }));
    await waitFor(() => expect(toastError).toHaveBeenCalledWith("Something went wrong. (Ref: 4f9a2c1e)"));
    await user.click(screen.getByRole("button", { name: "Create church" }));

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/"));
    const [first, second] = posts(api);
    expect(second.headers["Idempotency-Key"]).toBe(first.headers["Idempotency-Key"]);
  });

  it("toasts a network error with the full sentence and keeps what was typed", async () => {
    stubZones();
    installFakeApi({
      "POST /churches": () => {
        throw new TypeError("Failed to fetch");
      },
    });
    const { user } = renderForm();

    await user.type(screen.getByLabelText("Church name"), "New Life");
    await user.click(screen.getByRole("button", { name: "Create church" }));

    await waitFor(() => expect(toastError).toHaveBeenCalledWith(NETWORK_MESSAGE));
    expect(toastError).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText("Church name")).toHaveValue("New Life");
    expect(screen.getByRole("button", { name: "Create church" })).toBeEnabled();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(testRouter.replace).not.toHaveBeenCalled();
  });

  it("shows a 429 in an inline alert above the button, with no toast", async () => {
    stubZones();
    installFakeApi({
      "POST /churches": fakeError(429, "rate_limited", LIMIT_MESSAGE, { details: { retry_after_seconds: 3600 } }),
    });
    const { user } = renderForm();

    await user.type(screen.getByLabelText("Church name"), "New Life");
    await user.click(screen.getByRole("button", { name: "Create church" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(LIMIT_MESSAGE);
    expect(toastError).not.toHaveBeenCalled();
    expect(toastSuccess).not.toHaveBeenCalled();
    expect(testRouter.replace).not.toHaveBeenCalled();
  });

  it("shows 'Still working' after 8 s of pending and hides it when the request ends", async () => {
    vi.useFakeTimers();
    stubZones();
    let answer: (response: FakeResponse) => void = () => {};
    installFakeApi({
      "POST /churches": () =>
        new Promise<FakeResponse>((resolve) => {
          answer = resolve;
        }),
    });
    renderForm();

    fireEvent.change(screen.getByLabelText("Church name"), { target: { value: "New Life" } });
    fireEvent.click(screen.getByRole("button", { name: "Create church" }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(screen.getByRole("button", { name: "Creating church…" })).toBeDisabled();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(7_999);
    });
    expect(screen.queryByText(STILL_WORKING)).not.toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(screen.getByText(STILL_WORKING)).toBeInTheDocument();

    answer(fakeError(500, "internal_error", "Something went wrong."));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(screen.queryByText(STILL_WORKING)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create church" })).toBeEnabled();
  });
});

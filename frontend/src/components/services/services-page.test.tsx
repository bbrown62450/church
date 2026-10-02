/**
 * The Services page (slice 5a spec, "Services page", Testing
 * `services-archive.test.tsx`; F §4.8). The page renders as the route does,
 * with a Toaster; the draft is seeded in localStorage. The clock is fixed at
 * Tuesday, September 29, 2026, so a fresh draft is dated Sunday, October 4.
 */
import { screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ServicesRoute from "@/app/(signed-in)/(church)/services/page";
import { Toaster } from "@/components/ui/sonner";
import type { ServiceSummary } from "@/lib/api/types";
import { formatSavedAt } from "@/lib/dates";
import { serviceToDraft } from "@/lib/draft/mapping";
import { editOccasion } from "@/lib/draft/readings";
import { draftKey, type DraftV1 } from "@/lib/draft/schema";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import {
  church,
  churchProfile,
  DRAFT_NOW,
  me,
  savedService,
  SERVICE_ID,
  servicePage,
  serviceSummary,
  testDraft,
  USER_ID,
} from "@/test/fixtures";
import { testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

const KEY = draftKey(USER_ID, church().id);
const GONE = "That service is no longer in the archive.";

function renderServices(draft: DraftV1 | null, routes: Record<string, FakeHandler>) {
  if (draft) window.localStorage.setItem(KEY, JSON.stringify(draft));
  const api = installFakeApi({ "GET /church": churchProfile(), ...routes });
  const view = renderWithProviders(
    <>
      <ServicesRoute />
      <Toaster />
    </>,
    { me: me(), church: church(), path: "/services" },
  );
  return { ...view, api };
}

function listRequests(api: { requests: RecordedRequest[] }) {
  return api.requests.filter((r) => r.method === "GET" && r.path.startsWith("/services?"));
}

function stored(): DraftV1 {
  return JSON.parse(window.localStorage.getItem(KEY) ?? "null") as DraftV1;
}

/** `n` rows with distinct ids and dates, newest first. */
function rows(n: number, from = 0): ServiceSummary[] {
  return Array.from({ length: n }, (_, i) =>
    serviceSummary({ id: `00000000-0000-4000-8000-${String(from + i + 1).padStart(12, "0")}`, occasion: `Service ${from + i + 1}` }),
  );
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
});

afterEach(() => {
  toast.dismiss(); // sonner replays a toast still showing to the next Toaster
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("Services (slice 5a-3)", () => {
  it("shows five rows while it loads, then each service with its date, occasion and who saved it", async () => {
    let release!: () => void;
    const held = new Promise<void>((resolve) => (release = resolve));
    const undated = serviceSummary({
      id: "77777777-7777-4777-8777-777777777777",
      service_date_iso: null,
      service_date: "",
      occasion: "",
      created_by: null,
      saved_at: "2026-09-20T12:00:00+00:00",
    });
    renderServices(testDraft(), {
      "GET /services": async () => {
        await held;
        return servicePage([serviceSummary(), undated]);
      },
    });
    expect(await screen.findByRole("heading", { level: 1, name: "Services" })).toBeInTheDocument();
    expect(screen.getByText("Saved services for Grace.")).toBeInTheDocument();
    const loading = screen.getByRole("status", { name: "Loading" });
    expect(loading.querySelectorAll('[data-slot="skeleton"]')).toHaveLength(5);
    release();
    const list = await screen.findByRole("list");
    const buttons = within(list)
      .getAllByRole("listitem")
      .map((li) => within(li).getAllByRole("button")[0]);
    expect(buttons.map((b) => b.textContent)).toEqual([
      `October 4, 2026World Communion SundayCreated by Pat Pastor · last saved ${formatSavedAt(serviceSummary().saved_at)}`,
      `No dateNo occasionLast saved ${formatSavedAt("2026-09-20T12:00:00+00:00")}`,
    ]);
    expect(buttons[0]).toHaveClass("min-h-11");
    expect(within(list).getByRole("button", { name: "More actions for October 4, 2026" })).toHaveClass("size-11");
    expect(screen.getByText("Showing 2 of 2")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Show more" })).toBeNull();
    expect(screen.queryByText("Editing")).toBeNull();
  });

  it("with nothing saved, offers to build a service; New service opens the builder", async () => {
    const { user } = renderServices(testDraft(), { "GET /services": servicePage([]) });
    expect(await screen.findByText("No saved services yet")).toBeInTheDocument();
    expect(screen.getByText("Services you save from the builder appear here.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Build a service" })).toHaveAttribute("href", "/builder");
    await user.click(screen.getByRole("button", { name: "New service" }));
    expect(testRouter.push).toHaveBeenCalledWith("/builder/readings");
  });

  it("shows an error with Retry, never an empty list, and Retry asks again", async () => {
    let calls = 0;
    const { user, api } = renderServices(testDraft(), {
      "GET /services": () => {
        calls += 1;
        return calls === 1 ? fakeError(500, "internal_error", "Something went wrong.") : servicePage(rows(1));
      },
    });
    expect(await screen.findByText("Something went wrong. (Ref: 4f9a2c1e)")).toBeInTheDocument();
    expect(screen.queryByText("No saved services yet")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Service 1")).toBeInTheDocument();
    expect(listRequests(api)).toHaveLength(2);
  });

  it("Show more reads the next 20", async () => {
    const { user, api } = renderServices(testDraft(), {
      "GET /services?limit=20&offset=0": servicePage(rows(20), { total: 45 }),
      "GET /services?limit=20&offset=20": servicePage(rows(20, 20), { total: 45, offset: 20 }),
    });
    expect(await screen.findByText("Showing 20 of 45")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Show more" }));
    expect(await screen.findByText("Showing 40 of 45")).toBeInTheDocument();
    expect(listRequests(api).map((r) => r.path)).toEqual(["/services?limit=20&offset=0", "/services?limit=20&offset=20"]);
    expect(screen.getByText("Service 40")).toBeInTheDocument();
  });

  it("after Show more, a delete reads every page again and the count follows; an undated row's menu names its occasion", async () => {
    const undatedId = "88888888-8888-4888-8888-888888888888";
    const undated = serviceSummary({ id: undatedId, service_date_iso: null, service_date: "", occasion: "Service 40" });
    let deleted = false;
    const { user, api } = renderServices(testDraft(), {
      "GET /services?limit=20&offset=0": () => servicePage(rows(20), { total: deleted ? 44 : 45 }),
      "GET /services?limit=20&offset=20": () =>
        servicePage(deleted ? rows(19, 20) : [...rows(19, 20), undated], { total: deleted ? 44 : 45, offset: 20 }),
      [`DELETE /services/${undatedId}`]: () => {
        deleted = true;
        return { deleted: true };
      },
    });
    expect(await screen.findByText("Showing 20 of 45")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Show more" }));
    expect(await screen.findByText("Showing 40 of 45")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "More actions for No date, Service 40" }));
    await user.click(await screen.findByRole("menuitem", { name: "Delete…" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Delete this service?" });
    await user.click(within(dialog).getByRole("button", { name: "Delete service" }));
    expect(await screen.findByText("Showing 39 of 44")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(screen.queryByText("Service 40")).toBeNull();
    const [first, more] = ["/services?limit=20&offset=0", "/services?limit=20&offset=20"];
    expect(listRequests(api).map((r) => r.path)).toEqual([first, more, first, more]);
  });

  it("opens a service into the builder at once when the draft has nothing unsaved", async () => {
    const { user, api } = renderServices(testDraft(), {
      "GET /services": servicePage([serviceSummary()]),
      [`GET /services/${SERVICE_ID}`]: savedService(),
    });
    await user.click(await screen.findByRole("button", { name: /World Communion Sunday/ }));
    await waitFor(() => expect(testRouter.push).toHaveBeenCalledWith("/builder/review"));
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(api.requests.filter((r) => r.path === `/services/${SERVICE_ID}`)).toHaveLength(1);
    expect(stored()).toMatchObject({
      last_step: "review",
      editing: { service_id: SERVICE_ID, date_iso: "2026-10-04" },
      readings: { occasion: "World Communion Sunday", fields_origin: "archive" },
    });
  });

  it("asks before replacing unsaved work, and a service gone from the archive says so and refreshes the list", async () => {
    const { user, api } = renderServices(editOccasion(testDraft(), "Harvest"), {
      "GET /services": servicePage([serviceSummary()]),
      [`GET /services/${SERVICE_ID}`]: fakeError(404, "not_found", GONE),
    });
    await user.click(await screen.findByRole("button", { name: /World Communion Sunday/ }));
    const dialog = await screen.findByRole("alertdialog", { name: "Replace your unsaved draft?" });
    expect(dialog).toHaveTextContent(
      "Your current draft for October 4, 2026 has changes that aren't saved to the archive. Opening this service replaces it.",
    );
    await user.click(within(dialog).getByRole("button", { name: "Replace draft" }));
    expect(await screen.findByText(GONE)).toBeInTheDocument();
    await waitFor(() => expect(listRequests(api)).toHaveLength(2));
    expect(testRouter.push).not.toHaveBeenCalled();
    expect(stored().readings.occasion).toBe("Harvest");
  });

  it("deletes after asking, for everyone in the church; deleting the service being edited clears the draft", async () => {
    let deleted = false;
    const { user, api } = renderServices(serviceToDraft(savedService(), { church: churchProfile(), user: { id: USER_ID } }), {
      "GET /services": () => servicePage(deleted ? [] : [serviceSummary()]),
      [`DELETE /services/${SERVICE_ID}`]: () => {
        deleted = true;
        return { deleted: true };
      },
    });
    const row = (await screen.findByRole("button", { name: /World Communion Sunday/ })).closest("li") as HTMLElement;
    expect(within(row).getByText("Editing")).toBeInTheDocument();
    await user.click(within(row).getByRole("button", { name: "More actions for October 4, 2026" }));
    await user.click(await screen.findByRole("menuitem", { name: "Delete…" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Delete this service?" });
    expect(dialog).toHaveTextContent(
      "“World Communion Sunday” on October 4, 2026 will be removed from the archive for everyone in Grace. This can't be undone. " +
        "You're editing this service. Your current draft will be cleared too.",
    );
    await user.click(within(dialog).getByRole("button", { name: "Delete service" }));
    expect(await screen.findByText("No saved services yet")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(api.requests.filter((r) => r.method === "DELETE")).toHaveLength(1);
    expect(stored().editing).toBeNull();
    expect(stored().readings.occasion).toBe("");
  });

  it("names an untitled, undated service, and a delete that finds it gone says so", async () => {
    const undated = serviceSummary({ service_date_iso: null, service_date: "", occasion: "" });
    const { user, api } = renderServices(testDraft(), {
      "GET /services": servicePage([undated]),
      [`DELETE /services/${SERVICE_ID}`]: fakeError(404, "not_found", GONE),
    });
    await user.click(await screen.findByRole("button", { name: "More actions for No date" }));
    await user.click(await screen.findByRole("menuitem", { name: "Delete…" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Delete this service?" });
    expect(dialog).toHaveTextContent(
      "“Untitled service” (no date) will be removed from the archive for everyone in Grace. This can't be undone.",
    );
    expect(dialog).not.toHaveTextContent("You're editing");
    await user.click(within(dialog).getByRole("button", { name: "Delete service" }));
    expect(await screen.findByText(GONE)).toBeInTheDocument();
    await waitFor(() => expect(listRequests(api)).toHaveLength(2));
  });
});

/**
 * Review & send in slice 5a-1 (slice 5a spec, UX "Word documents card",
 * Testing `review-step.test.tsx` "Downloads" and "Invalid date"; owner answers
 * 2 and 3, 2026-10-01). The step renders inside the builder layout with a
 * Toaster; `URL.createObjectURL` and the link's click are stubbed, so a
 * download is recorded instead of navigating. The clock is fixed at Tuesday,
 * September 29, 2026, so a fresh draft is dated Sunday, October 4, 2026.
 */
import { act, screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import ReviewStepPage from "@/app/(signed-in)/(church)/builder/review/page";
import { Toaster } from "@/components/ui/sonner";
import { draftKey, type DraftV1 } from "@/lib/draft/schema";
import { pickFromHymn, setSlot } from "@/lib/hymns/picks";
import { editCardText, setCardEnabled } from "@/lib/liturgy/cards";
import { REVOKE_AFTER_MS } from "@/lib/download";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import {
  church,
  churchProfile,
  DRAFT_NOW,
  gg2013,
  hymnals,
  hymnListRoute,
  lectionaryRoute,
  liturgyConfig,
  me,
  testDraft,
  translations,
  USER_ID,
} from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { NEEDS_DATE, SAME_AS_BULLETIN } from "./documents-card";

const KEY = draftKey(USER_ID, church().id);
const NAME = "worship_October_04_2026.docx";
const HYMN_GONE = "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step.";

/** A Word file response, with the server's Content-Disposition unless `headers` says otherwise. */
function docx(headers: Record<string, string> = { "Content-Disposition": `attachment; filename="${NAME}"; filename*=UTF-8''${NAME}` }) {
  return new Response(new Uint8Array([0x50, 0x4b, 3, 4]), {
    status: 200,
    headers: { "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ...headers },
  });
}

let clicks: { download: string; href: string }[];
let revoked: string[];

function renderReview(draft: DraftV1 = testDraft(), routes: Record<string, FakeHandler> = {}) {
  window.localStorage.setItem(KEY, JSON.stringify(draft));
  const api = installFakeApi({
    "GET /church": churchProfile(),
    "GET /lectionary/readings": lectionaryRoute(),
    "GET /translations": translations(),
    "GET /hymnals": hymnals(),
    "GET /hymns": hymnListRoute(),
    "GET /liturgy/config": liturgyConfig(),
    ...routes,
  });
  const view = renderWithProviders(
    <>
      <BuilderLayout>
        <ReviewStepPage />
      </BuilderLayout>
      <Toaster />
    </>,
    { me: me(), church: church(), path: "/builder/review" },
  );
  return { ...view, api };
}

async function documentsCard() {
  return screen.findByRole("region", { name: "Word documents" });
}

function documentRequests(api: { requests: RecordedRequest[] }) {
  return api.requests.filter((r) => r.method === "POST" && r.path === "/documents");
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
  clicks = [];
  revoked = [];
  let n = 0;
  Object.assign(URL, {
    createObjectURL: vi.fn(() => `blob:test/${(n += 1)}`),
    revokeObjectURL: vi.fn((url: string) => revoked.push(url)),
  });
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
    clicks.push({ download: this.download, href: this.getAttribute("href") ?? "" });
  });
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("Review & send: the Word documents (slice 5a-1)", () => {
  it("shows Still needed, both copies with what they hold, and the archive note, with no placeholder", async () => {
    renderReview();
    const card = await documentsCard();
    expect(within(card).getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual(["Bulletin copy", "Pastor's copy"]);
    const bulletin = within(card).getByRole("button", { name: "Download bulletin copy" });
    const pastor = within(card).getByRole("button", { name: "Download pastor's copy" });
    expect(bulletin).toHaveAccessibleDescription(
      "The order of worship with hymns, readings and the sermon title. Leaves out Prayers of the People.",
    );
    // Prayers of the People is off on a fresh draft, so the two copies are the same.
    expect(pastor).toHaveAccessibleDescription(`Everything in the bulletin copy, plus Prayers of the People. ${SAME_AS_BULLETIN}`);
    for (const button of [bulletin, pastor]) {
      expect(button).toBeEnabled();
      expect(button).toHaveClass("h-11"); // 44 px on a phone
    }
    expect(within(card).queryByText(NEEDS_DATE)).toBeNull();
    expect(screen.getByRole("region", { name: "Still needed" })).toBeInTheDocument();
    const archive = screen.getByRole("region", { name: "Archive" });
    expect(archive).toHaveTextContent("Saving services to the archive is coming soon.");
    expect(screen.queryByText("Available soon")).toBeNull();
  });

  it("downloads the bulletin copy built from the draft, under the server's name", async () => {
    const [holy] = gg2013();
    let d = setSlot(testDraft(), "opening", pickFromHymn(holy));
    d = editCardText(d, "call_to_worship", "Leader: Come. People: We come.");
    const { api, user } = renderReview(d, { "POST /documents": () => docx() });
    const card = await documentsCard();
    await user.click(within(card).getByRole("button", { name: "Download bulletin copy" }));

    await waitFor(() => expect(clicks).toEqual([{ download: NAME, href: "blob:test/1" }]));
    const [request] = documentRequests(api);
    expect(request.headers["x-church-id"]).toBe(church().id);
    expect(request.body).toMatchObject({
      variant: "bulletin",
      service: {
        service_date_iso: "2026-10-04",
        hymns: { opening: { hymn_id: holy.id, title: holy.title, number: holy.number }, response: null, closing: null },
        liturgy: { call_to_worship: "Leader: Come. People: We come.", benediction: "Halverson" },
      },
    });
    expect(revoked).toEqual([]); // kept 5 minutes: revoking at once breaks Safari
    expect(REVOKE_AFTER_MS).toBe(300_000);
    expect(within(card).getByRole("button", { name: "Download bulletin copy" })).toBeEnabled();
  });

  it("names the pastor's copy itself when the header is missing; each button has its own Preparing…, then Still working… after 8 s", async () => {
    vi.useRealTimers(); // a second useFakeTimers call would keep beforeEach's Date-only fake
    vi.useFakeTimers({ toFake: ["Date", "setTimeout", "clearTimeout"], shouldAdvanceTime: true });
    vi.setSystemTime(DRAFT_NOW);
    let release!: () => void;
    const held = new Promise<void>((resolve) => (release = resolve));
    const { api, user } = renderReview(editCardText(setCardEnabled(testDraft(), "prayers_of_the_people", true), "prayers_of_the_people", "We pray."), {
      "POST /documents": async () => {
        await held;
        return docx({});
      },
    });
    const card = await documentsCard();
    const pastor = within(card).getByRole("button", { name: "Download pastor's copy" });
    expect(pastor).toHaveAccessibleDescription("Everything in the bulletin copy, plus Prayers of the People.");
    await user.click(pastor);
    expect(await within(card).findByRole("button", { name: "Preparing…" })).toBeDisabled();
    expect(within(card).getByRole("button", { name: "Download bulletin copy" })).toBeEnabled();
    expect(within(card).getAllByRole("status").map((s) => s.textContent)).toEqual(["", "Pastor's copy: Preparing…"]);
    act(() => {
      vi.advanceTimersByTime(8_000);
    });
    expect(within(card).getByRole("button", { name: "Still working…" })).toBeDisabled();
    expect(within(card).getAllByRole("status")[1]).toHaveTextContent("Pastor's copy: Still working…");
    release();
    await waitFor(() => expect(clicks).toEqual([{ download: "worship_pastor_October_04_2026.docx", href: "blob:test/1" }]));
    expect((documentRequests(api)[0].body as { variant: string }).variant).toBe("pastor");
    expect(await within(card).findByRole("button", { name: "Download pastor's copy" })).toBeEnabled();
  });

  it("shows the server's message when a download fails, and saves no file", async () => {
    const [holy] = gg2013();
    const { user } = renderReview(setSlot(testDraft(), "response", pickFromHymn(holy)), {
      "POST /documents": fakeError(404, "not_found", HYMN_GONE, { details: { field: "hymns.response.hymn_id" } }),
    });
    const card = await documentsCard();
    await user.click(within(card).getByRole("button", { name: "Download bulletin copy" }));
    expect(await screen.findByText(HYMN_GONE)).toBeInTheDocument();
    expect(clicks).toEqual([]);
    expect(URL.createObjectURL).not.toHaveBeenCalled();
    expect(within(card).getByRole("button", { name: "Download bulletin copy" })).toBeEnabled();
  });

  it("adds no message of its own after a 401 or a lost church, and saves no file", async () => {
    const errorToast = vi.spyOn(toast, "error");
    const responses = [
      fakeError(401, "unauthorized", "Sign in again."),
      fakeError(403, "forbidden", "You no longer have access to this church.", { details: { reason: "no_church_access" } }),
    ];
    for (const response of responses) {
      const { api, user, unmount } = renderReview(testDraft(), { "POST /documents": response });
      const card = await documentsCard();
      await user.click(within(card).getByRole("button", { name: "Download bulletin copy" }));
      await waitFor(() => expect(documentRequests(api)).toHaveLength(1));
      await waitFor(() => expect(within(card).getByRole("button", { name: "Download bulletin copy" })).toBeEnabled());
      unmount();
    }
    expect(errorToast).not.toHaveBeenCalled();
    expect(clicks).toEqual([]);
    expect(URL.createObjectURL).not.toHaveBeenCalled();
  });

  it("turns both buttons off without a service date, and says why", async () => {
    const d = testDraft();
    const { api } = renderReview({ ...d, readings: { ...d.readings, date_iso: "" } });
    const card = await documentsCard();
    expect(within(card).getByText(NEEDS_DATE)).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Download bulletin copy" })).toBeDisabled();
    expect(within(card).getByRole("button", { name: "Download pastor's copy" })).toBeDisabled();
    expect(within(screen.getByRole("region", { name: "Still needed" })).getByText(/No service date/)).toBeInTheDocument();
    expect(documentRequests(api)).toEqual([]);
  });
});

/**
 * Review & send (slice 5a spec, UX "Review step", Testing
 * `review-step.test.tsx`; owner answers 2-5 and 9, 2026-10-01): the Word
 * documents (5a-1) and saving (5a-3). The step renders inside the builder
 * layout with a Toaster; `URL.createObjectURL` and the link's click are
 * stubbed, so a download is recorded instead of navigating. The clock is
 * fixed at Tuesday, September 29, 2026, so a fresh draft is dated Sunday,
 * October 4, 2026. A test that needs an edit made elsewhere in the builder
 * renders a probe button that applies it.
 */
import { act, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import ReviewStepPage from "@/app/(signed-in)/(church)/builder/review/page";
import { Toaster } from "@/components/ui/sonner";
import { formatSavedAt } from "@/lib/dates";
import { emptyServiceBulletin, setAnnouncement } from "@/lib/draft/bulletin";
import { useDraft } from "@/lib/draft/context";
import { serviceToDraft } from "@/lib/draft/mapping";
import { draftKey, type DraftV1 } from "@/lib/draft/schema";
import { pickFromHymn, setSlot } from "@/lib/hymns/picks";
import { editOccasion, editScriptureLines, setDate, setTranslation } from "@/lib/draft/readings";
import { editCardText, setCardEnabled } from "@/lib/liturgy/cards";
import { REVOKE_AFTER_MS } from "@/lib/download";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import {
  bulletinSettings,
  church,
  churchProfile,
  DRAFT_NOW,
  filledBulletinSettings,
  gg2013,
  hymnId,
  hymnals,
  hymnListRoute,
  lectionaryRoute,
  liturgyConfig,
  me,
  previousBulletin,
  savedService,
  SERVICE_ID,
  serviceBulletin,
  testDraft,
  translations,
  USER_ID,
} from "@/test/fixtures";
import { testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import { CONFLICT_TITLE, RELOAD_REPLACES } from "./conflict-dialog";
import { FIX_READINGS, NEEDS_DATE, SAME_AS_BULLETIN, SAVE_HINT } from "./documents-card";
import { PRINTED_SUMMARY, SETTINGS_NOTE, WEEKLY_NOTE } from "./printed-card";
import { CONFLICT_MESSAGE, LOADED_LATEST, SAVE_FIX_READINGS, SAVE_NEEDS_DATE } from "./save-card";
import { SAVED_AFTER_DELETE_MESSAGE, SAVED_MESSAGE } from "@/lib/queries/services";
import { DEFAULT_BENEDICTION_FALLBACK } from "@/lib/liturgy/defaults";

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

function renderReview(draft: DraftV1 = testDraft(), routes: Record<string, FakeHandler> = {}, probe: ReactNode = null) {
  window.localStorage.setItem(KEY, JSON.stringify(draft));
  const api = installFakeApi({
    "GET /church": churchProfile(),
    "GET /lectionary/readings": lectionaryRoute(),
    "GET /translations": translations(),
    "GET /hymnals": hymnals(),
    "GET /hymns": hymnListRoute(),
    "GET /liturgy/config": liturgyConfig(),
    "GET /church/bulletin-settings": bulletinSettings(),
    "GET /services/previous-bulletin": previousBulletin(),
    ...routes,
  });
  const view = renderWithProviders(
    <>
      <BuilderLayout>
        <ReviewStepPage />
        {probe}
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
  toast.dismiss(); // sonner replays a toast still showing to the next Toaster
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("Review & send: the Word documents (slice 5a-1)", () => {
  it("shows Still to do, the Archive card and both copies with what they hold, in that order, with no placeholder", async () => {
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
    expect(within(card).queryByText(FIX_READINGS)).toBeNull();
    const step = screen.getByRole("region", { name: "Review & send" });
    expect(within(step).getAllByRole("heading", { level: 2 }).map((h) => h.textContent)).toEqual([
      "Still to do",
      "Archive",
      "Word documents",
      "Printed bulletin",
    ]);
    const archive = screen.getByRole("region", { name: "Archive" });
    expect(within(archive).getByText("Not in the archive yet.")).toHaveAttribute("aria-live", "polite");
    expect(within(archive).getByRole("button", { name: "Save to archive" })).toHaveClass("h-11");
    expect(within(archive).getByRole("button", { name: "Start a new service" })).toHaveClass("h-11");
    expect(screen.queryByText(/coming soon/i)).toBeNull();
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
        liturgy: { call_to_worship: "Leader: Come. People: We come.", benediction: DEFAULT_BENEDICTION_FALLBACK },
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
    const preparing = await within(card).findByRole("button", { name: "Preparing…" });
    expect(preparing).toHaveAttribute("aria-disabled", "true");
    expect(preparing).toBe(pastor); // the same button, so keyboard focus stays on it (build review fix 4)
    expect(pastor).toHaveFocus();
    expect(within(card).getByRole("button", { name: "Download bulletin copy" })).toBeEnabled();
    expect(within(card).getAllByRole("status").map((s) => s.textContent)).toEqual(["", "Pastor's copy: Preparing…"]);
    act(() => {
      vi.advanceTimersByTime(8_000);
    });
    expect(within(card).getByRole("button", { name: "Still working…" })).toHaveAttribute("aria-disabled", "true");
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

  it("turns both buttons and Save off without a service date, and says why", async () => {
    const d = testDraft();
    const { api } = renderReview({ ...d, readings: { ...d.readings, date_iso: "" } });
    const card = await documentsCard();
    expect(within(card).getByText(NEEDS_DATE)).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Download bulletin copy" })).toBeDisabled();
    expect(within(card).getByRole("button", { name: "Download pastor's copy" })).toBeDisabled();
    const archive = screen.getByRole("region", { name: "Archive" });
    expect(within(archive).getByText(SAVE_NEEDS_DATE)).toBeInTheDocument();
    expect(within(archive).getByRole("button", { name: "Save to archive" })).toBeDisabled();
    expect(within(archive).getByRole("button", { name: "Save to archive" })).toHaveAccessibleDescription(SAVE_NEEDS_DATE);
    expect(within(screen.getByRole("region", { name: "Still to do" })).getByText(/No service date/)).toBeInTheDocument();
    expect(documentRequests(api)).toEqual([]);
  });

  it("still shows the failure after the member leaves Review mid-download (build review fix 5)", async () => {
    const errorToast = vi.spyOn(toast, "error");
    let release!: () => void;
    const held = new Promise<void>((resolve) => (release = resolve));
    const failure = fakeError(404, "not_found", HYMN_GONE, { details: { field: "hymns.response.hymn_id" } });
    const { api, user, unmount } = renderReview(testDraft(), {
      "POST /documents": async () => {
        await held;
        return failure;
      },
    });
    const card = await documentsCard();
    await user.click(within(card).getByRole("button", { name: "Download bulletin copy" }));
    await waitFor(() => expect(documentRequests(api)).toHaveLength(1));
    unmount();
    release();
    await waitFor(() => expect(errorToast).toHaveBeenCalledWith(HYMN_GONE));
    expect(clicks).toEqual([]);
  });

  it("turns both buttons and Save off while a Date & readings field shows its message, and says why (build review fix 6)", async () => {
    const tooMany = editScriptureLines(testDraft(), Array.from({ length: 21 }, (_, i) => `Psalm ${i + 1}`).join("\n"));
    const d = testDraft();
    const longLine = editScriptureLines(d, `Isaiah 5:1-7\n${"x".repeat(201)}`);
    const longOccasion = { ...d, readings: { ...d.readings, occasion: "o".repeat(301) } };
    for (const draft of [tooMany, longLine, longOccasion]) {
      const { api, unmount } = renderReview(draft);
      const card = await documentsCard();
      expect(within(card).getByText(FIX_READINGS)).toBeInTheDocument();
      expect(within(card).queryByText(NEEDS_DATE)).toBeNull();
      expect(within(card).getByRole("button", { name: "Download bulletin copy" })).toBeDisabled();
      expect(within(card).getByRole("button", { name: "Download pastor's copy" })).toBeDisabled();
      const archive = screen.getByRole("region", { name: "Archive" });
      expect(within(archive).getByText(SAVE_FIX_READINGS)).toBeInTheDocument();
      expect(within(archive).getByRole("button", { name: "Save to archive" })).toBeDisabled();
      expect(within(archive).getByRole("button", { name: "Save to archive" })).toHaveAccessibleDescription(SAVE_FIX_READINGS);
      expect(documentRequests(api)).toEqual([]);
      unmount();
      window.localStorage.clear();
    }
  });
});

// --- the printed bulletin (printed bulletin spec, PR 1) ------------------------------

const PDF_NAME = "printed_bulletin_October_04_2026.pdf";

function pdf() {
  return new Response(new Uint8Array([0x25, 0x50, 0x44, 0x46]), {
    status: 200,
    headers: { "Content-Type": "application/pdf", "Content-Disposition": `attachment; filename="${PDF_NAME}"` },
  });
}

function printedRequests(api: { requests: RecordedRequest[] }) {
  return api.requests.filter((r) => r.method === "POST" && r.path === "/documents/printed");
}

describe("Review & send: the printed bulletin (printed bulletin PR 1)", () => {
  it("shows the card after the Word documents with what it prints and both files", async () => {
    renderReview();
    const card = await screen.findByRole("region", { name: "Printed bulletin" });
    expect(within(card).getByText(PRINTED_SUMMARY)).toBeInTheDocument();
    expect(within(card).getByText(WEEKLY_NOTE)).toBeInTheDocument();
    expect(within(card).queryByText(/\[placeholders\]/)).toBeNull(); // PR 1's note is gone (PR 2b)
    const printed = within(card).getByRole("button", { name: "Download printed bulletin" });
    const word = within(card).getByRole("button", { name: "Download Word version" });
    expect(printed).toHaveAccessibleDescription(
      "Ready to print on legal paper, two pages to a side.",
    );
    expect(word).toHaveAccessibleDescription("The same bulletin as a Word file, to change before printing.");
    for (const button of [printed, word]) {
      expect(button).toBeEnabled();
      expect(button).toHaveClass("h-11");
    }
  });

  it("downloads the PDF with the draft's translation, and names the Word version itself when the header is missing", async () => {
    const d = setTranslation(editCardText(testDraft(), "call_to_worship", "Leader: Come. People: We come."), "kjv", "web");
    const { api, user } = renderReview(d, {
      "POST /documents/printed": (request: RecordedRequest) => ((request.body as { format: string }).format === "pdf" ? pdf() : docx({})),
    });
    const card = await screen.findByRole("region", { name: "Printed bulletin" });
    await user.click(within(card).getByRole("button", { name: "Download printed bulletin" }));
    await waitFor(() => expect(clicks).toEqual([{ download: PDF_NAME, href: "blob:test/1" }]));
    expect(printedRequests(api)[0].body).toMatchObject({
      format: "pdf",
      translation: "kjv",
      service: { service_date_iso: "2026-10-04", liturgy: { call_to_worship: "Leader: Come. People: We come." } },
    });
    expect(printedRequests(api)[0].headers["x-church-id"]).toBe(church().id);
    expect(await within(card).findByText(SAVE_HINT)).toBeInTheDocument();
    await user.click(within(card).getByRole("button", { name: "Download Word version" }));
    await waitFor(() => expect(clicks).toHaveLength(2));
    expect(clicks[1].download).toBe("printed_bulletin_October_04_2026.docx");
    expect((printedRequests(api)[1].body as { format: string }).format).toBe("docx");
  });

  it("turns both off without a service date, and shows the server's message when a download fails", async () => {
    const d = testDraft();
    const undated = renderReview({ ...d, readings: { ...d.readings, date_iso: "" } });
    let card = await screen.findByRole("region", { name: "Printed bulletin" });
    expect(within(card).getByText(NEEDS_DATE)).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Download printed bulletin" })).toBeDisabled();
    expect(within(card).getByRole("button", { name: "Download Word version" })).toBeDisabled();
    undated.unmount();
    window.localStorage.clear();

    const { user } = renderReview(testDraft(), {
      "POST /documents/printed": fakeError(404, "not_found", HYMN_GONE, { details: { field: "hymns.response.hymn_id" } }),
    });
    card = await screen.findByRole("region", { name: "Printed bulletin" });
    await user.click(within(card).getByRole("button", { name: "Download printed bulletin" }));
    expect(await screen.findByText(HYMN_GONE)).toBeInTheDocument();
    expect(clicks).toEqual([]);
  });

  it("lists the bulletin settings still blank and links to them (printed bulletin PR 2a)", async () => {
    const blank = renderReview();
    let card = await screen.findByRole("region", { name: "Printed bulletin" });
    expect(within(card).getByText(SETTINGS_NOTE)).toBeInTheDocument();
    expect(
      await within(card).findByText(
        "Not filled in: address, phone, email, website, Facebook name, service time, worship leader, liturgist, organist, prelude, postlude, announcements.",
      ),
    ).toBeInTheDocument();
    const download = within(card).getByRole("button", { name: "Download printed bulletin" });
    // The list comes before the downloads (read before printing); the button after them.
    const missing = within(card).getByText(/^Not filled in:/);
    expect(missing.compareDocumentPosition(download) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    const link = within(card).getByRole("link", { name: "Bulletin settings" });
    expect(download.compareDocumentPosition(link) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(link).toHaveAttribute("href", "/bulletin-settings");
    expect(link).toHaveClass("h-11");
    blank.unmount();
    window.localStorage.clear();

    const filled = renderReview(testDraft(), { "GET /church/bulletin-settings": filledBulletinSettings({ organist: "" }) });
    card = await screen.findByRole("region", { name: "Printed bulletin" });
    expect(await within(card).findByText("Not filled in: organist, prelude, postlude, announcements.")).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Download printed bulletin" })).toBeEnabled();
    filled.unmount();
  });

  it("carries last week's music and announcements in, lists what to check, and prints them (printed bulletin PR 2b)", async () => {
    const lastWeek = previousBulletin({
      service_id: "s-last",
      service_date_iso: "2026-09-27",
      bulletin: serviceBulletin({
        prelude: { title: "Morning Voluntary", composer: "Pat Example" },
        announcements: { ...serviceBulletin().announcements, ushers: "Sam Sample", coffee_hour: "The Example family" },
      }),
    });
    const { api, user } = renderReview(testDraft(), {
      "GET /church/bulletin-settings": filledBulletinSettings(),
      "GET /services/previous-bulletin": lastWeek,
      "POST /documents/printed": pdf(),
    });
    const card = await screen.findByRole("region", { name: "Printed bulletin" });
    expect(await within(card).findByText("From last week, not checked yet: prelude, ushers and counters, coffee hour.")).toBeInTheDocument();
    expect(within(card).getByText("Not filled in: postlude.")).toBeInTheDocument();
    await user.click(within(card).getByRole("button", { name: "Download printed bulletin" }));
    await waitFor(() => expect(printedRequests(api)).toHaveLength(1));
    expect(printedRequests(api)[0].body).toMatchObject({
      service: { bulletin: { prelude: { title: "Morning Voluntary" }, announcements: { coffee_hour: "The Example family" } } },
    });
    const progress = screen.getByRole("navigation", { name: "Steps" });
    expect(within(progress).getAllByRole("link")[3]).toHaveTextContent("4 Bulletin 3 to check");
  });
});

// --- slice 5a-3: saving ------------------------------------------------------------

const FIRST_SAVE = "2026-10-01T14:42:00.123456+00:00";
const SECOND_SAVE = "2026-10-02T15:05:00+00:00";
const OTHER_ID = "66666666-6666-4666-8666-666666666666";

/** A button the test presses to change the draft as another step would. */
function Probe({ edit }: { edit: (d: DraftV1) => DraftV1 }) {
  const { update } = useDraft();
  return (
    <button type="button" onClick={() => update(edit)}>
      Probe edit
    </button>
  );
}

/** The draft as `serviceToDraft` opens `savedService(overrides)`. */
function opened(overrides: Parameters<typeof savedService>[0] = {}): DraftV1 {
  return serviceToDraft(savedService(overrides), { church: churchProfile(), user: { id: USER_ID } });
}

function archiveCard() {
  return screen.findByRole("region", { name: "Archive" });
}

function serviceRequests(api: { requests: RecordedRequest[] }, method: string) {
  return api.requests.filter((r) => r.method === method && r.path.startsWith("/services"));
}

/** The summary's status line, found by its archive half: the only part that links (to Review). */
function summaryStatus(aside: HTMLElement, archive: string) {
  const link = within(aside).getByRole("link", { name: archive });
  expect(link).toHaveAttribute("href", "/builder/review");
  return link.closest("p");
}

/** The draft as last written to localStorage. */
function stored(): DraftV1 {
  return JSON.parse(window.localStorage.getItem(KEY) ?? "null") as DraftV1;
}

describe("Review & send: saving (slice 5a-3)", () => {
  it("saves a new service with the draft's key, saves changes with If-Match, and every status follows", async () => {
    const d = editOccasion(testDraft(), "Harvest");
    const { api, user } = renderReview(
      d,
      {
        "POST /services": () => ({ status: 201, body: savedService({ occasion: "Harvest", saved_at: FIRST_SAVE }) }),
        [`PUT /services/${SERVICE_ID}`]: () => savedService({ occasion: "Harvest Home", saved_at: SECOND_SAVE }),
      },
      <Probe edit={(draft) => editOccasion(draft, "Harvest Home")} />,
    );
    const card = await archiveCard();
    const progress = screen.getByRole("navigation", { name: "Steps" });
    const aside = screen.getByRole("complementary", { name: "Summary" });
    expect(within(progress).getAllByRole("link")[4]).toHaveTextContent("5 Review & send Not in archive");
    expect(summaryStatus(aside, "Not in archive")).toHaveTextContent("Draft saved on this device · Not in archive");

    await user.click(within(card).getByRole("button", { name: "Save to archive" }));
    expect(await screen.findByText(SAVED_MESSAGE)).toBeInTheDocument();
    const [post] = serviceRequests(api, "POST");
    expect(post.headers["idempotency-key"]).toBe(d.save_key);
    expect(post.headers["x-church-id"]).toBe(church().id);
    expect(post.body).toMatchObject({ service_date_iso: "2026-10-04", occasion: "Harvest", include_communion: true });
    expect(within(card).getByText(`Saved to the archive · ${formatSavedAt(FIRST_SAVE)}`)).toBeInTheDocument();
    expect(within(progress).getAllByRole("link")[4]).toHaveTextContent("5 Review & send Saved");
    expect(summaryStatus(aside, `In archive (saved ${formatSavedAt(FIRST_SAVE)})`)).toHaveTextContent(
      `Draft saved on this device · In archive (saved ${formatSavedAt(FIRST_SAVE)})`,
    );
    await waitFor(() => expect(stored().editing).toEqual({ service_id: SERVICE_ID, saved_at: FIRST_SAVE, date_iso: "2026-10-04" }));
    expect(stored().save_key).not.toBe(d.save_key); // a definitive answer: the next POST gets a new key
    expect(stored().save_key_fingerprint).toBeNull();
    expect(stored().created_at).toBe(d.created_at); // the same draft, so the reviewer's notes stay (owner answer 9)
    // Owner answer 4: what followed a default is now the saved service's own.
    expect(stored().liturgy.cards.benediction.origin).toBe("archive");
    expect(stored().liturgy.communion_origin).toBe("archive");

    await user.click(screen.getByRole("button", { name: "Probe edit" }));
    expect(within(card).getByText(`Unsaved changes · last saved ${formatSavedAt(FIRST_SAVE)}`)).toBeInTheDocument();
    expect(within(progress).getAllByRole("link")[4]).toHaveTextContent("5 Review & send Unsaved changes");
    expect(summaryStatus(aside, `In archive (saved ${formatSavedAt(FIRST_SAVE)}) · Unsaved changes`)).toHaveTextContent(
      `Draft saved on this device · In archive (saved ${formatSavedAt(FIRST_SAVE)}) · Unsaved changes`,
    );

    await user.click(within(card).getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(within(card).getByText(`Saved to the archive · ${formatSavedAt(SECOND_SAVE)}`)).toBeInTheDocument());
    const [put] = serviceRequests(api, "PUT");
    expect(put.path).toBe(`/services/${SERVICE_ID}`);
    expect(put.headers["if-match"]).toBe(FIRST_SAVE);
    expect(put.headers["idempotency-key"]).toBeUndefined();
    expect(put.body).toMatchObject({ occasion: "Harvest Home" });
    expect(serviceRequests(api, "POST")).toHaveLength(1);
  });

  it("opens with the banner and the hymn to replace, and saves a copy when the date changed or the service had none", async () => {
    const moved = setDate(opened(), "2026-10-11");
    const first = renderReview(moved, {
      "POST /services": () => ({ status: 201, body: savedService({ id: OTHER_ID, service_date_iso: "2026-10-11", saved_at: SECOND_SAVE }) }),
    });
    const card = await archiveCard();
    expect(screen.getByText("You're editing the saved service for October 4, 2026. Changes stay on this device until you save.")).toBeInTheDocument();
    const todo = screen.getByRole("region", { name: "Still to do" });
    expect(within(todo).getByText(/Old Favorite isn't in your hymnal/)).toBeInTheDocument();
    expect(within(todo).getByRole("link", { name: "Choose a replacement" })).toHaveAttribute("href", "/builder/hymns");
    const button = within(card).getByRole("button", { name: "Save as new service" });
    expect(button).toHaveAccessibleDescription(
      "The date changed from October 4, 2026 to October 11, 2026, so this will be saved as a new service. The October 4 service stays in the archive.",
    );
    await first.user.click(button);
    expect(await screen.findByText(SAVED_MESSAGE)).toBeInTheDocument();
    expect(serviceRequests(first.api, "PUT")).toEqual([]);
    expect(serviceRequests(first.api, "POST")).toHaveLength(1);
    await waitFor(() => expect(stored().editing?.service_id).toBe(OTHER_ID));
    expect(within(card).getByRole("button", { name: "Save changes" })).toBeInTheDocument();
    first.unmount();
    window.localStorage.clear();

    const second = renderReview(opened({ service_date_iso: null, service_date: "" }), {
      "POST /services": () => ({ status: 201, body: savedService({ id: OTHER_ID, saved_at: SECOND_SAVE }) }),
    });
    const undated = await archiveCard();
    expect(screen.getByText(/This saved service has no date\. It's set to Sunday, October 4, 2026 for now\./)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Check the date" })).toHaveAttribute("href", "/builder/readings");
    expect(within(undated).getByRole("button", { name: "Save as new service" })).toHaveAccessibleDescription(
      "The saved service has no date, so this will be saved as a new service on October 4, 2026. The undated service stays in the archive.",
    );
    await second.user.click(within(undated).getByRole("button", { name: "Save as new service" }));
    expect(await screen.findByText("You're editing the saved service for October 4, 2026. Changes stay on this device until you save.")).toBeInTheDocument();
    expect(screen.queryByText(/has no date/)).toBeNull();
  });

  it("on a conflict, reloads their version or saves mine as a new service", async () => {
    const { api, user } = renderReview(
      opened({ saved_at: FIRST_SAVE }),
      {
        [`PUT /services/${SERVICE_ID}`]: fakeError(409, "conflict", CONFLICT_MESSAGE, { details: { current_saved_at: SECOND_SAVE } }),
        [`GET /services/${SERVICE_ID}`]: savedService({ occasion: "Their occasion", saved_at: SECOND_SAVE }),
        "POST /services": () => ({ status: 201, body: savedService({ id: OTHER_ID, saved_at: "2026-10-02T15:10:00+00:00" }) }),
      },
      <Probe edit={(draft) => editOccasion(draft, "My occasion")} />,
    );
    const card = await archiveCard();
    await user.click(within(card).getByRole("button", { name: "Save changes" }));
    const dialog = await screen.findByRole("alertdialog", { name: CONFLICT_TITLE });
    expect(dialog).toHaveAccessibleDescription(`${CONFLICT_MESSAGE} ${RELOAD_REPLACES}`);
    expect(within(dialog).getByRole("button", { name: "Save mine as a new service" })).toHaveClass("bg-primary"); // the primary choice
    expect(within(dialog).getByRole("button", { name: "Reload their version" })).toHaveClass("bg-background"); // outline
    await user.click(within(dialog).getByRole("button", { name: "Reload their version" }));
    expect(await screen.findByText(LOADED_LATEST)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(stored()).toMatchObject({ readings: { occasion: "Their occasion" }, editing: { saved_at: SECOND_SAVE } });
    expect(within(card).getByText(`Saved to the archive · ${formatSavedAt(SECOND_SAVE)}`)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Probe edit" })); // and they save again meanwhile
    await user.click(within(card).getByRole("button", { name: "Save changes" }));
    const again = await screen.findByRole("alertdialog", { name: CONFLICT_TITLE });
    await user.click(within(again).getByRole("button", { name: "Save mine as a new service" }));
    expect(await screen.findByText(SAVED_MESSAGE)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(serviceRequests(api, "POST")).toHaveLength(1);
    await waitFor(() => expect(stored().editing?.service_id).toBe(OTHER_ID));
  });

  it("after a save whose answer was lost, a 409 is that save when the archive's copy is what was sent", async () => {
    const errorToast = vi.spyOn(toast, "error");
    let puts = 0;
    const { api, user } = renderReview(editOccasion(opened({ saved_at: FIRST_SAVE }), "Harvest Home"), {
      [`PUT /services/${SERVICE_ID}`]: () => {
        puts += 1;
        if (puts === 1) throw new TypeError("Failed to fetch"); // the server saved it; the answer never came
        return fakeError(409, "conflict", CONFLICT_MESSAGE, { details: { current_saved_at: SECOND_SAVE } });
      },
      [`GET /services/${SERVICE_ID}`]: savedService({ occasion: "Harvest Home", saved_at: SECOND_SAVE }),
    });
    const card = await archiveCard();
    await user.click(within(card).getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(errorToast).toHaveBeenCalledTimes(1));
    await user.click(within(card).getByRole("button", { name: "Save changes" }));
    expect(await screen.findByText(SAVED_MESSAGE)).toBeInTheDocument();
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(within(card).getByText(`Saved to the archive · ${formatSavedAt(SECOND_SAVE)}`)).toBeInTheDocument();
    await waitFor(() => expect(stored().editing).toEqual({ service_id: SERVICE_ID, saved_at: SECOND_SAVE, date_iso: "2026-10-04" }));
    expect(serviceRequests(api, "PUT").map((r) => r.headers["if-match"])).toEqual([FIRST_SAVE, FIRST_SAVE]);
    expect(serviceRequests(api, "POST")).toEqual([]);
  });

  it("a lost answer's 409 is still that save when the server found a hymn by its title and the body cut a long text", async () => {
    const long = "Sing to the Lord. ".repeat(600); // 10,800 characters: the body cuts a custom element's text to 10,000
    let d = opened({ saved_at: FIRST_SAVE });
    d = { ...d, liturgy: { ...d.liturgy, custom_elements: [{ ...d.liturgy.custom_elements[0], text: long }] } };
    d = setSlot(d, "closing", { hymn_id: null, title: "old  favorite", number: null, hymnal: "PH1990" });
    let puts = 0;
    const { api, user } = renderReview(d, {
      [`PUT /services/${SERVICE_ID}`]: () => {
        puts += 1;
        if (puts === 1) throw new TypeError("Failed to fetch");
        return fakeError(409, "conflict", CONFLICT_MESSAGE, { details: { current_saved_at: SECOND_SAVE } });
      },
      // As the archive keeps it: the closing hymn found in the church's hymnal by title, the text cut and trimmed.
      [`GET /services/${SERVICE_ID}`]: savedService({
        saved_at: SECOND_SAVE,
        hymns: {
          ...savedService().hymns,
          closing: { hymn_id: hymnId(9), title: "Old Favorite", number: 12, hymnal: "PH1990", in_hymnal: true },
        },
        custom_elements: [{ label: "Anthem", text: long.slice(0, 10_000).trim(), insert_after: "sermon" }],
      }),
    });
    const card = await archiveCard();
    await user.click(within(card).getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(puts).toBe(1));
    await user.click(await within(card).findByRole("button", { name: "Save changes" }));
    expect(await screen.findByText(SAVED_MESSAGE)).toBeInTheDocument();
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(serviceRequests(api, "PUT")).toHaveLength(2);
    expect((serviceRequests(api, "PUT")[1].body as { custom_elements: { text: string }[] }).custom_elements[0].text).toHaveLength(10_000);
    await waitFor(() => expect(stored().editing?.saved_at).toBe(SECOND_SAVE));
  });

  it("saves as a new service, and says so, when the saved copy was deleted", async () => {
    const { api, user } = renderReview(opened(), {
      [`PUT /services/${SERVICE_ID}`]: fakeError(404, "not_found", "That service is no longer in the archive."),
      "POST /services": () => ({ status: 201, body: savedService({ id: OTHER_ID, saved_at: SECOND_SAVE }) }),
    });
    const card = await archiveCard();
    await user.click(within(card).getByRole("button", { name: "Save changes" }));
    expect(await screen.findByText(SAVED_AFTER_DELETE_MESSAGE)).toBeInTheDocument();
    const [post] = serviceRequests(api, "POST");
    expect(post.headers["idempotency-key"]).toBeTruthy();
    await waitFor(() => expect(stored().editing?.service_id).toBe(OTHER_ID));
  });

  it("offers Go to Hymns for a hymn the church no longer has, and the corrected save uses a new key", async () => {
    const [holy, praise] = gg2013();
    const failure = fakeError(404, "not_found", HYMN_GONE, { details: { field: "hymns.opening.hymn_id" } });
    let posts = 0;
    const { api, user } = renderReview(
      setSlot(testDraft(), "opening", pickFromHymn(holy)),
      {
        "POST /services": () => {
          posts += 1;
          return posts === 1 ? failure : { status: 201, body: savedService({ saved_at: FIRST_SAVE }) };
        },
      },
      <Probe edit={(draft) => setSlot(draft, "opening", pickFromHymn(praise))} />,
    );
    const card = await archiveCard();
    await user.click(within(card).getByRole("button", { name: "Save to archive" }));
    expect(await screen.findByText(HYMN_GONE)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Go to Hymns" }));
    expect(testRouter.push).toHaveBeenCalledWith("/builder/hymns");
    await user.click(screen.getByRole("button", { name: "Probe edit" }));
    await user.click(within(card).getByRole("button", { name: "Save to archive" }));
    expect(await screen.findByText(SAVED_MESSAGE)).toBeInTheDocument();
    const [first, second] = serviceRequests(api, "POST");
    expect(second.headers["idempotency-key"]).not.toBe(first.headers["idempotency-key"]);
  });

  it("leaves a blank bulletin out of a POST and always sends it in a PUT (2b-2 build review M1)", async () => {
    // A POST whose answer was lost before 2b-2 sent no bulletin: its retry now keeps the same body, so no duplicate.
    const { api, user } = renderReview(
      editOccasion(testDraft(), "Harvest"),
      {
        "POST /services": () => ({ status: 201, body: savedService({ occasion: "Harvest", saved_at: FIRST_SAVE }) }),
        [`PUT /services/${SERVICE_ID}`]: () => savedService({ occasion: "Harvest Home", saved_at: SECOND_SAVE }),
      },
      <Probe edit={(draft) => editOccasion(draft, "Harvest Home")} />,
    );
    const card = await archiveCard();
    await user.click(within(card).getByRole("button", { name: "Save to archive" }));
    expect(await screen.findByText(SAVED_MESSAGE)).toBeInTheDocument();
    const [post] = serviceRequests(api, "POST");
    expect(post.body).toMatchObject({ occasion: "Harvest" });
    expect(post.body).not.toHaveProperty("bulletin");
    await user.click(screen.getByRole("button", { name: "Probe edit" }));
    await user.click(within(card).getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(within(card).getByText(`Saved to the archive · ${formatSavedAt(SECOND_SAVE)}`)).toBeInTheDocument());
    const [put] = serviceRequests(api, "PUT");
    // Clearing every field clears the saved ones, the picture included (PR 3b: null says "no picture").
    expect(put.body).toHaveProperty("bulletin", { ...emptyServiceBulletin(), cover_image_id: null });
  });

  it("sends a filled-in bulletin in a POST (2b-2 build review M1)", async () => {
    const { api, user } = renderReview(setAnnouncement(editOccasion(testDraft(), "Harvest"), "coffee_hour", "The Sample family"), {
      "POST /services": () => ({ status: 201, body: savedService({ occasion: "Harvest", saved_at: FIRST_SAVE }) }),
    });
    const card = await archiveCard();
    await user.click(within(card).getByRole("button", { name: "Save to archive" }));
    expect(await screen.findByText(SAVED_MESSAGE)).toBeInTheDocument();
    const [post] = serviceRequests(api, "POST");
    expect(post.body).toMatchObject({ bulletin: { announcements: { coffee_hour: "The Sample family" } } });
    expect((post.body as { bulletin: object }).bulletin).not.toHaveProperty("cover_image_id"); // no picture (PR 3b)
  });

  it("keeps the key for an identical retry after an unknown outcome, replaces it after an edit, and retries a mismatch once", async () => {
    const errorToast = vi.spyOn(toast, "error");
    let posts = 0;
    const { api, user } = renderReview(
      editOccasion(testDraft(), "Harvest"),
      {
        "POST /services": () => {
          posts += 1;
          if (posts <= 2) throw new TypeError("Failed to fetch");
          if (posts === 3) return fakeError(422, "idempotency_mismatch", "This request was already sent with different details.");
          return { status: 201, body: savedService({ saved_at: FIRST_SAVE }) };
        },
      },
      <Probe edit={(draft) => editOccasion(draft, "Harvest Home")} />,
    );
    const card = await archiveCard();
    const save = () => user.click(within(card).getByRole("button", { name: "Save to archive" }));
    await save();
    await waitFor(() => expect(errorToast).toHaveBeenCalledTimes(1));
    await save(); // unchanged: the same key, so a stored first answer would be replayed
    await waitFor(() => expect(errorToast).toHaveBeenCalledTimes(2));
    await user.click(screen.getByRole("button", { name: "Probe edit" }));
    await save(); // changed: a new key; the mismatch is retried once with another
    expect(await screen.findByText(SAVED_MESSAGE)).toBeInTheDocument();
    const keys = serviceRequests(api, "POST").map((r) => r.headers["idempotency-key"]);
    expect(keys).toHaveLength(4);
    expect(keys[1]).toBe(keys[0]);
    expect(new Set(keys.slice(1)).size).toBe(3);
    expect(errorToast).toHaveBeenCalledTimes(2); // no message for the mismatch
  });

  it("Start a new service asks first when the draft has unsaved work, and not when it is saved", async () => {
    const first = renderReview(editOccasion(testDraft(), "Harvest"));
    const card = await archiveCard();
    await first.user.click(within(card).getByRole("button", { name: "Start a new service" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Start a new service?" });
    await first.user.click(within(dialog).getByRole("button", { name: "Start new service" }));
    expect(testRouter.push).toHaveBeenCalledWith("/builder/readings");
    expect(stored().readings.occasion).toBe("");
    first.unmount();
    window.localStorage.clear();
    testRouter.push.mockClear();

    const second = renderReview(opened());
    const savedCard = await archiveCard();
    await second.user.click(within(savedCard).getByRole("button", { name: "Start a new service" }));
    expect(testRouter.push).toHaveBeenCalledWith("/builder/readings");
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(stored().editing).toBeNull();
  });

  it("after a download, says that saving records the hymns, until the service is saved", async () => {
    const { user } = renderReview(testDraft(), {
      "POST /documents": () => docx(),
      "POST /services": () => ({ status: 201, body: savedService({ saved_at: FIRST_SAVE }) }),
    });
    const documents = await documentsCard();
    expect(within(documents).queryByText(SAVE_HINT)).toBeNull();
    await user.click(within(documents).getByRole("button", { name: "Download bulletin copy" }));
    expect(await within(documents).findByText(SAVE_HINT)).toBeInTheDocument();
    await user.click(within(await archiveCard()).getByRole("button", { name: "Save to archive" }));
    await waitFor(() => expect(within(documents).queryByText(SAVE_HINT)).toBeNull());
  });
});

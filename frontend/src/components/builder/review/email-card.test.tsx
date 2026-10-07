/**
 * Review → Email the bulletin (slice 5b spec, UX "Email the bulletin card",
 * "Email dialog", "Send outcomes", flow B; amended 2026-10-06; slice 5b-2).
 * The step renders inside the builder layout with a Toaster, as in
 * review-send-step.test.tsx. The clock is fixed at Tuesday, September 29,
 * 2026, so a fresh draft is dated Sunday, October 4, 2026. Leaving for
 * Google is `browser.assign`, spied.
 */
import { screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import ReviewStepPage from "@/app/(signed-in)/(church)/builder/review/page";
import { Toaster } from "@/components/ui/sonner";
import type { Church } from "@/lib/api/types";
import { draftKey } from "@/lib/draft/schema";
import { emailPrefsKey, uncertainSendKey, writeUncertainSend } from "@/lib/email";
import { browser, GMAIL_RETURN_KEY, REOPEN_EMAIL_KEY } from "@/lib/gmail";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import {
  bulletinSettings,
  church,
  churchProfile,
  contact,
  contactList,
  DRAFT_NOW,
  gmailConnection,
  gmailDisconnected,
  hymnals,
  hymnListRoute,
  lectionaryRoute,
  liturgyConfig,
  me,
  previousBulletin,
  serviceBulletin,
  testDraft,
  translations,
  USER_ID,
} from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { BCC_NOTE, CHOOSE_ATTACHMENT, CHOOSE_RECIPIENT, CONNECTION_LOST, CONTACTS_ERROR, INVALID_CONTACT, NO_CONTACTS, TOO_MANY } from "./email-dialog";
import { EMAIL_CONNECT, EMAIL_NEEDS_DATE, EMAIL_NOT_CONFIGURED, EMAIL_STATUS_ERROR } from "./email-card";

const GRACE = church();
const PREFS = emailPrefsKey(USER_ID, GRACE.id);
const MARY = contact();
const OFFICE = contact({ id: "6c0b5e1a-1d2b-4c3d-8e4f-5a6b7c8d9e02", name: null, email: "office@example.org" });
const BROKEN = contact({ id: "6c0b5e1a-1d2b-4c3d-8e4f-5a6b7c8d9e03", name: "Two at once", email: "a@example.org, b@example.org", email_valid: false });
const GOOGLE_URL = "https://accounts.google.com/o/oauth2/v2/auth?state=s1";
const SENT = { sent: true, recipient_count: 2 };
let assign: ReturnType<typeof vi.spyOn>;

function renderReview(routes: Record<string, FakeHandler> = {}, { draft = testDraft(), role = "admin" as Church["role"] } = {}) {
  window.localStorage.setItem(draftKey(USER_ID, GRACE.id), JSON.stringify(draft));
  const active = church({ role });
  const api = installFakeApi({
    "GET /church": churchProfile({ role }),
    "GET /lectionary/readings": lectionaryRoute(),
    "GET /translations": translations(),
    "GET /hymnals": hymnals(),
    "GET /hymns": hymnListRoute(),
    "GET /liturgy/config": liturgyConfig(),
    "GET /church/bulletin-settings": bulletinSettings(),
    "GET /services/previous-bulletin": previousBulletin(),
    "GET /gmail-connection": gmailConnection(),
    "GET /contacts": contactList([MARY, OFFICE, BROKEN]),
    ...routes,
  });
  const view = renderWithProviders(
    <>
      <BuilderLayout>
        <ReviewStepPage />
      </BuilderLayout>
      <Toaster />
    </>,
    { me: me({ churches: [active] }), church: active, path: "/builder/review" },
  );
  return { ...view, api };
}

async function emailCard() {
  return screen.findByRole("region", { name: "Email the bulletin" });
}

/** Opens the dialog once the card knows the connection (while it loads, its button is disabled). */
async function openDialog(user: ReturnType<typeof renderReview>["user"]) {
  const card = await emailCard();
  await within(card).findByText("Sends from pat@example.com.");
  await user.click(within(card).getByRole("button", { name: "Email bulletin…" }));
  const dialog = await screen.findByRole("dialog", { name: "Email the bulletin" });
  await within(dialog).findByRole("checkbox", { name: /Mary Jones/ });
  return dialog;
}

function sends(api: { requests: RecordedRequest[] }) {
  return api.requests.filter((r) => r.method === "POST" && r.path === "/bulletin-emails");
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
  assign = vi.spyOn(browser, "assign").mockImplementation(() => {});
});

afterEach(() => {
  toast.dismiss();
  vi.useRealTimers();
});

describe("Review → Email the bulletin: the card (slice 5b-2)", () => {
  it("says when emailing is not set up here, with no button", async () => {
    renderReview({ "GET /gmail-connection": gmailConnection({ configured: false, connected: false, google_email: null }) });
    const card = await emailCard();
    expect(await within(card).findByText(EMAIL_NOT_CONFIGURED)).toBeInTheDocument();
    expect(within(card).queryByRole("button")).toBeNull();
  });

  it("connects Gmail from Review, to come back here and reopen the dialog", async () => {
    const { user } = renderReview({
      "GET /gmail-connection": gmailDisconnected(),
      "POST /gmail-connection/auth-url": { auth_url: GOOGLE_URL },
    });
    const card = await emailCard();
    expect(await within(card).findByText(EMAIL_CONNECT)).toBeInTheDocument();
    await user.click(within(card).getByRole("button", { name: "Connect Gmail" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith(GOOGLE_URL));
    expect(window.sessionStorage.getItem(GMAIL_RETURN_KEY)).toBe("/builder/review");
    expect(JSON.parse(window.sessionStorage.getItem(REOPEN_EMAIL_KEY) ?? "null")).toEqual({ church_id: GRACE.id });
  });

  it("shows a failed check with Retry", async () => {
    let fail = true;
    const { user } = renderReview({
      "GET /gmail-connection": () => (fail ? fakeError(500, "internal_error", "Something went wrong.") : gmailConnection()),
    });
    const card = await emailCard();
    expect(await within(card).findByText(EMAIL_STATUS_ERROR)).toBeInTheDocument();
    fail = false;
    await user.click(within(card).getByRole("button", { name: "Retry" }));
    expect(await within(card).findByText("Sends from pat@example.com.")).toBeInTheDocument();
  });

  it("needs a service date first, and says so", async () => {
    renderReview({}, { draft: testDraft((d) => ({ ...d, readings: { ...d.readings, date_iso: "" } })) });
    const card = await emailCard();
    expect(await within(card).findByText(EMAIL_NEEDS_DATE)).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Email bulletin…" })).toBeDisabled();
  });
});

describe("Review → Email the bulletin: the dialog (slice 5b-2)", () => {
  it("shows the contacts, the subject, the attachments and the prefilled message, and counts each person once", async () => {
    const { user, api } = renderReview();
    const dialog = await openDialog(user);
    expect(within(dialog).getByText("pat@example.com")).toBeInTheDocument();
    const broken = within(dialog).getByRole("checkbox", { name: /Two at once/ });
    expect(broken).toBeDisabled();
    expect(within(dialog).getByText(INVALID_CONTACT)).toBeInTheDocument();
    expect(within(dialog).getByRole("checkbox", { name: "office@example.org" })).not.toBeChecked();
    expect(within(dialog).getByText("Worship service for October 4, 2026")).toBeInTheDocument();
    expect(within(dialog).getByRole("checkbox", { name: /Bulletin copy \(Word\)/ })).toBeChecked();
    expect(within(dialog).getByRole("checkbox", { name: /Printed bulletin \(PDF\)/ })).not.toBeChecked();
    expect(within(dialog).getByText("worship_October_04_2026.docx")).toBeInTheDocument();
    expect(within(dialog).getByText("printed_bulletin_October_04_2026.pdf")).toBeInTheDocument();
    const message = within(dialog).getByRole("textbox", { name: "Message" });
    expect(message).toHaveValue("Hi! Here's the worship bulletin for this Sunday.");
    expect(message).toHaveAttribute("maxLength", "5000");
    expect(within(dialog).getByRole("button", { name: "Send" })).toBeDisabled();
    expect(within(dialog).getByText(CHOOSE_RECIPIENT)).toBeInTheDocument();

    await user.click(within(dialog).getByRole("checkbox", { name: /Mary Jones/ }));
    expect(within(dialog).getByRole("button", { name: "Send to 1 person" })).toBeEnabled();
    expect(within(dialog).queryByText(BCC_NOTE)).toBeNull();
    await user.type(within(dialog).getByRole("textbox", { name: "Other addresses" }), "MARY@example.org, organist@example.org");
    expect(within(dialog).getByRole("button", { name: "Send to 2 people" })).toBeEnabled();
    expect(within(dialog).getByText(BCC_NOTE)).toBeInTheDocument();

    await user.click(within(dialog).getByRole("checkbox", { name: /Bulletin copy \(Word\)/ }));
    expect(within(dialog).getByText(CHOOSE_ATTACHMENT)).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Send to 2 people" })).toBeDisabled();
    await user.click(within(dialog).getByRole("checkbox", { name: /Printed bulletin \(PDF\)/ }));
    expect(JSON.parse(window.localStorage.getItem(PREFS) ?? "null").attachments).toEqual(["pdf"]);
    expect(sends(api)).toEqual([]);
  });

  it("is a bottom sheet on a phone whose one scroll area holds Send, so the keyboard never hides it", async () => {
    const { user } = renderReview();
    const dialog = await openDialog(user);
    // Below md the sheet itself scrolls (5b-1's contact editor); from md the fields scroll above the buttons.
    expect(dialog.className).toContain("max-md:overflow-y-auto");
    expect(dialog.className).toContain("max-md:max-h-[85dvh]");
    const send = within(dialog).getByRole("button", { name: "Send" });
    const between: string[] = [];
    for (let el = send.parentElement; el !== null && el !== dialog; el = el.parentElement) between.push(el.className);
    expect(between.length).toBeGreaterThan(0);
    for (const className of between) {
      expect(className.split(/\s+/)).not.toContain("overflow-y-auto"); // nothing between Send and the sheet scrolls on a phone
      expect(className.split(/\s+/)).not.toContain("min-h-0");
    }
    expect(between.some((className) => className.split(/\s+/).includes("md:overflow-y-auto"))).toBe(false);
    const fields = within(dialog).getByRole("textbox", { name: "Message" }).closest("div.content-start");
    expect(fields?.className.split(/\s+/)).toContain("md:overflow-y-auto");
    expect(fields?.contains(send)).toBe(false);
  });

  it("allows at most 50 people", async () => {
    const { user } = renderReview();
    const dialog = await openDialog(user);
    const many = Array.from({ length: 51 }, (_, i) => `p${i}@example.org`).join(", ");
    await user.click(within(dialog).getByRole("textbox", { name: "Other addresses" }));
    await user.paste(many);
    expect(within(dialog).getByText(TOO_MANY)).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Send to 51 people" })).toBeDisabled();
  });

  it("sends the service as it is now with a key, toasts, remembers the contacts and resets the message", async () => {
    window.localStorage.setItem(PREFS, JSON.stringify({ version: 1, contact_ids: [MARY.id, "gone"], attachments: ["docx", "pdf"] }));
    const { user, api } = renderReview({ "POST /bulletin-emails": SENT });
    const dialog = await openDialog(user);
    expect(within(dialog).getByRole("checkbox", { name: /Mary Jones/ })).toBeChecked();
    await user.click(within(dialog).getByRole("checkbox", { name: "office@example.org" }));
    const message = within(dialog).getByRole("textbox", { name: "Message" });
    await user.clear(message);
    await user.type(message, "See you Sunday.");
    await user.click(within(dialog).getByRole("button", { name: "Send to 2 people" }));
    expect(await screen.findByText("Email sent to 2 people.")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).toBeNull();
    const [request] = sends(api);
    expect(request.headers["x-church-id"]).toBe(GRACE.id);
    expect(request.headers["idempotency-key"]).toMatch(/^[0-9a-f-]{36}$/);
    expect(request.body).toMatchObject({
      contact_ids: [MARY.id, OFFICE.id],
      additional_emails: [],
      message: "See you Sunday.",
      attachments: ["docx", "pdf"],
      service: { service_date_iso: "2026-10-04" },
    });
    expect(JSON.parse(window.localStorage.getItem(PREFS) ?? "null")).toEqual({
      version: 1,
      contact_ids: [MARY.id, OFFICE.id],
      attachments: ["docx", "pdf"],
    });
    await user.click(within(await emailCard()).getByRole("button", { name: "Email bulletin…" }));
    expect(within(await screen.findByRole("dialog")).getByRole("textbox", { name: "Message" })).toHaveValue(
      "Hi! Here's the worship bulletin for this Sunday.",
    );
  });

  it("shows each field's refusal where it belongs and focuses the first", async () => {
    let answer = fakeError(422, "invalid_request", "The request was not valid.", {
      fields: { "additional_emails.1": "Not a valid value.", message: "Too long (max 5000 characters)." },
    });
    const { user } = renderReview({ "POST /bulletin-emails": () => answer });
    const dialog = await openDialog(user);
    const other = within(dialog).getByRole("textbox", { name: "Other addresses" });
    await user.type(other, "a@example.org, b@example.org");
    await user.click(within(dialog).getByRole("button", { name: "Send to 2 people" }));
    expect(await within(dialog).findByText("Not a valid value.")).toBeInTheDocument();
    await waitFor(() => expect(other).toHaveFocus());
    expect(other).toHaveAttribute("aria-invalid", "true");
    expect(within(dialog).getByText("Too long (max 5000 characters).")).toBeInTheDocument();
    answer = fakeError(422, "invalid_request", "Give each custom element a label.", {
      fields: { "custom_elements.0.label": "Give each custom element a label." },
    });
    await user.click(within(dialog).getByRole("button", { name: "Send to 2 people" }));
    expect(await within(dialog).findByText("Give each custom element a label.")).toBeInTheDocument();
    expect(document.querySelectorAll("[data-sonner-toast]")).toHaveLength(0);
  });

  it("refreshes the contacts when one is gone, and links to Hymns for a hymn that is gone", async () => {
    let answer = fakeError(404, "not_found", "One of the selected contacts no longer exists. Refresh the list and try again.", {
      details: { field: "contact_ids" },
    });
    const { user, api } = renderReview({ "POST /bulletin-emails": () => answer });
    const dialog = await openDialog(user);
    await user.click(within(dialog).getByRole("checkbox", { name: /Mary Jones/ }));
    await user.click(within(dialog).getByRole("button", { name: "Send to 1 person" }));
    expect(await within(dialog).findByText("One of the selected contacts no longer exists. Refresh the list and try again.")).toBeInTheDocument();
    await waitFor(() => expect(api.requests.filter((r) => r.path === "/contacts")).toHaveLength(2));
    answer = fakeError(404, "not_found", "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step.", {
      details: { field: "hymns.response.hymn_id" },
    });
    await user.click(within(dialog).getByRole("button", { name: "Send to 1 person" }));
    expect(await within(dialog).findByRole("link", { name: "Go to Hymns" })).toHaveAttribute("href", "/builder/hymns");
    expect(api.requests.filter((r) => r.path === "/contacts")).toHaveLength(2);
  });

  it("offers Connect Gmail when the connection is gone, keeping the form for the way back", async () => {
    const { user, api } = renderReview({
      "POST /bulletin-emails": fakeError(409, "gmail_not_connected", "Connect your Gmail first, then try again."),
      "POST /gmail-connection/auth-url": { auth_url: GOOGLE_URL },
    });
    const dialog = await openDialog(user);
    await user.click(within(dialog).getByRole("checkbox", { name: /Mary Jones/ }));
    await user.type(within(dialog).getByRole("textbox", { name: "Other addresses" }), "organist@example.org");
    await user.click(within(dialog).getByRole("button", { name: "Send to 2 people" }));
    expect(await within(dialog).findByText("Connect your Gmail first, then try again.")).toBeInTheDocument();
    await waitFor(() => expect(api.requests.filter((r) => r.path === "/gmail-connection")).toHaveLength(2));
    await user.click(within(dialog).getByRole("button", { name: "Connect Gmail" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith(GOOGLE_URL));
    expect(JSON.parse(window.sessionStorage.getItem(REOPEN_EMAIL_KEY) ?? "null")).toEqual({
      church_id: GRACE.id,
      contact_ids: [MARY.id],
      other_addresses: "organist@example.org",
      message: "Hi! Here's the worship bulletin for this Sunday.",
      attachments: ["docx"],
    });
  });

  it("after an uncertain send turns plain Send off, even after a reload, and only Send again anyway sends, with a new key", async () => {
    const UNCERTAIN =
      "Gmail didn't confirm the email, so it may already have been sent. Check your Gmail Sent folder before sending again.";
    const first = renderReview({
      "POST /bulletin-emails": fakeError(504, "upstream_timeout", UNCERTAIN, { details: { send_uncertain: true } }),
    });
    const dialog = await openDialog(first.user);
    await first.user.click(within(dialog).getByRole("checkbox", { name: /Mary Jones/ }));
    await first.user.click(within(dialog).getByRole("button", { name: "Send to 1 person" }));
    expect(await within(dialog).findByText(UNCERTAIN)).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Send to 1 person" })).toBeDisabled();
    expect(sends(first.api)).toHaveLength(1);
    const firstKey = sends(first.api)[0].headers["idempotency-key"];
    first.unmount(); // leaving Review, or a reload: this tab still knows

    const again = renderReview({ "POST /bulletin-emails": SENT });
    const reopened = await openDialog(again.user);
    expect(within(reopened).getByText(UNCERTAIN)).toBeInTheDocument();
    await again.user.click(within(reopened).getByRole("checkbox", { name: /Mary Jones/ }));
    expect(within(reopened).getByRole("button", { name: "Send to 1 person" })).toBeDisabled();
    await again.user.click(within(reopened).getByRole("button", { name: "Send again anyway" }));
    expect(await screen.findByText("Email sent to 2 people.")).toBeInTheDocument();
    expect(sends(again.api).map((r) => r.headers["idempotency-key"])).not.toContain(firstKey);
    expect(window.sessionStorage.getItem(uncertainSendKey(USER_ID, GRACE.id))).toBeNull();
  });

  it("after a lost connection says the email may have gone, and only Send again anyway sends", async () => {
    let first = true;
    const { user, api } = renderReview({
      "POST /bulletin-emails": () => {
        if (first) {
          first = false;
          throw new TypeError("Failed to fetch");
        }
        return SENT;
      },
    });
    const dialog = await openDialog(user);
    await user.click(within(dialog).getByRole("checkbox", { name: /Mary Jones/ }));
    await user.click(within(dialog).getByRole("button", { name: "Send to 1 person" }));
    expect(await within(dialog).findByText(CONNECTION_LOST)).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Send to 1 person" })).toBeDisabled();
    await user.click(within(dialog).getByRole("button", { name: "Send again anyway" }));
    expect(await screen.findByText("Email sent to 2 people.")).toBeInTheDocument();
    const [one, two] = sends(api).map((r) => r.headers["idempotency-key"]);
    expect(two).not.toBe(one);
  });

  it("remembers a send as possibly sent before it leaves, so leaving mid-send keeps plain Send off on the way back", async () => {
    const first = renderReview({ "POST /bulletin-emails": () => new Promise(() => {}) });
    const dialog = await openDialog(first.user);
    await first.user.click(within(dialog).getByRole("checkbox", { name: /Mary Jones/ }));
    await first.user.click(within(dialog).getByRole("button", { name: "Send to 1 person" }));
    await waitFor(() => expect(sends(first.api)).toHaveLength(1));
    expect(window.sessionStorage.getItem(uncertainSendKey(USER_ID, GRACE.id))).not.toBeNull();
    expect(within(dialog).queryByText(CONNECTION_LOST)).toBeNull(); // nothing flashes while it is sending
    first.unmount(); // Back or a reload during "Still working…": the request's answer never reaches the dialog
    expect(window.sessionStorage.getItem(uncertainSendKey(USER_ID, GRACE.id))).not.toBeNull();

    const back = renderReview({ "POST /bulletin-emails": SENT });
    const reopened = await openDialog(back.user);
    expect(within(reopened).getByText(CONNECTION_LOST)).toBeInTheDocument();
    await back.user.click(within(reopened).getByRole("checkbox", { name: /Mary Jones/ }));
    expect(within(reopened).getByRole("button", { name: "Send to 1 person" })).toBeDisabled();
    expect(sends(back.api)).toEqual([]);
  });

  it("after a reload reads the stored send, keeps plain Send off, and Send again anyway sends", async () => {
    writeUncertainSend(USER_ID, GRACE.id, CONNECTION_LOST, "2026-10-04");
    const { user, api } = renderReview({ "POST /bulletin-emails": SENT });
    const dialog = await openDialog(user);
    expect(within(dialog).getByText(CONNECTION_LOST)).toBeInTheDocument();
    await user.click(within(dialog).getByRole("checkbox", { name: /Mary Jones/ }));
    const plain = within(dialog).getByRole("button", { name: "Send to 1 person" });
    expect(plain).toBeDisabled();
    await user.click(plain);
    expect(sends(api)).toEqual([]);
    await user.click(within(dialog).getByRole("button", { name: "Send again anyway" }));
    expect(await screen.findByText("Email sent to 2 people.")).toBeInTheDocument();
    expect(sends(api)).toHaveLength(1);
    expect(window.sessionStorage.getItem(uncertainSendKey(USER_ID, GRACE.id))).toBeNull();
  });

  it("ignores a possibly-sent mark left by another service date", async () => {
    writeUncertainSend(USER_ID, GRACE.id, CONNECTION_LOST, "2026-09-27");
    const { user, api } = renderReview({ "POST /bulletin-emails": SENT });
    const dialog = await openDialog(user);
    expect(within(dialog).queryByText(CONNECTION_LOST)).toBeNull();
    await user.click(within(dialog).getByRole("checkbox", { name: /Mary Jones/ }));
    await user.click(within(dialog).getByRole("button", { name: "Send to 1 person" }));
    expect(await screen.findByText("Email sent to 2 people.")).toBeInTheDocument();
    expect(sends(api)).toHaveLength(1);
  });

  it("forgets the possibly-sent mark on a definite refusal, and keeps it when the answer is not definite", async () => {
    let answer = fakeError(409, "gmail_not_connected", "Connect your Gmail first, then try again.");
    const { user } = renderReview({ "POST /bulletin-emails": () => answer });
    const dialog = await openDialog(user);
    await user.click(within(dialog).getByRole("checkbox", { name: /Mary Jones/ }));
    await user.click(within(dialog).getByRole("button", { name: "Send to 1 person" }));
    expect(await within(dialog).findByText("Connect your Gmail first, then try again.")).toBeInTheDocument();
    expect(window.sessionStorage.getItem(uncertainSendKey(USER_ID, GRACE.id))).toBeNull();
    answer = fakeError(500, "internal_error", "Something went wrong.");
    await user.click(within(dialog).getByRole("button", { name: "Send to 1 person" }));
    await waitFor(() => expect(within(dialog).getByRole("button", { name: "Send to 1 person" })).toBeEnabled());
    expect(window.sessionStorage.getItem(uncertainSendKey(USER_ID, GRACE.id))).not.toBeNull();
  });

  it("brings a problem at the top into view by focusing it, and a To problem by focusing the first contact that can be chosen", async () => {
    let answer = fakeError(409, "gmail_not_connected", "Connect your Gmail first, then try again.");
    const { user } = renderReview({
      "GET /contacts": contactList([BROKEN, MARY, OFFICE]),
      "POST /bulletin-emails": () => answer,
    });
    const dialog = await openDialog(user);
    await user.click(within(dialog).getByRole("checkbox", { name: /Mary Jones/ }));
    await user.click(within(dialog).getByRole("button", { name: "Send to 1 person" }));
    const top = await within(dialog).findByText("Connect your Gmail first, then try again.");
    const alert = top.closest("[role=alert]");
    await waitFor(() => expect(document.activeElement).toBe(alert));
    expect(alert).toHaveAttribute("tabindex", "-1");

    answer = fakeError(404, "not_found", "One of the selected contacts no longer exists. Refresh the list and try again.", {
      details: { field: "contact_ids" },
    });
    await user.click(within(dialog).getByRole("button", { name: "Send to 1 person" }));
    expect(await within(dialog).findByText("One of the selected contacts no longer exists. Refresh the list and try again.")).toBeInTheDocument();
    await waitFor(() => expect(document.activeElement).toBe(within(dialog).getByRole("checkbox", { name: /Mary Jones/ })));
  });

  it("offers Reconnect Gmail when Google dropped the grant", async () => {
    const { user } = renderReview({
      "POST /bulletin-emails": fakeError(502, "gmail_send_failed",
        "Your Gmail connection has expired or was removed. Reconnect Gmail and try again.",
        { details: { disconnected: true, send_uncertain: false } }),
    });
    const dialog = await openDialog(user);
    await user.click(within(dialog).getByRole("checkbox", { name: /Mary Jones/ }));
    await user.click(within(dialog).getByRole("button", { name: "Send to 1 person" }));
    expect(await within(dialog).findByText("Your Gmail connection has expired or was removed. Reconnect Gmail and try again.")).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Reconnect Gmail" })).toBeInTheDocument();
    // role="alert" announces itself; a live region around it would announce it twice (5b-2b build review M5).
    const alert = within(dialog).getByText(/has expired or was removed/).closest("[role=alert]");
    expect(alert?.closest("[aria-live]")).toBeNull();
  });

  it("with no contacts says so, links admins to Contacts, and still sends to typed addresses", async () => {
    const { user, api, unmount } = renderReview({ "GET /contacts": contactList([]), "POST /bulletin-emails": SENT });
    const card = await emailCard();
    await within(card).findByText("Sends from pat@example.com.");
    await user.click(within(card).getByRole("button", { name: "Email bulletin…" }));
    const opened = await screen.findByRole("dialog", { name: "Email the bulletin" });
    expect(await within(opened).findByText(NO_CONTACTS)).toBeInTheDocument();
    expect(within(opened).getByRole("link", { name: "Manage contacts" })).toHaveAttribute("href", "/settings/contacts");
    await user.type(within(opened).getByRole("textbox", { name: "Other addresses" }), "organist@example.org");
    await user.click(within(opened).getByRole("button", { name: "Send to 1 person" }));
    await waitFor(() => expect(sends(api)).toHaveLength(1));
    unmount();

    const member = renderReview({ "GET /contacts": fakeError(500, "internal_error", "Something went wrong.") }, { role: "member" });
    const memberCard = await emailCard();
    await within(memberCard).findByText("Sends from pat@example.com.");
    await member.user.click(within(memberCard).getByRole("button", { name: "Email bulletin…" }));
    const failing = await screen.findByRole("dialog", { name: "Email the bulletin" });
    expect(await within(failing).findByText(CONTACTS_ERROR)).toBeInTheDocument();
    expect(within(failing).getByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(within(failing).queryByRole("link", { name: "Manage contacts" })).toBeNull();
  });
});

describe("Review → Email the bulletin: back from Google (slice 5b-2, flow B)", () => {
  function reopen(value: object) {
    window.sessionStorage.setItem(REOPEN_EMAIL_KEY, JSON.stringify(value));
  }

  it("waits for the status, then reopens the dialog with what was in it", async () => {
    reopen({ church_id: GRACE.id, contact_ids: [OFFICE.id], other_addresses: "organist@example.org", message: "Hello", attachments: ["pdf"] });
    let release: (value: unknown) => void = () => {};
    const held = new Promise((resolve) => {
      release = resolve;
    });
    renderReview({
      "GET /gmail-connection": async () => {
        await held;
        return gmailConnection();
      },
    });
    await emailCard();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(window.sessionStorage.getItem(REOPEN_EMAIL_KEY)).not.toBeNull();
    release(undefined);
    const dialog = await screen.findByRole("dialog", { name: "Email the bulletin" });
    expect(await within(dialog).findByRole("checkbox", { name: "office@example.org" })).toBeChecked();
    expect(within(dialog).getByRole("textbox", { name: "Other addresses" })).toHaveValue("organist@example.org");
    expect(within(dialog).getByRole("textbox", { name: "Message" })).toHaveValue("Hello");
    expect(within(dialog).getByRole("checkbox", { name: /Printed bulletin \(PDF\)/ })).toBeChecked();
    expect(within(dialog).getByRole("checkbox", { name: /Bulletin copy \(Word\)/ })).not.toBeChecked();
    expect(window.sessionStorage.getItem(REOPEN_EMAIL_KEY)).toBeNull();
  });

  it("waits for last week's bulletin to be carried in, then shows the printed bulletin's notes with the PDF", async () => {
    reopen({ church_id: GRACE.id, contact_ids: [MARY.id], attachments: ["pdf"] });
    let release: (value: unknown) => void = () => {};
    const held = new Promise((resolve) => {
      release = resolve;
    });
    const lastWeek = serviceBulletin({ announcements: { ...serviceBulletin().announcements, coffee_hour: "The Smiths" } });
    renderReview({
      "GET /services/previous-bulletin": async () => {
        await held;
        return previousBulletin({ service_date_iso: "2026-09-27", bulletin: lastWeek });
      },
    });
    expect(await within(await emailCard()).findByText("Sends from pat@example.com.")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(window.sessionStorage.getItem(REOPEN_EMAIL_KEY)).not.toBeNull();
    release(undefined);
    const dialog = await screen.findByRole("dialog", { name: "Email the bulletin" });
    expect(within(dialog).getByText("From last week, not checked yet: coffee hour.")).toBeInTheDocument();
    expect(window.sessionStorage.getItem(REOPEN_EMAIL_KEY)).toBeNull();
  });

  it("forgets the request without reopening when still not connected (a cancel at Google) or for another church", async () => {
    reopen({ church_id: GRACE.id });
    const { unmount } = renderReview({ "GET /gmail-connection": gmailDisconnected() });
    expect(await within(await emailCard()).findByText(EMAIL_CONNECT)).toBeInTheDocument();
    await waitFor(() => expect(window.sessionStorage.getItem(REOPEN_EMAIL_KEY)).toBeNull());
    expect(screen.queryByRole("dialog")).toBeNull();
    unmount();

    reopen({ church_id: "22222222-2222-4222-8222-222222222222" });
    renderReview();
    expect(await within(await emailCard()).findByText("Sends from pat@example.com.")).toBeInTheDocument();
    await waitFor(() => expect(window.sessionStorage.getItem(REOPEN_EMAIL_KEY)).toBeNull());
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});

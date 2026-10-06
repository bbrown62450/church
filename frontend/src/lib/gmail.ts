/**
 * Connecting Gmail (slice 5b spec, flows A-C; slice 5b-2). Pure helpers and
 * the browser's side of the trip to Google:
 *
 * - `startGmailRedirect(authUrl, returnTo, reopen?)`: refuses any URL that is
 *   not Google's consent page; otherwise remembers where to come back to
 *   (`wsb:gmailReturnTo`, and for the email dialog what to reopen,
 *   `wsb:reopenEmailDialog`, both in sessionStorage) and leaves for Google in
 *   the same tab. The draft is already in localStorage.
 * - `readReturnTo()`: the remembered page, through `safeInternalPath`, else
 *   Settings → Account.
 * - `parseCallbackParams(search)`: what Google put on `/gmail/callback`.
 * - `connectGmailOnce(call, {code, state})`: `POST /gmail-connection` once
 *   per state, however often it is asked (React StrictMode runs the callback
 *   page's effect twice; a state is single use at the server).
 * - `gmailErrorMessage(e)`: what a failed Gmail request tells the user.
 */
import { ApiError } from "@/lib/api/client";
import { errorToastMessage } from "@/lib/api/errors";
import type { GmailConnectBody, GmailConnection } from "@/lib/api/types";
import type { ApiCall } from "@/lib/queries/client";
import { readSession, removeSession, writeSession } from "@/lib/storage";
import { safeInternalPath } from "@/lib/urls";

export const GMAIL_RETURN_KEY = "wsb:gmailReturnTo";
export const REOPEN_EMAIL_KEY = "wsb:reopenEmailDialog";
export const DEFAULT_RETURN = "/settings/account";

/** Leaving the app for Google; tests replace `assign` (jsdom cannot navigate). */
export const browser = {
  assign(url: string): void {
    window.location.assign(url);
  },
};

/** True only for Google's consent page over https. */
export function isGoogleAuthUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" && parsed.host === "accounts.google.com";
  } catch {
    return false;
  }
}

/**
 * Leave for Google's consent page, remembering `returnTo` (and `reopen`, the
 * email dialog's state, when given). False, and nothing stored, for a URL that
 * is not Google's.
 */
export function startGmailRedirect(authUrl: string, returnTo: string, reopen?: object): boolean {
  if (!isGoogleAuthUrl(authUrl)) return false;
  writeSession(GMAIL_RETURN_KEY, returnTo);
  if (reopen !== undefined) writeSession(REOPEN_EMAIL_KEY, JSON.stringify(reopen));
  browser.assign(authUrl);
  return true;
}

/** `raw` when it is a page the app may return to, else Settings → Account. */
export function returnToFrom(raw: unknown): string {
  return safeInternalPath(raw) ?? DEFAULT_RETURN;
}

export function readReturnTo(): string {
  return returnToFrom(readSession(GMAIL_RETURN_KEY));
}

export function clearReturnTo(): void {
  removeSession(GMAIL_RETURN_KEY);
}

export type CallbackParams = { code: string | null; state: string | null; error: string | null };

/** `?code=…&state=…` or `?error=…` from `/gmail/callback`'s query string; blank values are null. */
export function parseCallbackParams(search: string): CallbackParams {
  const params = new URLSearchParams(search);
  const value = (name: string) => {
    const found = params.get(name);
    return found === null || found.trim() === "" ? null : found;
  };
  return { code: value("code"), state: value("state"), error: value("error") };
}

const submitted = new Map<string, Promise<GmailConnection>>();

/** `POST /gmail-connection` for this state, or the promise of the one already sent. */
export function connectGmailOnce(call: ApiCall, body: GmailConnectBody): Promise<GmailConnection> {
  let pending = submitted.get(body.state);
  if (pending === undefined) {
    pending = call<GmailConnection>("/gmail-connection", { method: "POST", json: body });
    submitted.set(body.state, pending);
  }
  return pending;
}

/** Gmail's and Google's 5xx answers whose message says what happened and what to do. */
const OWN_MESSAGE_CODES = new Set(["gmail_send_failed", "gmail_not_configured", "upstream_error", "upstream_timeout"]);

/**
 * The sentence for a failed Gmail request: the server's own for a Gmail or
 * Google 502, 503 or 504 ("Couldn't reach Google. Try connecting again in a
 * minute."), which `errorToastMessage` would turn into "Something went
 * wrong."; anything else as every toast says it.
 */
export function gmailErrorMessage(e: unknown): string {
  return e instanceof ApiError && OWN_MESSAGE_CODES.has(e.code) ? e.message : errorToastMessage(e);
}

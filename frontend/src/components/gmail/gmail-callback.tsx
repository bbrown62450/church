"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Loader2Icon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { PendingButton } from "@/components/app/pending-button";
import { useStillWorking } from "@/components/builder/liturgy/use-still-working";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import {
  clearReturnTo,
  connectGmailOnce,
  gmailErrorMessage,
  parseCallbackParams,
  readReturnTo,
  type CallbackParams,
} from "@/lib/gmail";
import { reportAuthErrors, useApi } from "@/lib/queries/client";
import { useStartGmailConnect } from "@/lib/queries/gmail";
import { keys } from "@/lib/queries/keys";

export const CONNECTING = "Connecting your Gmail…";
export const STILL_CONNECTING = "Still working. This can take up to a minute.";
export const CONNECTED = "Gmail connected";
export const CANCELLED = "Gmail connection was cancelled.";
export const GOOGLE_REFUSED = "Google couldn't connect your Gmail.";
export const NOT_FINISHED = "Gmail connection didn't finish. Try connecting again.";
const CALLBACK_PATH = "/gmail/callback";

type View =
  | { kind: "connecting" }
  | { kind: "failed"; message: string; canRetry: boolean };

/**
 * `/gmail/callback` (slice 5b spec, flow C; slice 5b-2): the page Google sends
 * the browser back to. It reads Google's answer from the address bar once (a
 * ref, so React StrictMode's second effect reuses it), removes it from the
 * address bar and history, and then:
 * - `?error=access_denied` (the user cancelled): "Gmail connection was
 *   cancelled." and back where they started;
 * - another `?error=`: "Google couldn't connect your Gmail." (the value is
 *   never shown), with **Try again** and **Go back**;
 * - a code and a state: "Connecting your Gmail…" while `POST
 *   /gmail-connection` runs, once per state; then "Gmail connected", the
 *   status in the cache, and back; or the server's message with **Try again**
 *   (not when Gmail is not set up here) and **Go back**;
 * - nothing (a signed-out landing lost the query, or a reload after success):
 *   "Gmail connection didn't finish. Try connecting again.".
 * "Back" is the page the connect started from (`wsb:gmailReturnTo`), else
 * Settings → Account. It starts in the "connecting" state so the "didn't
 * finish" card never flashes during a successful connect.
 */
export function GmailCallback() {
  const api = useApi();
  const queryClient = useQueryClient();
  const router = useRouter();
  const params = useRef<CallbackParams | null>(null);
  const [view, setView] = useState<View>({ kind: "connecting" });
  const slow = useStillWorking(view.kind === "connecting");
  const start = useStartGmailConnect();

  useEffect(() => {
    if (params.current === null) params.current = parseCallbackParams(window.location.search);
    window.history.replaceState(null, "", CALLBACK_PATH);
    const { code, state, error } = params.current;
    const returnTo = readReturnTo();
    if (error === "access_denied") {
      clearReturnTo();
      toast(CANCELLED, { id: "gmail-callback" });
      router.replace(returnTo);
      return;
    }
    if (error !== null) {
      setView({ kind: "failed", message: GOOGLE_REFUSED, canRetry: true });
      return;
    }
    if (code === null || state === null) {
      setView({ kind: "failed", message: NOT_FINISHED, canRetry: true });
      return;
    }
    let active = true;
    connectGmailOnce(api.user, { code, state }).then(
      (status) => {
        if (!active) return;
        queryClient.setQueryData(keys.gmailConnection(), status);
        clearReturnTo();
        toast.success(CONNECTED, { id: "gmail-callback" });
        router.replace(returnTo);
      },
      (e: unknown) => {
        if (!active) return;
        reportAuthErrors(e, null);
        const notConfigured = e instanceof ApiError && e.code === "gmail_not_configured";
        setView({ kind: "failed", message: gmailErrorMessage(e), canRetry: !notConfigured });
      },
    );
    return () => {
      active = false;
    };
  }, [api, queryClient, router]);

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col justify-center p-4">
      <section aria-labelledby="gmail-callback-title" className="grid gap-4 rounded-lg border p-6">
        <h1 id="gmail-callback-title" className="text-lg font-semibold">
          Gmail
        </h1>
        {view.kind === "connecting" ? (
          <div role="status" className="flex items-start gap-2 text-sm">
            <Loader2Icon className="mt-0.5 size-4 shrink-0 animate-spin" aria-hidden="true" />
            <div className="grid gap-1">
              <p>{CONNECTING}</p>
              {slow ? <p className="text-muted-foreground">{STILL_CONNECTING}</p> : null}
            </div>
          </div>
        ) : (
          <>
            <p role="alert" className="text-sm">
              {view.message}
            </p>
            <div className="flex flex-col gap-2 sm:flex-row">
              {view.canRetry ? (
                <PendingButton
                  size="touch"
                  pending={start.isPending}
                  pendingLabel="Opening Google…"
                  onClick={() => start.mutate({ returnTo: readReturnTo() })}
                >
                  Try again
                </PendingButton>
              ) : null}
              <Button variant="outline" size="touch" onClick={() => router.replace(readReturnTo())}>
                Go back
              </Button>
            </div>
          </>
        )}
      </section>
    </main>
  );
}

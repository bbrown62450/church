"use client";

/**
 * Join a church with an invite code: preview first, then an explicit Join tap
 * (S Flow A Join tab, Flow B steps 4-6, Pages; owner decision 1, amendment to
 * decision 6). `/welcome`'s Join tab shows the entry field (`showEntry`); `/join`
 * does not, and passes the captured code with `autoPreview`.
 *
 * States: `enter` (the field only) → `previewing` (skeleton card) → `preview`
 * (church, role, expiry, or "already a member") → `joining` → `done` (navigating);
 * `rejected` (any 4xx other than 401 from preview or accept: the server's message)
 * and `error` (preview could not reach the server: inline ErrorState + Retry).
 * Rejection text lives only in this component's state, never in storage.
 *
 * The pending code (`wsb:pendingInviteCode`) is cleared after a join, after a
 * rejection other than `email_mismatch`, and by "Not now". Switching accounts
 * keeps it, and first stores the code in use, so a code typed on `/welcome`
 * also survives the new sign-in (`/login?next=/join` reads it back).
 *
 * A 401 or a sign-out in progress (`aborted`) changes nothing here: the
 * mutation cache's `handleAuthErrors` asks the page to sign out.
 */
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useId, useRef, useState, type FormEvent } from "react";
import { toast } from "sonner";

import { ErrorState } from "@/components/app/error-state";
import { PendingButton } from "@/components/app/pending-button";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, errorToastMessage, type InviteRejectReason } from "@/lib/api/errors";
import type { InvitePreview } from "@/lib/api/types";
import { useSignOut } from "@/lib/auth";
import { useMembershipChanged } from "@/lib/queries/membership";
import { useAcceptInvite, usePreviewInvite } from "@/lib/queries/onboarding";
import { removeSession, SESSION_KEYS, writeSession } from "@/lib/storage";
import { extractInviteCode } from "@/lib/urls";

/** The server's 422 text for a blank code (S Flow A step 3), checked on the client first. */
export const BLANK_CODE_MESSAGE = "Enter an invite code, or open your invite link again.";

const REJECT_REASONS: readonly InviteRejectReason[] = [
  "unknown",
  "revoked",
  "expired",
  "used",
  "church_unavailable",
  "email_mismatch",
];

type State =
  | { kind: "enter" }
  | { kind: "previewing"; code: string }
  | { kind: "preview"; code: string; preview: InvitePreview }
  | { kind: "joining"; code: string; preview: InvitePreview }
  | { kind: "done"; code: string; preview: InvitePreview }
  | { kind: "rejected"; code: string; reason: InviteRejectReason; message: string }
  | { kind: "error"; code: string; error: unknown };

export type JoinInviteProps = {
  /** The pending code (`/welcome`) or the captured one (`/join`); a pasted link works too. */
  initialCode?: string;
  /** Preview `initialCode` once on mount (never retried automatically; clarification 29). */
  autoPreview?: boolean;
  /** The signed-in user's email, for the email-bound, mismatch and footer lines. */
  email: string;
  /** Show the "Invite link or code" field and Continue (`/welcome` only). */
  showEntry: boolean;
};

/** Sign-out is already under way: a 401 (handleAuthErrors signs out) or a request cancelled by it. */
function isSignOutError(e: unknown): boolean {
  return e instanceof ApiError && (e.status === 401 || e.code === "aborted");
}

/** A 4xx the user cannot fix by retrying: the invite (or the code) is not usable. */
function isRejection(e: unknown): e is ApiError {
  return e instanceof ApiError && e.status >= 400 && e.status < 500 && e.status !== 401;
}

function rejectReason(e: ApiError): InviteRejectReason {
  const reason = e.details?.reason;
  return e.code === "invite_rejected" && REJECT_REASONS.includes(reason as InviteRejectReason)
    ? (reason as InviteRejectReason)
    : "unknown";
}

/** "October 5, 2026" in the browser's time zone (S Flow B step 4). */
function formatExpiry(iso: string): string {
  return new Intl.DateTimeFormat("en-US", { month: "long", day: "numeric", year: "numeric" }).format(new Date(iso));
}

export function JoinInvite({ initialCode = "", autoPreview = false, email, showEntry }: JoinInviteProps) {
  const router = useRouter();
  const signOut = useSignOut();
  const membershipChanged = useMembershipChanged();
  const { mutateAsync: previewInvite } = usePreviewInvite();
  const { mutateAsync: acceptInvite } = useAcceptInvite();

  const [field, setField] = useState(initialCode);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [state, setState] = useState<State>(() => {
    const code = autoPreview ? extractInviteCode(initialCode) : "";
    return code ? { kind: "previewing", code } : { kind: "enter" };
  });
  const autoCode = useRef(state.kind === "previewing" ? state.code : null);
  const inputRef = useRef<HTMLInputElement>(null);
  const inputId = useId();
  const helpId = useId();
  const errorId = useId();

  const reject = useCallback((code: string, e: ApiError) => {
    const reason = rejectReason(e);
    if (reason !== "email_mismatch") removeSession(SESSION_KEYS.pendingInviteCode);
    setState({ kind: "rejected", code, reason, message: e.fields?.code ?? e.message });
  }, []);

  /** Sends the preview; the caller has already shown the `previewing` skeleton. */
  const loadPreview = useCallback(
    async (code: string) => {
      try {
        const preview = await previewInvite(code);
        setState({ kind: "preview", code, preview });
      } catch (e) {
        if (isSignOutError(e)) return;
        if (isRejection(e)) reject(code, e);
        else setState({ kind: "error", code, error: e });
      }
    },
    [previewInvite, reject],
  );

  // `autoPreview`: once per mount, even under StrictMode's double effects, and never
  // retried automatically (clarification 29). The ref is emptied by the first run.
  useEffect(() => {
    const code = autoCode.current;
    if (code === null) return;
    autoCode.current = null;
    void loadPreview(code);
  }, [loadPreview]);

  function startPreview(code: string) {
    setState({ kind: "previewing", code });
    void loadPreview(code);
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const code = extractInviteCode(field);
    if (!code) {
      setFieldError(BLANK_CODE_MESSAGE);
      inputRef.current?.focus();
      return;
    }
    setFieldError(null);
    startPreview(code);
  }

  async function join(code: string, preview: InvitePreview) {
    setState({ kind: "joining", code, preview });
    try {
      const accepted = await acceptInvite(code);
      setState({ kind: "done", code, preview });
      removeSession(SESSION_KEYS.pendingInviteCode);
      await membershipChanged({ selectChurchId: accepted.church.id });
      toast.success(accepted.message);
    } catch (e) {
      if (isSignOutError(e)) return;
      if (isRejection(e)) {
        reject(code, e);
        return;
      }
      toast.error(errorToastMessage(e));
      setState({ kind: "preview", code, preview });
    }
  }

  function notNow() {
    removeSession(SESSION_KEYS.pendingInviteCode);
    router.replace("/");
  }

  async function switchAccount(code: string) {
    writeSession(SESSION_KEYS.pendingInviteCode, code);
    await signOut({ keepPendingInvite: true, next: "/join", selectAccount: true });
  }

  const busy = state.kind === "previewing" || state.kind === "joining" || state.kind === "done";

  return (
    <div className="flex flex-col gap-6">
      {showEntry && (
        <form noValidate onSubmit={submit} className="flex flex-col gap-2">
          <Label htmlFor={inputId}>Invite link or code</Label>
          <Input
            ref={inputRef}
            id={inputId}
            value={field}
            onChange={(event) => setField(event.target.value)}
            autoComplete="off"
            autoCapitalize="none"
            spellCheck={false}
            aria-invalid={fieldError ? true : undefined}
            aria-describedby={fieldError ? `${helpId} ${errorId}` : helpId}
            className="h-11 text-base md:text-sm"
          />
          <p id={helpId} className="text-sm text-muted-foreground">
            Paste the link or code from your invite.
          </p>
          {fieldError && (
            <p id={errorId} className="text-sm text-destructive">
              {fieldError}
            </p>
          )}
          <Button type="submit" size="touch" className="w-full" disabled={busy}>
            Continue
          </Button>
        </form>
      )}

      {state.kind === "previewing" && (
        <Card role="status" aria-label="Loading invite">
          <CardHeader>
            <Skeleton className="h-5 w-2/3" />
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-11 w-full" />
          </CardContent>
        </Card>
      )}

      {(state.kind === "preview" || state.kind === "joining" || state.kind === "done") && (
        <Card>
          <CardHeader>
            <CardTitle>
              <h2>{state.preview.church_name}</h2>
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {state.preview.already_member ? (
              <p>You&apos;re already a member of {state.preview.church_name}.</p>
            ) : (
              <div className="flex flex-col gap-1">
                <p>You&apos;re invited to join as {state.preview.role === "admin" ? "an admin" : "a member"}.</p>
                {state.preview.email_bound && <p>This invite is for {email}.</p>}
                <p className="text-muted-foreground">Invite expires {formatExpiry(state.preview.expires_at)}.</p>
              </div>
            )}
            <div className="flex flex-col gap-2">
              <PendingButton
                size="touch"
                className="w-full"
                pending={state.kind !== "preview"}
                pendingLabel="Joining…"
                onClick={() => void join(state.code, state.preview)}
              >
                {state.preview.already_member ? `Open ${state.preview.church_name}` : `Join ${state.preview.church_name}`}
              </PendingButton>
              <Button variant="outline" size="touch" className="w-full" disabled={busy} onClick={notNow}>
                Not now
              </Button>
            </div>
          </CardContent>
          <CardFooter className="flex-wrap gap-1 text-sm text-muted-foreground">
            <span>Signed in as {email} ·</span>
            <Button
              variant="link"
              className="h-auto p-0"
              disabled={busy}
              onClick={() => void switchAccount(state.code)}
            >
              Use a different account
            </Button>
          </CardFooter>
        </Card>
      )}

      {state.kind === "rejected" && (
        <Card role="alert">
          <CardHeader>
            <CardTitle>
              <h2>{state.message}</h2>
            </CardTitle>
            <CardDescription>
              {state.reason === "email_mismatch" ? `You're signed in as ${email}.` : "Ask for a new invite link."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {state.reason === "email_mismatch" ? (
              <Button size="touch" className="w-full" onClick={() => void switchAccount(state.code)}>
                Use a different Google account
              </Button>
            ) : (
              <Button variant="outline" size="touch" className="w-full" onClick={() => router.replace("/")}>
                Go to home
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {state.kind === "error" && <ErrorState error={state.error} onRetry={() => startPreview(state.code)} />}
    </div>
  );
}

"use client";

import { useEffect, useRef, useState } from "react";

import { STILL_WORKING } from "@/components/settings/hymnals-card";
import { useStillWorking } from "@/components/builder/liturgy/use-still-working";
import { PendingButton } from "@/components/app/pending-button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { ApiError } from "@/lib/api/client";
import { isNoChurchAccess } from "@/lib/api/errors";
import { useDraftVoiceProfile } from "@/lib/queries/prayer-library";
import { useAutosize } from "@/lib/use-autosize";
import { cn } from "@/lib/utils";

export const PROFILE_HELP = "How you pray, in a few sentences. The AI follows it whenever it writes your liturgy.";
export const SAVE_FIRST = "Save your prayers first.";
/** The server's words for a draft with no saved prayers (`usecases.prayer_library.NO_PRAYERS`). */
export const NO_SAVED_PRAYERS = "Add at least one prayer and save it first.";
export const DRAFT_TITLE = "Draft from your prayers";
export const WRITE_IT_YOURSELF = "You can still write the voice profile yourself.";

/** A failed draft's message: the server's (or the app's) words, never upstream text. */
function failureText(e: ApiError): string {
  return e.code === "ai_not_configured" ? `${e.message} ${WRITE_IT_YOURSELF}` : e.message;
}

/**
 * Settings → Prayers' voice profile (slice 6a-3b; prayer library spec "Voice
 * profile card"): the profile the liturgy writer follows, editable by owners
 * and admins and saved with the prayers (the page's one **Save**). Members
 * read it.
 *
 * **Update from my prayers** asks the AI for a draft from the *saved* prayers
 * (so it is disabled, with `blocked` as its hint, while the list has unsaved
 * changes or nothing is saved). While it waits: "Drafting…", "Still working"
 * after 8 s, and **Cancel**, which stops the wait (the draft is not stored, so
 * nothing changes). The draft shows beside the profile (stacked on a phone) as
 * text only, with **Use this draft** (it replaces the box's text, unsaved, so
 * it can still be edited) and **Keep mine**. It takes focus only from where the
 * wait left it (the button, Cancel, or nowhere); an admin typing elsewhere
 * keeps their place and hears "Draft from your prayers" instead. Leaving the
 * page stops the wait, and an answer for a wait given up on is dropped.
 */
export function VoiceProfileCard({
  value,
  admin,
  onChange,
  error,
  blocked,
}: {
  value: string;
  admin: boolean;
  onChange: (value: string) => void;
  error?: string;
  /** Why a draft cannot be asked for now ("Save your prayers first."), or null. */
  blocked: string | null;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const draftTitleRef = useRef<HTMLHeadingElement>(null);
  const controller = useRef<AbortController | null>(null);
  const focusDraft = useRef(false);
  const draft = useDraftVoiceProfile();
  const slow = useStillWorking(draft.isPending);
  const [result, setResult] = useState<string | null>(null);
  const [failure, setFailure] = useState<ApiError | null>(null);
  // True when the draft arrived while focus was elsewhere: the live line says it is there.
  const [announce, setAnnounce] = useState(false);
  useAutosize(ref, value);

  // Leaving the page (or switching church) stops the wait.
  useEffect(() => () => controller.current?.abort(), []);

  // A draft that just arrived takes focus (when the wait still had it), so it is read out and its two choices are next.
  useEffect(() => {
    if (!focusDraft.current) return;
    focusDraft.current = false;
    draftTitleRef.current?.focus();
  });

  function run() {
    if (draft.isPending || blocked !== null) return;
    const own = new AbortController();
    controller.current = own;
    setResult(null);
    setFailure(null);
    setAnnounce(false);
    draft.mutate(
      { signal: own.signal },
      {
        onSuccess: (answer) => {
          if (controller.current !== own) return; // given up on
          controller.current = null;
          // Focus moves only from the button, Cancel or nowhere; someone typing elsewhere keeps their place.
          const active = document.activeElement;
          const waiting =
            active === null || active === document.body || active === buttonRef.current || active === cancelRef.current;
          focusDraft.current = waiting;
          setAnnounce(!waiting);
          setResult(answer.draft);
        },
        onError: (e) => {
          if (controller.current !== own) return;
          controller.current = null;
          // A cancel, a sign-out, a lost church or a role 403 (toasted by the hook) shows nothing here.
          if (e.code === "aborted" || e.status === 401 || e.status === 403 || isNoChurchAccess(e)) return;
          setFailure(e);
        },
      },
    );
  }

  function cancel() {
    controller.current?.abort();
    buttonRef.current?.focus(); // the Cancel button goes away
  }

  const describedBy = ["voice-profile-help", error && "voice-profile-error"].filter(Boolean).join(" ");
  return (
    <section aria-labelledby="voice-profile-title" className="grid gap-3 rounded-lg border p-4">
      <h3 id="voice-profile-title" className="text-base font-medium">
        <label htmlFor="voice-profile">Voice profile</label>
      </h3>
      <div className={cn("grid gap-4", result !== null && "md:grid-cols-2")}>
        <div className="grid content-start gap-2">
          <Textarea
            id="voice-profile"
            ref={ref}
            value={value}
            readOnly={!admin}
            rows={5}
            className="max-h-[60vh] overflow-y-auto"
            aria-invalid={error ? true : undefined}
            aria-describedby={describedBy}
            onChange={(e) => onChange(e.target.value)}
          />
          <p id="voice-profile-help" className="text-sm text-muted-foreground">
            {PROFILE_HELP}
          </p>
          {error ? (
            <p id="voice-profile-error" role="alert" className="text-sm text-destructive">
              {error}
            </p>
          ) : null}
        </div>
        {result !== null ? (
          <section aria-labelledby="voice-draft-title" className="grid content-start gap-2 rounded-md border bg-muted/40 p-3">
            <h4 id="voice-draft-title" ref={draftTitleRef} tabIndex={-1} className="text-sm font-medium outline-none">
              {DRAFT_TITLE}
            </h4>
            <p className="text-sm break-words whitespace-pre-wrap">{result}</p>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                size="touch"
                className="md:h-9"
                onClick={() => {
                  onChange(result);
                  setResult(null);
                  setAnnounce(false);
                  ref.current?.focus();
                }}
              >
                Use this draft
              </Button>
              <Button
                type="button"
                variant="outline"
                size="touch"
                className="md:h-9"
                onClick={() => {
                  setResult(null);
                  setAnnounce(false);
                  buttonRef.current?.focus();
                }}
              >
                Keep mine
              </Button>
            </div>
          </section>
        ) : null}
      </div>
      {admin ? (
        <div className="grid gap-1">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <PendingButton
              ref={buttonRef}
              type="button"
              variant="outline"
              size="touch"
              className="w-full sm:w-fit md:h-9"
              pending={draft.isPending}
              pendingLabel="Drafting…"
              disabled={blocked !== null}
              aria-describedby={blocked !== null && !draft.isPending ? "voice-draft-blocked" : undefined}
              onClick={run}
            >
              Update from my prayers
            </PendingButton>
            {draft.isPending ? (
              <Button ref={cancelRef} type="button" variant="link" className="h-11 px-0 md:h-9" onClick={cancel}>
                Cancel
              </Button>
            ) : null}
          </div>
          <p id="voice-draft-status" aria-live="polite" className="text-sm text-muted-foreground empty:hidden">
            {draft.isPending && slow ? STILL_WORKING : announce && result !== null ? DRAFT_TITLE : null}
          </p>
          {blocked !== null && !draft.isPending ? (
            <p id="voice-draft-blocked" className="text-sm text-muted-foreground">
              {blocked}
            </p>
          ) : null}
          {failure ? (
            <Alert variant="destructive" role="alert">
              <AlertDescription>{failureText(failure)}</AlertDescription>
            </Alert>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

"use client";

/**
 * The Create tab of `/welcome` (S Flow A step 4; S "Loading, empty and error states", row
 * "Accept / Create"; AC6, AC11).
 *
 * - The client checks first, with the server's exact messages, and sends nothing when a
 *   check fails: the message shows under the field and the first invalid field gets focus.
 * - One Idempotency-Key tracker per mount (F §1.6): an identical retry after a network
 *   error, timeout or 5xx reuses the key, so the server replays the first answer instead of
 *   creating a second church; any 2xx or 4xx, or an edit, gets a new key, so a corrected
 *   resubmit never meets a stored 422 or `idempotency_mismatch`.
 * - A 422 with `fields.name` / `fields.timezone` shows inline like the client checks; a 429
 *   shows its message in an inline alert above the button (no toast); anything else is a
 *   toast (`errorToastMessage`: the long network sentence, or "Something went wrong. (Ref: …)").
 * - After 8 s of pending, "Still working — this can take up to a minute." (F §1.8; 1b
 *   clarification 25).
 * - Success: toast "Created {name}. You're the owner.", then `useMembershipChanged` stores the
 *   new church, refetches `/me` and goes to `/`. The button stays pending until then, so a
 *   second tap cannot create a second church with a new key.
 *
 * It renders only on the client (the `(signed-in)` layout shows its skeleton until `/me`
 * loads), so the time-zone default in the `useState` initializer cannot differ from a server
 * render.
 */
import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { toast } from "sonner";

import { PendingButton } from "@/components/app/pending-button";
import { TimezoneCombobox } from "@/components/app/timezone-combobox";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api/client";
import { errorToastMessage } from "@/lib/api/errors";
import type { Church } from "@/lib/api/types";
import { createKeyTracker, settleOutcome } from "@/lib/idempotency";
import { useMembershipChanged } from "@/lib/queries/membership";
import { useCreateChurch } from "@/lib/queries/onboarding";
import { defaultTimezone, listTimezones } from "@/lib/timezones";

/** How long a create may run before the "Still working" line shows (F §1.8). */
export const SLOW_AFTER_MS = 8_000;

type FieldErrors = { name?: string; timezone?: string };

/** The name and time-zone messages of a 422, or null when it has neither (then it is a toast). */
function fieldErrorsOf(e: unknown): FieldErrors | null {
  if (!(e instanceof ApiError) || e.status !== 422 || !e.fields) return null;
  const { name, timezone } = e.fields;
  return name || timezone ? { name, timezone } : null;
}

export function CreateChurchForm() {
  const nameId = useId();
  const timezoneId = useId();
  const nameRef = useRef<HTMLInputElement>(null);
  const [tracker] = useState(() => createKeyTracker());
  const [name, setName] = useState("");
  const [timezone, setTimezone] = useState(() => defaultTimezone(listTimezones()));
  const [errors, setErrors] = useState<FieldErrors>({});
  const [limitMessage, setLimitMessage] = useState<string | null>(null);
  const [slow, setSlow] = useState(false);
  const [created, setCreated] = useState(false);
  const create = useCreateChurch();
  const membershipChanged = useMembershipChanged();
  const pending = create.isPending || created;

  useEffect(() => {
    if (!pending) return;
    const timer = setTimeout(() => setSlow(true), SLOW_AFTER_MS);
    return () => clearTimeout(timer);
  }, [pending]);

  function showFieldErrors(next: FieldErrors) {
    setErrors(next);
    if (next.name) nameRef.current?.focus();
    else document.getElementById(timezoneId)?.focus();
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
    const body = { name: name.trim(), timezone: timezone.trim() };
    const checks: FieldErrors = {};
    if (body.name === "") checks.name = "Church name is required.";
    if (body.timezone === "") checks.timezone = "Timezone is required.";
    setLimitMessage(null);
    if (checks.name || checks.timezone) {
      showFieldErrors(checks);
      return;
    }
    setErrors({});
    setSlow(false);

    let church: Church;
    try {
      church = await create.mutateAsync({ body, key: tracker.keyFor(body) });
    } catch (e) {
      tracker.settle(settleOutcome(e));
      // A 401 is already signing out (useCreateChurch's handleAuthErrors): no toast.
      if (e instanceof ApiError && (e.status === 401 || e.code === "aborted")) return;
      const fields = fieldErrorsOf(e);
      if (fields) showFieldErrors(fields);
      else if (e instanceof ApiError && e.code === "rate_limited") setLimitMessage(e.message);
      else toast.error(errorToastMessage(e));
      return;
    }
    tracker.settle("success");
    setCreated(true);
    toast.success(`Created ${church.name}. You're the owner.`);
    await membershipChanged({ selectChurchId: church.id });
  }

  return (
    <form noValidate className="grid gap-4" onSubmit={(event) => void onSubmit(event)}>
      <p className="text-sm text-muted-foreground">
        Start a new church. You&apos;ll be its owner and can invite others.
      </p>
      <div className="grid gap-2">
        <Label htmlFor={nameId}>Church name</Label>
        <Input
          ref={nameRef}
          id={nameId}
          name="name"
          autoComplete="off"
          placeholder="e.g. First Presbyterian Church"
          maxLength={200}
          value={name}
          onChange={(event) => setName(event.target.value)}
          aria-invalid={errors.name ? true : undefined}
          aria-describedby={errors.name ? `${nameId}-error` : undefined}
          className="h-11"
        />
        {errors.name ? (
          <p id={`${nameId}-error`} className="text-sm text-destructive">
            {errors.name}
          </p>
        ) : null}
      </div>
      <TimezoneCombobox id={timezoneId} value={timezone} onChange={setTimezone} error={errors.timezone} />
      <p className="text-sm text-muted-foreground">Your church gets its own copy of the starter hymnal.</p>
      {limitMessage ? (
        <Alert variant="destructive">
          <AlertDescription>{limitMessage}</AlertDescription>
        </Alert>
      ) : null}
      <PendingButton type="submit" size="touch" className="w-full" pending={pending} pendingLabel="Creating church…">
        Create church
      </PendingButton>
      {pending && slow ? (
        <p role="status" className="text-sm text-muted-foreground">
          Still working — this can take up to a minute.
        </p>
      ) : null}
    </form>
  );
}

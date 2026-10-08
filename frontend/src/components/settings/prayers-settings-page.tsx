"use client";

import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { ErrorState } from "@/components/app/error-state";
import { LeaveGuard } from "@/components/app/leave-guard";
import { PendingButton } from "@/components/app/pending-button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { errorToastMessage } from "@/lib/api/errors";
import type { PrayerLibrary, PrayerType } from "@/lib/api/types";
import { isAdmin } from "@/lib/church";
import { useChurch } from "@/lib/church-context";
import { usePrayerLibrary, useSavePrayerLibrary } from "@/lib/queries/prayer-library";
import {
  afterSave,
  firstLine,
  hasErrors,
  hasLibraryChanges,
  libraryErrors,
  libraryFieldErrors,
  libraryFormFrom,
  MAX_PRAYERS,
  namesLibraryField,
  newRow,
  PRAYER_TYPE_LABELS,
  PRAYER_TYPES,
  prayersPayload,
  rebaseLibrary,
  TOO_MANY,
  type LibraryErrors,
  type LibraryForm,
  type PrayerRow,
  type RowErrors,
} from "@/lib/settings/prayers";
import { useAutosize } from "@/lib/use-autosize";
import { useKeyboardOpen } from "@/lib/use-keyboard-open";
import { cn } from "@/lib/utils";

import { VoiceProfileCard } from "./voice-profile-card";

export const PRAYERS_INTRO =
  "Your own prayers teach the AI how you pray. When it writes a prayer, it follows your voice profile and reads one of your prayers of the same kind, without reusing its lines. Everyone in your church can read this page.";
export const ADMINS_ONLY = "Only admins can edit the prayer library. You can read it below.";
export const EMPTY_LIBRARY = "No prayers yet. Paste in a few of your own prayers so the writer can learn your voice.";
export const REMOVE_TITLE = "Remove this prayer?";
const REMOVE_BODY = "It leaves your library when you save.";
const NEW_PRAYER = "New prayer";
const TYPE_ITEMS: Record<string, string> = Object.fromEntries(PRAYER_TYPES.map((type) => [type, PRAYER_TYPE_LABELS[type]]));
const NO_ERRORS: LibraryErrors = { rows: {} };

/**
 * `/settings/prayers` (slice 6a-3b; prayer library spec "Prayers page (slice
 * 6a)"; 6a spec UX §5): the church's own prayers, which teach the liturgy
 * writer the pastor's voice, and the voice profile drafted from them. Every
 * member reads them; owners and admins add, edit and remove prayers and edit
 * the profile, all saved together by the one **Save** (a full replace). 6a's
 * rules for settings forms: newer server data rebases the form, and leaving
 * with unsaved edits asks first (`LeaveGuard`). Pastor text is React text only.
 */
export function PrayersSettingsPage() {
  const church = useChurch();
  const admin = isAdmin(church.role);
  const library = usePrayerLibrary();
  let body: ReactNode;
  if (library.data) {
    body = <LibraryEditor out={library.data} admin={admin} />;
  } else if (library.isError) {
    body = <ErrorState error={library.error} onRetry={() => void library.refetch()} retrying={library.isFetching} />;
  } else {
    body = (
      <div role="status" aria-label="Loading" className="grid gap-3">
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
    );
  }
  return (
    <section aria-labelledby="prayers-title" className="grid gap-4">
      <div className="grid gap-1">
        <h2 id="prayers-title" className="text-lg font-semibold">
          Prayer library
        </h2>
        <p className="text-sm text-muted-foreground">{PRAYERS_INTRO}</p>
      </div>
      {body}
    </section>
  );
}

type FormState = { source: PrayerLibrary; baseline: LibraryForm; form: LibraryForm };

function LibraryEditor({ out, admin }: { out: PrayerLibrary; admin: boolean }) {
  const save = useSavePrayerLibrary();
  const keyboardOpen = useKeyboardOpen();
  const [state, setState] = useState<FormState>(() => {
    const form = libraryFormFrom(out);
    return { source: out, baseline: form, form };
  });
  const [errors, setErrors] = useState<LibraryErrors>(NO_ERRORS);
  const [open, setOpen] = useState<ReadonlySet<string>>(() => new Set());
  const [removing, setRemoving] = useState<string | null>(null);
  const removeFocus = useRef<string | null>(null);
  const focusId = useRef<string | null>(null);
  const added = useRef(0);
  const rowsNow = useRef<readonly PrayerRow[]>([]);
  const { form, baseline } = state;
  const dirty = admin && hasLibraryChanges(baseline, form);
  // A member (or an admin demoted meanwhile) reads what is stored, never an unsaved edit.
  const shown = admin ? form : libraryFormFrom(out);

  // Newer server data (a refetch, or this page's own save in the cache): rebase (6a).
  if (out !== state.source) {
    const next = libraryFormFrom(out);
    setState({ source: out, baseline: next, form: rebaseLibrary(baseline, form, next) });
  }

  // The rows on the page now, for a refusal that lands after a row it names was removed.
  useEffect(() => {
    rowsNow.current = form.rows;
  });

  // The control a check or a refusal named, or a new row's type: focused once it is on the page.
  useEffect(() => {
    if (focusId.current === null) return;
    document.getElementById(focusId.current)?.focus();
    focusId.current = null;
  });

  const setRows = (rows: (rows: PrayerRow[]) => PrayerRow[]) => setState((s) => ({ ...s, form: { ...s.form, rows: rows(s.form.rows) } }));
  const clearError = (key: string, field: keyof RowErrors) => {
    if (!errors.rows[key]?.[field]) return;
    setErrors((e) => ({ ...e, rows: { ...e.rows, [key]: { ...e.rows[key], [field]: undefined } } }));
  };
  const update = (key: string, patch: Partial<PrayerRow>) => {
    setRows((rows) => rows.map((row) => (row.key === key ? { ...row, ...patch } : row)));
    if ("type" in patch) clearError(key, "type");
    if ("text" in patch) clearError(key, "text");
  };
  const toggle = (key: string) =>
    setOpen((o) => {
      const next = new Set(o);
      if (!next.delete(key)) next.add(key);
      return next;
    });

  function addPrayer() {
    added.current += 1;
    const key = `new-${added.current}`;
    setRows((rows) => [...rows, newRow(key)]);
    setOpen((o) => new Set(o).add(key));
    focusId.current = `prayer-type-${key}`;
  }

  function confirmRemove() {
    const rows = form.rows;
    const at = rows.findIndex((row) => row.key === removing);
    const next = rows[at + 1] ?? rows[at - 1];
    // The Remove button that opened the dialog is gone: focus goes to the next prayer, else the one before, else Add.
    removeFocus.current = next ? `prayer-edit-${next.key}` : "add-prayer";
    setRows((all) => all.filter((row) => row.key !== removing));
    setRemoving(null);
  }

  /** Shows these messages and focuses the first in page order: the profile, then each row's type, then its text. */
  function show(found: LibraryErrors, order: readonly string[]) {
    setErrors(found);
    setOpen((o) => new Set([...o, ...Object.keys(found.rows)]));
    const first = order.find((key) => found.rows[key]);
    if (found.profile) focusId.current = "voice-profile";
    else if (first) focusId.current = found.rows[first].type ? `prayer-type-${first}` : `prayer-text-${first}`;
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (save.isPending || !dirty) return;
    const sent = form;
    const sentKeys = sent.rows.map((row) => row.key);
    const found = libraryErrors(sent);
    if (hasErrors(found)) {
      show(found, sentKeys);
      return;
    }
    save.mutate(prayersPayload(sent), {
      // What was typed while saving stays; everything else shows what was stored. `source` is left for the
      // cache's copy of the answer to replace, which rebases onto this (a render may still see the old copy).
      onSuccess: (saved) => {
        setErrors(NO_ERRORS);
        setState((s) => ({ ...s, ...afterSave(sent, s.form, saved) }));
      },
      onError: (e) => {
        if (!namesLibraryField(e)) return; // the hook toasted it, or the app reports it
        const named = libraryFieldErrors(e, sentKeys);
        const onPage = new Set(rowsNow.current.map((row) => row.key));
        // Shown on the form only while a field it names is still there (a row removed during the save is not).
        if (named && (named.profile !== undefined || Object.keys(named.rows).some((key) => onPage.has(key)))) {
          show(named, sentKeys);
        } else {
          toast.error(errorToastMessage(e));
        }
      },
    });
  }

  const rows = shown.rows;
  return (
    <form onSubmit={onSubmit} className="grid gap-4" aria-label="Prayer library">
      {admin ? null : (
        <Alert role="status">
          <AlertDescription>{ADMINS_ONLY}</AlertDescription>
        </Alert>
      )}
      <VoiceProfileCard
        value={shown.profile}
        admin={admin}
        onChange={(profile) => {
          setState((s) => ({ ...s, form: { ...s.form, profile } }));
          if (errors.profile) setErrors((e) => ({ ...e, profile: undefined }));
        }}
        error={admin ? errors.profile : undefined}
      />
      <section aria-labelledby="prayer-list-title" className="grid gap-3">
        <h3 id="prayer-list-title" className="text-base font-medium">
          Prayers
        </h3>
        {rows.length === 0 ? <p className="text-sm text-muted-foreground">{EMPTY_LIBRARY}</p> : null}
        {rows.length > 0 ? (
          <ol aria-labelledby="prayer-list-title" className="grid gap-3">
            {rows.map((row, i) =>
              admin ? (
                <PrayerRowEditor
                  key={row.key}
                  row={row}
                  n={i + 1}
                  open={open.has(row.key)}
                  errors={errors.rows[row.key]}
                  onToggle={() => toggle(row.key)}
                  onChange={(patch) => update(row.key, patch)}
                  onRemove={() => {
                    removeFocus.current = null;
                    setRemoving(row.key);
                  }}
                />
              ) : (
                <li key={row.key} className="grid gap-1 rounded-lg border p-3">
                  <p className="text-sm font-medium">{row.type === "" ? null : PRAYER_TYPE_LABELS[row.type]}</p>
                  <p className="min-w-0 text-sm break-words whitespace-pre-wrap">{row.text}</p>
                </li>
              ),
            )}
          </ol>
        ) : null}
        {admin ? (
          <div className="grid gap-1">
            <Button
              id="add-prayer"
              type="button"
              variant="outline"
              size="touch"
              className="w-full sm:w-fit"
              disabled={rows.length >= MAX_PRAYERS}
              onClick={addPrayer}
            >
              Add a prayer
            </Button>
            {rows.length >= MAX_PRAYERS ? <p className="text-sm text-muted-foreground">{TOO_MANY}</p> : null}
          </div>
        ) : null}
      </section>
      {admin ? (
        <div
          data-keyboard-open={keyboardOpen ? "" : undefined}
          className={cn(
            "sticky bottom-0 z-10 flex flex-wrap gap-2 border-t bg-background/95 pt-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] backdrop-blur",
            // While a text field has focus the footer sits after the list, at every width (6a-3a build review 2:
            // a phone held sideways is wider than md, and its keyboard leaves a short view the bar would cover).
            keyboardOpen && "static",
          )}
        >
          <PendingButton type="submit" size="touch" className="w-full sm:w-fit" pending={save.isPending} disabled={!dirty}>
            Save
          </PendingButton>
        </div>
      ) : null}
      <ConfirmDialog
        open={removing !== null}
        onOpenChange={(next) => {
          if (!next) setRemoving(null);
        }}
        title={REMOVE_TITLE}
        description={REMOVE_BODY}
        confirmLabel="Remove prayer"
        destructive
        onConfirm={confirmRemove}
        finalFocus={() => (removeFocus.current === null ? true : document.getElementById(removeFocus.current))}
      />
      <LeaveGuard when={dirty} />
    </form>
  );
}

function PrayerRowEditor({
  row,
  n,
  open,
  errors,
  onToggle,
  onChange,
  onRemove,
}: {
  row: PrayerRow;
  n: number;
  open: boolean;
  errors?: RowErrors;
  onToggle: () => void;
  onChange: (patch: Partial<PrayerRow>) => void;
  onRemove: () => void;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);
  useAutosize(ref, row.text, open);
  const id = (part: string) => `prayer-${part}-${row.key}`;
  const summary = firstLine(row.text);
  return (
    <li className="grid gap-2 rounded-lg border p-3">
      <p className={cn("min-w-0 truncate text-sm", summary === "" && "text-muted-foreground")}>{summary || NEW_PRAYER}</p>
      <div className="flex flex-wrap items-center gap-2">
        <Select
          value={row.type === "" ? null : row.type}
          items={TYPE_ITEMS}
          onValueChange={(value) => {
            if (typeof value === "string") onChange({ type: value as PrayerType });
          }}
        >
          <SelectTrigger
            id={id("type")}
            aria-label={`Type of prayer ${n}`}
            aria-invalid={errors?.type ? true : undefined}
            aria-describedby={errors?.type ? id("type-error") : undefined}
            className="h-11 w-full min-w-0 data-[size=default]:h-11 sm:w-60 md:h-9 md:data-[size=default]:h-9"
          >
            <SelectValue placeholder="Choose a type" />
          </SelectTrigger>
          <SelectContent>
            {PRAYER_TYPES.map((type) => (
              <SelectItem key={type} value={type}>
                {PRAYER_TYPE_LABELS[type]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          id={id("edit")}
          type="button"
          variant="outline"
          size="touch"
          className="md:h-9"
          aria-expanded={open}
          aria-controls={open ? id("body") : undefined}
          aria-label={`${open ? "Close" : "Edit"} prayer ${n}`}
          onClick={onToggle}
        >
          {open ? "Close" : "Edit"}
        </Button>
        <Button type="button" variant="ghost" size="touch" className="md:h-9" aria-label={`Remove prayer ${n}`} onClick={onRemove}>
          Remove
        </Button>
      </div>
      {errors?.type ? (
        <p id={id("type-error")} role="alert" className="text-sm text-destructive">
          {errors.type}
        </p>
      ) : null}
      {open ? (
        <div id={id("body")} className="grid gap-2">
          <label htmlFor={id("text")} className="sr-only">
            {`Prayer ${n}`}
          </label>
          <Textarea
            id={id("text")}
            ref={ref}
            value={row.text}
            rows={6}
            className="max-h-[60vh] overflow-y-auto"
            aria-invalid={errors?.text ? true : undefined}
            aria-describedby={errors?.text ? id("text-error") : undefined}
            onChange={(e) => onChange({ text: e.target.value })}
          />
          {errors?.text ? (
            <p id={id("text-error")} role="alert" className="text-sm text-destructive">
              {errors.text}
            </p>
          ) : null}
        </div>
      ) : null}
    </li>
  );
}

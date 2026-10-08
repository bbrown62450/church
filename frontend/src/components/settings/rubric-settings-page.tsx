"use client";

import { useEffect, useRef, useState, type FormEvent, type ReactNode, type RefObject } from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { ErrorState } from "@/components/app/error-state";
import { LeaveGuard } from "@/components/app/leave-guard";
import { PendingButton } from "@/components/app/pending-button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import type { Rubric } from "@/lib/api/types";
import { isAdmin } from "@/lib/church";
import { useChurch } from "@/lib/church-context";
import { isInvalidRubric, useRubric, useSaveRubric } from "@/lib/queries/rubric";
import {
  changedItems,
  checklistCustomized,
  CHECKLISTS,
  rebaseRubric,
  resetAllPatch,
  rubricErrors,
  rubricFormFrom,
  rubricPatch,
  type Checklist,
  type ChecklistKey,
  type RubricForm,
} from "@/lib/settings/rubric";
import { useKeyboardOpen } from "@/lib/use-keyboard-open";
import { cn } from "@/lib/utils";

import { ChecklistCard, pointId, THEME_NOTE } from "./checklist-card";

export const RUBRIC_INTRO =
  "What makes a good hymn or prayer at your church. The AI follows these checklists when it suggests hymns and writes liturgy. How each prayer is laid out (Leader and People lines, length, “Amen”) stays in Liturgy prompts.";
export const ADMINS_ONLY = "Only admins can edit the rubric. You can read it below.";
export const YEAR_HELP =
  "Hymns with older words are suggested first. This is a preference, not a filter: a newer hymn can still be suggested when it fits clearly better, and the builder shows its year.";
export const FAMILIAR_HELP = "Hymns found in many hymnals are suggested first.";
export const RESET_ALL_TITLE = "Reset the rubric?";
const RESET_ALL_BODY = "Your church's checklists and preferences go back to the shared defaults.";

/** Open from `md` (48rem), closed below it, as the page first renders (6a spec UX §6). */
function openAtFirst(): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia("(min-width: 48rem)").matches;
}

/**
 * `/settings/rubric` (slice 6a-3a; 6a spec UX §6): the church's service
 * rubric, the checklists the AI follows when it suggests hymns and writes
 * liturgy, and two hymn preferences. Every member reads it; owners and admins
 * edit it and save one sparse `PATCH /rubric` (an item put back to its
 * default is sent as null), or reset it all (confirmed). 6a's rules for
 * settings forms: newer server data rebases the form, and leaving with
 * unsaved edits asks first (`LeaveGuard`).
 */
export function RubricSettingsPage() {
  const church = useChurch();
  const admin = isAdmin(church.role);
  const rubric = useRubric();
  const headingRef = useRef<HTMLHeadingElement>(null);
  let body: ReactNode;
  if (rubric.data) {
    body = <RubricFormView out={rubric.data} admin={admin} headingRef={headingRef} />;
  } else if (rubric.isError) {
    body = <ErrorState error={rubric.error} onRetry={() => void rubric.refetch()} retrying={rubric.isFetching} />;
  } else {
    body = (
      <div role="status" aria-label="Loading" className="grid gap-3">
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-11 w-full" />
      </div>
    );
  }
  return (
    <section aria-labelledby="rubric-title" className="grid gap-4">
      <div className="grid gap-1">
        <h2 id="rubric-title" ref={headingRef} tabIndex={-1} className="text-lg font-semibold outline-none">
          Service rubric
        </h2>
        <p className="text-sm text-muted-foreground">{RUBRIC_INTRO}</p>
      </div>
      {body}
    </section>
  );
}

type FormState = { source: Rubric; baseline: RubricForm; form: RubricForm };

function RubricFormView({ out, admin, headingRef }: { out: Rubric; admin: boolean; headingRef: RefObject<HTMLHeadingElement | null> }) {
  const save = useSaveRubric();
  const reset = useSaveRubric();
  const keyboardOpen = useKeyboardOpen();
  const [thisYear] = useState(() => new Date().getFullYear());
  const [state, setState] = useState<FormState>(() => {
    const form = rubricFormFrom(out.rubric);
    return { source: out, baseline: form, form };
  });
  const [open, setOpen] = useState(
    () => Object.fromEntries(CHECKLISTS.map((list) => [list.key, openAtFirst()])) as Record<ChecklistKey, boolean>,
  );
  const [serverError, setServerError] = useState<string | null>(null);
  // The year's message waits until the box loses focus or holds four characters (Save is blocked meanwhile).
  const [yearLeft, setYearLeft] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const focusTarget = useRef<string | null>(null);
  const resetDone = useRef(false);
  const { form, baseline } = state;
  const pending = save.isPending || reset.isPending;
  const errors = admin ? rubricErrors(form, thisYear) : {};
  const dirty = admin && changedItems(baseline, form).length > 0;
  const canSave = dirty && Object.keys(errors).length === 0;
  // A member (or an admin demoted meanwhile) reads what is stored, never an unsaved edit.
  const shown = admin ? form : rubricFormFrom(out.rubric);
  const yearError = yearLeft || shown.prefer_before_year.trim().length >= 4 ? errors.prefer_before_year : undefined;
  const defaults = rubricFormFrom(out.defaults);

  // Newer server data (a refetch, or this page's own save in the cache): rebase (6a).
  if (out !== state.source) {
    const next = rubricFormFrom(out.rubric);
    setState({ source: out, baseline: next, form: rebaseRubric(baseline, form, next) });
  }

  // A point added or removed, a preference or checklist reset, or the server's message: focused once it is on the page.
  useEffect(() => {
    if (focusTarget.current === null) return;
    document.getElementById(focusTarget.current)?.focus();
    focusTarget.current = null;
  });

  const edit = (change: (f: RubricForm) => RubricForm) => {
    setState((s) => ({ ...s, form: change(s.form) }));
    setServerError(null);
  };
  const setPoints = (list: Checklist, points: string[]) =>
    edit((f) => ({ ...f, checklists: { ...f.checklists, [list.key]: points } }));

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (pending || !canSave) return;
    const sent = form;
    save.mutate(
      { patch: rubricPatch(baseline, sent, out.defaults) },
      {
        // What was typed while saving stays; everything else shows what was stored.
        onSuccess: (saved) =>
          setState((s) => {
            const next = rubricFormFrom(saved.rubric);
            return { source: saved, baseline: next, form: rebaseRubric(sent, s.form, next) };
          }),
        onError: (e) => {
          if (!isInvalidRubric(e)) return;
          setServerError(e.message);
          focusTarget.current = "rubric-server-error";
        },
      },
    );
  }

  function onResetAll() {
    if (pending) return;
    resetDone.current = false;
    reset.mutate(
      { patch: resetAllPatch(), reset: true },
      {
        onSuccess: (saved) => {
          const next = rubricFormFrom(saved.rubric);
          setState({ source: saved, baseline: next, form: next });
          setServerError(null);
          resetDone.current = true;
          setConfirming(false);
        },
        onError: () => setConfirming(false),
      },
    );
  }

  const yearCustomized = shown.prefer_before_year.trim() !== defaults.prefer_before_year;
  const familiarCustomized = shown.prefer_familiar !== defaults.prefer_familiar;
  const card = (list: Checklist) => (
    <ChecklistCard
      key={list.key}
      list={list}
      points={shown.checklists[list.key]}
      defaultPoints={defaults.checklists[list.key]}
      customized={checklistCustomized(shown, out.defaults, list)}
      admin={admin}
      open={open[list.key] || Boolean(errors[list.key])}
      onOpenChange={(next) => setOpen((o) => ({ ...o, [list.key]: next }))}
      onChange={(points) => setPoints(list, points)}
      onFocusPoint={(index) => {
        focusTarget.current = index === null ? `rubric-${list.key}-add` : pointId(list, index);
      }}
      error={errors[list.key]}
      note={list.key === "hymns.opening" || list.key === "hymns.closing" ? THEME_NOTE : undefined}
    />
  );

  return (
    <form onSubmit={onSubmit} className="grid gap-4" aria-label="Service rubric">
      {admin ? null : (
        <Alert role="status">
          <AlertDescription>{ADMINS_ONLY}</AlertDescription>
        </Alert>
      )}
      <fieldset className="grid gap-4 rounded-lg border p-4">
        <legend className="px-1 text-base font-medium">Hymn preferences</legend>
        <div className="grid gap-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <Label htmlFor="rubric-year">Prefer hymns written before</Label>
            {yearCustomized ? <Badge variant="secondary">Customized</Badge> : null}
          </div>
          <Input
            id="rubric-year"
            inputMode="numeric"
            maxLength={4}
            value={shown.prefer_before_year}
            readOnly={!admin}
            className="h-11 w-28"
            aria-invalid={yearError ? true : undefined}
            aria-describedby={["rubric-year-help", yearError && "rubric-year-error"].filter(Boolean).join(" ")}
            onChange={(e) => edit((f) => ({ ...f, prefer_before_year: e.target.value }))}
            onBlur={() => setYearLeft(true)}
          />
          <p id="rubric-year-help" className="text-sm text-muted-foreground">
            {YEAR_HELP}
          </p>
          {yearError ? (
            <p id="rubric-year-error" role="alert" className="text-sm text-destructive">
              {yearError}
            </p>
          ) : null}
          {admin && yearCustomized ? (
            <Button
              type="button"
              variant="link"
              className="h-11 justify-self-start px-0 md:h-auto"
              aria-label="Reset to default: Prefer hymns written before"
              onClick={() => {
                edit((f) => ({ ...f, prefer_before_year: defaults.prefer_before_year }));
                focusTarget.current = "rubric-year"; // the button goes: focus stays on the preference
              }}
            >
              Reset to default
            </Button>
          ) : null}
        </div>
        <div className="grid gap-1.5">
          <div className="flex flex-wrap items-center gap-3">
            <Switch
              id="rubric-familiar"
              checked={shown.prefer_familiar}
              disabled={!admin}
              aria-describedby="rubric-familiar-help"
              onCheckedChange={(checked) => edit((f) => ({ ...f, prefer_familiar: checked }))}
              className="after:-inset-y-3.5"
            />
            <Label htmlFor="rubric-familiar">Prefer familiar hymns</Label>
            {familiarCustomized ? <Badge variant="secondary">Customized</Badge> : null}
          </div>
          <p id="rubric-familiar-help" className="text-sm text-muted-foreground">
            {FAMILIAR_HELP}
          </p>
          {admin && familiarCustomized ? (
            <Button
              type="button"
              variant="link"
              className="h-11 justify-self-start px-0 md:h-auto"
              aria-label="Reset to default: Prefer familiar hymns"
              onClick={() => {
                edit((f) => ({ ...f, prefer_familiar: defaults.prefer_familiar }));
                focusTarget.current = "rubric-familiar"; // the button goes: focus stays on the preference
              }}
            >
              Reset to default
            </Button>
          ) : null}
        </div>
      </fieldset>
      <h3 className="text-base font-medium">Hymns</h3>
      {CHECKLISTS.filter((list) => list.group === "hymns").map(card)}
      <h3 className="text-base font-medium">Prayers</h3>
      {CHECKLISTS.filter((list) => list.group === "prayers").map(card)}
      {admin && serverError ? (
        <Alert id="rubric-server-error" tabIndex={-1} variant="destructive" className="outline-none">
          <AlertDescription>{serverError}</AlertDescription>
        </Alert>
      ) : null}
      {admin ? (
        <div
          data-keyboard-open={keyboardOpen ? "" : undefined}
          className={cn(
            "sticky bottom-0 z-10 flex flex-wrap gap-2 border-t bg-background/95 pt-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] backdrop-blur",
            // While a text field has focus the footer sits after the last card, at every width (6a-3a build
            // review 2): a phone held sideways is wider than md (844-932px) and its keyboard leaves a short
            // view the sticky bar would cover. Focus cannot tell an on-screen keyboard from a hardware one,
            // and pointer media queries misreport tablets with keyboards, so no width or pointer test: on a
            // desktop the cost is scrolling (or Tab) to Save while typing, and the bar comes back on blur.
            keyboardOpen && "static",
          )}
        >
          <PendingButton type="submit" size="touch" className="w-full sm:w-fit" pending={save.isPending} disabled={!canSave || reset.isPending}>
            Save rubric
          </PendingButton>
          {out.customized.length > 0 ? (
            <Button type="button" variant="outline" size="touch" className="w-full sm:w-fit" disabled={pending} onClick={() => setConfirming(true)}>
              Reset all to defaults
            </Button>
          ) : null}
        </div>
      ) : null}
      <ConfirmDialog
        open={confirming}
        onOpenChange={(next) => {
          if (!next && !reset.isPending) setConfirming(false);
        }}
        title={RESET_ALL_TITLE}
        description={RESET_ALL_BODY}
        confirmLabel="Reset all"
        destructive
        pending={reset.isPending}
        onConfirm={onResetAll}
        // After a reset the button that opened it is gone (nothing is customized): the page's heading takes focus.
        finalFocus={() => (resetDone.current ? headingRef.current : true)}
      />
      <LeaveGuard when={dirty} />
    </form>
  );
}

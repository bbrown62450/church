"use client";

import { ChevronDownIcon } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent, type ReactNode, type RefObject } from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { ErrorState } from "@/components/app/error-state";
import { LeaveGuard } from "@/components/app/leave-guard";
import { PendingButton } from "@/components/app/pending-button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import type { LiturgyPrompts, PromptField, PromptKey } from "@/lib/api/types";
import { isAdmin } from "@/lib/church";
import { useChurch } from "@/lib/church-context";
import { useLiturgyPrompts, useSaveLiturgyPrompts } from "@/lib/queries/liturgy-prompts";
import {
  hasPromptChanges,
  isCustomized,
  MAX_PROMPT_LENGTH,
  PROMPT_KEYS,
  promptFieldErrors,
  promptsPayload,
  promptValuesFrom,
  rebasePrompts,
  type PromptErrors,
  type PromptValues,
} from "@/lib/settings/prompts";
import { useAutosize } from "@/lib/use-autosize";
import { useKeyboardOpen } from "@/lib/use-keyboard-open";
import { cn } from "@/lib/utils";

export const PROMPTS_INTRO =
  "These are the instructions the AI follows when it writes your liturgy. Edit any of them to shape the voice; leave a box on its default to use the shared wording.";
export const ADMINS_ONLY = "Only admins can edit the prompts. You can read them below.";
export const SYSTEM_NOTE = "Placeholders aren't filled in here; this text is sent as written.";
export const BRACE_NOTE = "Use {{ or }} to print a brace.";
export const RESET_ALL_TITLE = "Reset all prompts?";
const RESET_ALL_BODY = "Your church's custom wording will be removed and the shared defaults used.";
const SYSTEM_TITLE = "Overall voice (system prompt)";
/** The two long prompts start taller (6a spec UX §3). */
const TALL: ReadonlySet<PromptKey> = new Set(["system", "prayers_of_the_people"]);

/** Open from `md` (48rem), closed below it, as the page first renders (6a spec UX §3; as the hymn matches). */
function openAtFirst(): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia("(min-width: 48rem)").matches;
}

const allKeys = (open: boolean) => Object.fromEntries(PROMPT_KEYS.map((key) => [key, open])) as Record<PromptKey, boolean>;

/**
 * `/settings/liturgy` (slice 6a-3a; 6a spec UX §3): the instructions the AI
 * follows when it writes the liturgy, the overall voice (system) prompt and
 * one per section, each beside its shared default. Every member reads them;
 * owners and admins edit them, put one back to its default (unsaved until
 * **Save prompts**) and reset them all (confirmed). 6a's rules for settings
 * forms: newer server data rebases the form, and leaving with unsaved edits
 * asks first (`LeaveGuard`).
 */
export function LiturgyPromptsPage() {
  const church = useChurch();
  const admin = isAdmin(church.role);
  const prompts = useLiturgyPrompts();
  const headingRef = useRef<HTMLHeadingElement>(null);
  let body: ReactNode;
  if (prompts.data) {
    body = <PromptsForm out={prompts.data} admin={admin} headingRef={headingRef} />;
  } else if (prompts.isError) {
    body = <ErrorState error={prompts.error} onRetry={() => void prompts.refetch()} retrying={prompts.isFetching} />;
  } else {
    body = (
      <div role="status" aria-label="Loading" className="grid gap-3">
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-11 w-full" />
      </div>
    );
  }
  return (
    <section aria-labelledby="prompts-title" className="grid gap-4">
      <div className="grid gap-1">
        <h2 id="prompts-title" ref={headingRef} tabIndex={-1} className="text-lg font-semibold outline-none">
          Liturgy prompts
        </h2>
        <p className="text-sm text-muted-foreground">{PROMPTS_INTRO}</p>
      </div>
      {body}
    </section>
  );
}

type FormState = { source: LiturgyPrompts; baseline: PromptValues; form: PromptValues };

function PromptsForm({
  out,
  admin,
  headingRef,
}: {
  out: LiturgyPrompts;
  admin: boolean;
  headingRef: RefObject<HTMLHeadingElement | null>;
}) {
  const save = useSaveLiturgyPrompts();
  const reset = useSaveLiturgyPrompts();
  const keyboardOpen = useKeyboardOpen();
  const [state, setState] = useState<FormState>(() => {
    const form = promptValuesFrom(out);
    return { source: out, baseline: form, form };
  });
  const [errors, setErrors] = useState<PromptErrors>({});
  const [open, setOpen] = useState(() => allKeys(openAtFirst()));
  const focusKey = useRef<PromptKey | null>(null);
  const [confirming, setConfirming] = useState(false);
  const resetDone = useRef(false);
  const { form, baseline } = state;
  const pending = save.isPending || reset.isPending;
  const dirty = admin && hasPromptChanges(baseline, form, out.fields);
  // A member (or an admin demoted meanwhile) reads what is stored, never an unsaved edit.
  const shown = admin ? form : promptValuesFrom(out);

  // Newer server data (a refetch, or this page's own save in the cache): rebase (6a).
  if (out !== state.source) {
    const next = promptValuesFrom(out);
    setState({ source: out, baseline: next, form: rebasePrompts(baseline, form, next) });
  }

  // The first card a failed save named: opened by onError, focused once it is on the page.
  useEffect(() => {
    if (focusKey.current === null) return;
    document.getElementById(`prompt-${focusKey.current}`)?.focus();
    focusKey.current = null;
  });

  const update = (key: PromptKey, value: string) => {
    setState((s) => ({ ...s, form: { ...s.form, [key]: value } }));
    if (errors[key]) setErrors((e) => ({ ...e, [key]: undefined }));
  };

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (pending || !dirty) return;
    const sent = form;
    save.mutate(
      { prompts: promptsPayload(sent, out.fields) },
      {
        // What was typed while saving stays; everything else shows what was stored.
        onSuccess: (saved) => {
          setErrors({});
          setState((s) => {
            const next = promptValuesFrom(saved);
            return { source: saved, baseline: next, form: rebasePrompts(sent, s.form, next) };
          });
        },
        onError: (e) => {
          const found = promptFieldErrors(e, PROMPT_KEYS);
          if (found === null) return;
          setErrors(found);
          setOpen((o) => ({ ...o, ...Object.fromEntries(Object.keys(found).map((key) => [key, true])) }));
          focusKey.current = PROMPT_KEYS.find((key) => found[key]) ?? null;
        },
      },
    );
  }

  function onResetAll() {
    if (pending) return;
    resetDone.current = false;
    reset.mutate(
      { prompts: {}, reset: true },
      {
        onSuccess: (saved) => {
          const next = promptValuesFrom(saved);
          setState({ source: saved, baseline: next, form: next });
          setErrors({});
          resetDone.current = true;
          setConfirming(false);
        },
        onError: () => setConfirming(false),
      },
    );
  }

  const card = (field: PromptField) => (
    <PromptCard
      key={field.key}
      field={field}
      value={shown[field.key]}
      admin={admin}
      open={open[field.key]}
      onOpenChange={(next) => setOpen((o) => ({ ...o, [field.key]: next }))}
      onChange={(value) => update(field.key, value)}
      error={admin ? errors[field.key] : undefined}
      note={field.key === "system" ? SYSTEM_NOTE : undefined}
    />
  );
  const [system, ...sections] = out.fields;

  return (
    <form onSubmit={onSubmit} className="grid gap-4" aria-label="Liturgy prompts">
      {admin ? null : (
        <Alert role="status">
          <AlertDescription>{ADMINS_ONLY}</AlertDescription>
        </Alert>
      )}
      {card(system)}
      <div className="grid gap-1">
        <h3 className="text-base font-medium">Section prompts</h3>
        <p className="text-sm text-muted-foreground">{`${out.placeholder_help} ${BRACE_NOTE}`}</p>
      </div>
      {sections.map(card)}
      {admin ? (
        <div
          data-keyboard-open={keyboardOpen ? "" : undefined}
          className={cn(
            "sticky bottom-0 z-10 flex flex-wrap gap-2 border-t bg-background/95 pt-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] backdrop-blur",
            // Below md with the iPhone keyboard open the footer sits after the last card, reachable and not covering the box.
            keyboardOpen && "max-md:static",
          )}
        >
          <PendingButton type="submit" size="touch" className="w-full sm:w-fit" pending={save.isPending} disabled={!dirty || reset.isPending}>
            Save prompts
          </PendingButton>
          {out.fields.some((f) => f.customized) ? (
            <Button
              type="button"
              variant="outline"
              size="touch"
              className="w-full sm:w-fit"
              disabled={pending}
              onClick={() => setConfirming(true)}
            >
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

function PromptCard({
  field,
  value,
  admin,
  open,
  onOpenChange,
  onChange,
  error,
  note,
}: {
  field: PromptField;
  value: string;
  admin: boolean;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onChange: (value: string) => void;
  error?: string;
  note?: string;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);
  useAutosize(ref, value, open);
  const id = `prompt-${field.key}`;
  const title = field.key === "system" ? SYSTEM_TITLE : field.label;
  const customized = isCustomized(value, field);
  const describedBy = [note && `${id}-note`, error && `${id}-error`].filter(Boolean).join(" ") || undefined;
  return (
    <Collapsible open={open} onOpenChange={onOpenChange} className="rounded-lg border">
      <CollapsibleTrigger className="flex min-h-11 w-full items-center gap-2 rounded-lg px-4 py-2 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring">
        <span className="min-w-0 flex-1 text-sm font-medium">{title}</span>
        {customized ? <Badge variant="secondary">Customized</Badge> : null}
        <ChevronDownIcon aria-hidden="true" className={cn("size-4 shrink-0 transition-transform", open && "rotate-180")} />
      </CollapsibleTrigger>
      <CollapsibleContent className="grid gap-2 px-4 pb-4">
        <label htmlFor={id} className="sr-only">
          {title}
        </label>
        <Textarea
          id={id}
          ref={ref}
          value={value}
          readOnly={!admin}
          maxLength={MAX_PROMPT_LENGTH}
          rows={TALL.has(field.key) ? 8 : 4}
          className="max-h-[60vh] overflow-y-auto"
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          onChange={(e) => onChange(e.target.value)}
        />
        {note ? (
          <p id={`${id}-note`} className="text-sm text-muted-foreground">
            {note}
          </p>
        ) : null}
        {error ? (
          <p id={`${id}-error`} role="alert" className="text-sm text-destructive">
            {error}
          </p>
        ) : null}
        {admin ? (
          <Button
            type="button"
            variant="link"
            className="h-11 justify-self-start px-0 md:h-auto"
            disabled={value === field.default}
            onClick={() => {
              onChange(field.default);
              // The button is disabled once the default is back: focus stays in the card, on its box.
              ref.current?.focus();
            }}
          >
            Reset to default
          </Button>
        ) : null}
      </CollapsibleContent>
    </Collapsible>
  );
}

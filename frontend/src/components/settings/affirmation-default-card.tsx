"use client";

import { ChevronDownIcon } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { ErrorState } from "@/components/app/error-state";
import { CreedText } from "@/components/builder/liturgy/affirmation-card";
import { PendingButton } from "@/components/app/pending-button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import type { AffirmationConfig, ChurchAffirmation, ChurchProfile } from "@/lib/api/types";
import { isAdmin } from "@/lib/church";
import { useChurch } from "@/lib/church-context";
import { APOSTLES_DEFAULT, type AffirmationChoice } from "@/lib/draft/schema";
import { useChurchProfile, useUpdateChurch } from "@/lib/queries/church";
import { useLiturgyConfig } from "@/lib/queries/liturgy";
import { useAutosize } from "@/lib/use-autosize";
import { cn } from "@/lib/utils";

export const AFFIRMATION_INTRO = "What the Liturgy step starts with for a new service. Each service can still change it or switch it off.";
export const AFFIRMATION_ADMINS_ONLY = "Only admins can change the default. You can read it below.";
export const OWN_TEXT_HELP = "Paste your church's own text, for example A Brief Statement of Faith.";
export const OWN_TEXT_REQUIRED = "Type your church's own text, or choose a creed.";
export const AFFIRMATION_SAVED = "Affirmation of Faith default saved.";

/** The form as the server stores it: the text trimmed with "\n" line ends, and only for "own". */
function cleaned(form: ChurchAffirmation): ChurchAffirmation {
  return { choice: form.choice, text: form.choice === "own" ? form.text.replace(/\r\n?/g, "\n").trim() : "" };
}

function same(a: ChurchAffirmation, b: ChurchAffirmation): boolean {
  const x = cleaned(a);
  const y = cleaned(b);
  return x.choice === y.choice && x.text === y.text;
}

function fromProfile(profile: ChurchProfile): ChurchAffirmation {
  return profile.default_affirmation ?? APOSTLES_DEFAULT;
}

/**
 * Settings → Liturgy's Affirmation of Faith card (affirmation spec, "Settings
 * → Liturgy: the church default"): the church's default choice and, for
 * "Your own text", its text. Owners and admins change it and press **Save
 * default** (`PATCH /church`); members read it. 6a's settings rules: newer
 * server data replaces the form unless it was edited, and `onDirtyChange`
 * tells the page, whose one leave guard covers both of its forms.
 */
export function AffirmationDefaultCard({ onDirtyChange }: { onDirtyChange: (dirty: boolean) => void }) {
  const church = useChurch();
  const profile = useChurchProfile(church.id);
  const config = useLiturgyConfig();
  // An API from before the affirmation spec sends no card data (and would refuse the default): no card.
  if (config.data && !config.data.affirmation) return null;
  let body;
  if (profile.data && config.data) {
    body = <AffirmationForm profile={profile.data} config={config.data.affirmation} onDirtyChange={onDirtyChange} />;
  } else if (profile.isError || config.isError) {
    const failed = profile.isError ? profile : config;
    body = <ErrorState error={failed.error} onRetry={() => void failed.refetch()} retrying={failed.isFetching} />;
  } else {
    body = (
      <div role="status" aria-label="Loading" className="grid gap-3">
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-11 w-full" />
      </div>
    );
  }
  return (
    <section aria-labelledby="affirmation-default-title" className="grid gap-4">
      <div className="grid gap-1">
        <h2 id="affirmation-default-title" className="text-lg font-semibold">
          Affirmation of Faith
        </h2>
        <p className="text-sm text-muted-foreground">{AFFIRMATION_INTRO}</p>
      </div>
      {body}
    </section>
  );
}

type FormState = { source: ChurchProfile; baseline: ChurchAffirmation; form: ChurchAffirmation };

function AffirmationForm({
  profile,
  config,
  onDirtyChange,
}: {
  profile: ChurchProfile;
  config: AffirmationConfig;
  onDirtyChange: (dirty: boolean) => void;
}) {
  const admin = isAdmin(profile.role);
  const save = useUpdateChurch({ savedMessage: AFFIRMATION_SAVED });
  const textRef = useRef<HTMLTextAreaElement>(null);
  const [open, setOpen] = useState(false);
  const [state, setState] = useState<FormState>(() => {
    const form = fromProfile(profile);
    return { source: profile, baseline: form, form };
  });
  const { form, baseline } = state;
  // A member (or an admin demoted meanwhile) reads what is stored, never an unsaved edit.
  const shown = admin ? form : fromProfile(profile);
  const dirty = admin && !same(baseline, form);
  const ownBlank = shown.choice === "own" && shown.text.trim() === "";
  useAutosize(textRef, shown.text, shown.choice === "own");

  // Newer server data (a refetch, or this form's own save): the form follows it unless it was edited (6a).
  if (profile !== state.source) {
    const next = fromProfile(profile);
    setState({ source: profile, baseline: next, form: same(baseline, form) ? next : form });
  }

  useEffect(() => onDirtyChange(dirty), [dirty, onDirtyChange]);

  const chosen = config.choices.find((choice) => choice.key === shown.choice);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (save.isPending || !dirty || ownBlank) return;
    save.mutate({ default_affirmation: cleaned(form) });
  }

  return (
    <form onSubmit={onSubmit} className="grid gap-3 rounded-lg border p-4" aria-label="Affirmation of Faith default">
      {admin ? null : (
        <Alert role="status">
          <AlertDescription>{AFFIRMATION_ADMINS_ONLY}</AlertDescription>
        </Alert>
      )}
      <RadioGroup
        aria-label="Default Affirmation of Faith"
        value={shown.choice}
        disabled={!admin}
        onValueChange={(value) => setState((s) => ({ ...s, form: { ...s.form, choice: value as AffirmationChoice } }))}
        className="gap-0"
      >
        {config.choices.map((choice) => (
          <label key={choice.key} className="flex min-h-11 cursor-pointer items-center gap-3 text-sm">
            <RadioGroupItem value={choice.key} />
            {choice.label}
          </label>
        ))}
      </RadioGroup>
      {shown.choice === "own" ? (
        <div className="grid gap-1.5">
          <label htmlFor="affirmation-default-text" className="sr-only">
            Your church&apos;s own text
          </label>
          <Textarea
            id="affirmation-default-text"
            ref={textRef}
            value={shown.text}
            readOnly={!admin}
            rows={6}
            className="max-h-[60vh] overflow-y-auto"
            aria-describedby="affirmation-default-help"
            aria-invalid={admin && ownBlank && dirty ? true : undefined}
            onChange={(e) => setState((s) => ({ ...s, form: { ...s.form, text: e.target.value } }))}
          />
          <p id="affirmation-default-help" className="text-sm text-muted-foreground">
            {admin && ownBlank ? OWN_TEXT_REQUIRED : OWN_TEXT_HELP}
          </p>
        </div>
      ) : chosen ? (
        <Collapsible open={open} onOpenChange={setOpen} className="grid gap-2">
          <CollapsibleTrigger className="flex min-h-11 items-center gap-2 text-left text-sm font-medium">
            <ChevronDownIcon aria-hidden="true" className={cn("size-4 transition-transform", !open && "-rotate-90")} />
            Show creed text
          </CollapsibleTrigger>
          <CollapsibleContent className="grid gap-2">
            <CreedText text={chosen.text} />
            {chosen.credit ? <p className="text-xs text-muted-foreground">{chosen.credit}</p> : null}
          </CollapsibleContent>
        </Collapsible>
      ) : null}
      {admin ? (
        <div>
          <PendingButton type="submit" size="touch" className="w-full sm:w-fit" pending={save.isPending} disabled={!dirty || ownBlank}>
            Save default
          </PendingButton>
        </div>
      ) : null}
    </form>
  );
}

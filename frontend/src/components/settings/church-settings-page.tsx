"use client";

import { useState, type FormEvent, type ReactNode } from "react";

import { ErrorState } from "@/components/app/error-state";
import { LeaveGuard } from "@/components/app/leave-guard";
import { PendingButton } from "@/components/app/pending-button";
import { TimezoneCombobox } from "@/components/app/timezone-combobox";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api/client";
import type { ChurchProfile } from "@/lib/api/types";
import { isAdmin } from "@/lib/church";
import { useChurch } from "@/lib/church-context";
import { useUpdateChurch, useChurchProfile } from "@/lib/queries/church";
import { useHymnals } from "@/lib/queries/hymns";
import { useTranslations } from "@/lib/queries/reference";
import {
  diffProfile,
  hasChanges,
  hymnalItems,
  profileFormFrom,
  rebaseProfile,
  translationItems,
  type ProfileForm,
} from "@/lib/settings/profile";
import { browserTimezone, listTimezones, timezoneLabel } from "@/lib/timezones";

export const ADMINS_ONLY = "Only admins can edit the church profile.";
export const TIMEZONE_NOT_RECOGNIZED = "Timezone not recognized. Choose one from the list.";
// A change reaches every service that follows the church's choice (a service whose own pick equals it follows too:
// the draft stores no pick then), and a saved service reopens with the church's translation (6a-1 owner question 11).
export const TRANSLATION_HELP =
  "Used for passage text in the builder, in every service that has not switched to another translation (saved services too, when reopened). Anyone can switch it for a single service.";
export const HYMNAL_HELP =
  "The hymnal the builder opens with, in every unsaved service that has not switched to another hymnal. You can switch hymnals for a single service.";
export const BENEDICTION_HELP =
  "Pre-fills the Benediction card in each new service, and in unsaved services whose card still shows the default. Leave it blank to let the AI write the benediction.";
const NO_HYMNALS = "Your church has no hymns yet, so there is no default hymnal.";
const NO_BENEDICTION = "None. The AI writes the benediction.";

/**
 * `/settings/church` (slice 6a-1; 6a spec "Church profile"): the church's
 * name, time zone, default Bible translation, default hymnal and default
 * Benediction. Owners and admins edit them and save only what changed
 * (`PATCH /church`); members read them, with a note that only admins can
 * edit. 6a's rules for settings forms: newer server data rebases the form
 * (an untouched field takes it, an edited one keeps the edit), and leaving
 * with unsaved edits asks first (`LeaveGuard`).
 */
export function ChurchSettingsPage() {
  const church = useChurch();
  const profile = useChurchProfile(church.id);
  let body: ReactNode;
  if (profile.data) {
    body = isAdmin(profile.data.role) ? <ProfileFormView profile={profile.data} /> : <ProfileSummary profile={profile.data} />;
  } else if (profile.isError) {
    body = <ErrorState error={profile.error} onRetry={() => void profile.refetch()} retrying={profile.isFetching} />;
  } else {
    body = (
      <div role="status" aria-label="Loading" className="grid gap-4">
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-28 w-full" />
      </div>
    );
  }
  return (
    <section aria-labelledby="church-profile-title" className="grid gap-4">
      <h2 id="church-profile-title" className="text-lg font-semibold">
        Church profile
      </h2>
      {body}
    </section>
  );
}

type Field = keyof ProfileForm;

/** This device's time zone when the browser lists it (or lists none), else null: the shortcut is not offered. */
function listedDeviceZone(): string | null {
  const zone = browserTimezone();
  const zones = listTimezones();
  return zone !== null && (zones === null || zones.includes(zone)) ? zone : null;
}
type FormState = { source: ChurchProfile; baseline: ProfileForm; form: ProfileForm };

function FieldNote({ id, children, error }: { id: string; children: ReactNode; error?: boolean }) {
  return (
    <p id={id} role={error ? "alert" : undefined} className={error ? "text-sm text-destructive" : "text-sm text-muted-foreground"}>
      {children}
    </p>
  );
}

function ProfileFormView({ profile }: { profile: ChurchProfile }) {
  const save = useUpdateChurch();
  const translations = useTranslations();
  const hymnals = useHymnals();
  const [state, setState] = useState<FormState>(() => {
    const form = profileFormFrom(profile);
    return { source: profile, baseline: form, form };
  });
  const [errors, setErrors] = useState<Partial<Record<Field, string>>>({});
  const [deviceZone] = useState(listedDeviceZone);
  const { form, baseline } = state;
  const changed = hasChanges(baseline, form);

  // Newer server data (a refetch, or this page's own save in the cache): rebase (6a).
  if (profile !== state.source) {
    const next = profileFormFrom(profile);
    setState({ source: profile, baseline: next, form: rebaseProfile(baseline, form, next) });
  }

  const update = (field: Field, value: string) => {
    setState((s) => ({ ...s, form: { ...s.form, [field]: value } }));
    if (errors[field]) setErrors((e) => ({ ...e, [field]: undefined }));
  };

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (save.isPending || !changed) return;
    const sent = form;
    save.mutate(diffProfile(baseline, sent), {
      // What was typed while saving stays; everything else shows what was stored.
      onSuccess: (saved) =>
        setState((s) => {
          const next = profileFormFrom(saved);
          return { source: saved, baseline: next, form: rebaseProfile(sent, s.form, next) };
        }),
      onError: (e) => {
        if (!(e instanceof ApiError) || e.status !== 422 || !e.fields) return;
        const found = Object.fromEntries(
          Object.entries(e.fields).filter(([key]) => key in form),
        ) as Partial<Record<Field, string>>;
        setErrors(found);
        const first = (Object.keys(found) as Field[])[0];
        if (first) document.getElementById(`church-${first}`)?.focus();
      },
    });
  }

  const describedBy = (...ids: (string | false | undefined)[]) => ids.filter(Boolean).join(" ") || undefined;
  const errorNote = (field: Field) =>
    errors[field] ? (
      <FieldNote id={`church-${field}-error`} error>
        {errors[field]}
      </FieldNote>
    ) : null;

  // Until GET /translations answers (or when it fails), the profile's own facts: the translation in effect, and a
  // stored one that differs from it is one this server does not offer.
  const translationChoices = translations.data
    ? translationItems(translations.data, profile.bible_translation)
    : {
        [profile.effective_translation]: profile.effective_translation_label,
        ...translationItems(undefined, profile.bible_translation === profile.effective_translation ? null : profile.bible_translation),
      };
  const hymnalChoices = hymnals.data
    ? hymnalItems(hymnals.data, profile.default_hymnal)
    : form.default_hymnal
      ? { [form.default_hymnal]: form.default_hymnal }
      : {};
  // From the church's hymnals (GET /hymnals), never from the choices: a stale stored default is not "your only hymnal".
  const churchHymnals = hymnals.data?.items.map((h) => h.code) ?? null;
  const noHymnals = churchHymnals !== null ? churchHymnals.length === 0 : form.default_hymnal === "";
  const onlyHymnal = churchHymnals !== null && churchHymnals.length === 1 && churchHymnals[0] === form.default_hymnal;

  return (
    <form onSubmit={onSubmit} className="grid gap-5" aria-label="Church profile">
      <div className="grid gap-1.5">
        <Label htmlFor="church-name">Church name</Label>
        <Input
          id="church-name"
          value={form.name}
          maxLength={200}
          className="h-11"
          aria-invalid={errors.name ? true : undefined}
          aria-describedby={describedBy(errors.name && "church-name-error")}
          onChange={(e) => update("name", e.target.value)}
        />
        {errorNote("name")}
      </div>

      <div className="grid gap-1">
        <TimezoneCombobox
          id="church-timezone"
          value={form.timezone}
          onChange={(value) => update("timezone", value)}
          error={errors.timezone}
          warning={!profile.timezone_valid && form.timezone === profile.timezone ? TIMEZONE_NOT_RECOGNIZED : null}
        />
        {deviceZone !== null && deviceZone !== form.timezone ? (
          <Button
            type="button"
            variant="link"
            className="h-auto min-h-11 justify-self-start px-0 text-left whitespace-normal md:min-h-8"
            onClick={() => update("timezone", deviceZone)}
          >
            {`Use this device's time zone (${timezoneLabel(deviceZone)})`}
          </Button>
        ) : null}
      </div>

      <div className="grid gap-1.5">
        <Label htmlFor="church-bible_translation">Default Bible translation</Label>
        <Select
          value={form.bible_translation}
          items={translationChoices}
          onValueChange={(value) => {
            if (typeof value === "string") update("bible_translation", value);
          }}
        >
          <SelectTrigger
            id="church-bible_translation"
            className="h-11 w-full data-[size=default]:h-11"
            aria-invalid={errors.bible_translation ? true : undefined}
            aria-describedby={describedBy("church-bible_translation-help", errors.bible_translation && "church-bible_translation-error")}
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(translationChoices).map(([value, label]) => (
              <SelectItem key={value} value={value}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <FieldNote id="church-bible_translation-help">{TRANSLATION_HELP}</FieldNote>
        {errorNote("bible_translation")}
      </div>

      <div className="grid gap-1.5">
        {noHymnals ? (
          <>
            <p className="text-sm font-medium">Default hymnal</p>
            <p className="text-sm text-muted-foreground">{NO_HYMNALS}</p>
          </>
        ) : onlyHymnal ? (
          <>
            <p className="text-sm font-medium">Default hymnal</p>
            <p className="text-sm">{`${form.default_hymnal} (your only hymnal)`}</p>
          </>
        ) : (
          <>
            <Label htmlFor="church-default_hymnal">Default hymnal</Label>
            <Select
              value={form.default_hymnal}
              items={hymnalChoices}
              onValueChange={(value) => {
                if (typeof value === "string") update("default_hymnal", value);
              }}
            >
              <SelectTrigger
                id="church-default_hymnal"
                className="h-11 w-full data-[size=default]:h-11"
                aria-invalid={errors.default_hymnal ? true : undefined}
                aria-describedby={describedBy("church-default_hymnal-help", errors.default_hymnal && "church-default_hymnal-error")}
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(hymnalChoices).map(([value, label]) => (
                  <SelectItem key={value} value={value}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <FieldNote id="church-default_hymnal-help">{HYMNAL_HELP}</FieldNote>
            {errorNote("default_hymnal")}
          </>
        )}
      </div>

      <div className="grid gap-1.5">
        <Label htmlFor="church-default_benediction">Default Benediction</Label>
        <Textarea
          id="church-default_benediction"
          value={form.default_benediction}
          maxLength={4000}
          rows={4}
          className="max-h-[60vh] overflow-y-auto"
          aria-invalid={errors.default_benediction ? true : undefined}
          aria-describedby={describedBy(
            "church-default_benediction-help",
            errors.default_benediction && "church-default_benediction-error",
          )}
          onChange={(e) => update("default_benediction", e.target.value)}
        />
        <FieldNote id="church-default_benediction-help">{BENEDICTION_HELP}</FieldNote>
        {errorNote("default_benediction")}
      </div>

      <PendingButton type="submit" size="touch" className="w-full sm:w-fit" pending={save.isPending} disabled={!changed}>
        Save profile
      </PendingButton>
      <LeaveGuard when={changed} />
    </form>
  );
}

function SummaryItem({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid gap-0.5">
      <dt className="text-sm font-medium">{label}</dt>
      <dd className="text-sm whitespace-pre-line break-words">{children}</dd>
    </div>
  );
}

/** The hymnal the builder opens with, noting a stored default the church no longer has. */
function summaryHymnal(profile: ChurchProfile): string | null {
  const { default_hymnal: stored, effective_hymnal: effective } = profile;
  if (effective === null) return null;
  return stored !== null && stored !== effective
    ? `${effective} (the builder uses this; ${stored} is no longer in your hymnals)`
    : effective;
}

/** What a member sees: the profile as plain text, no controls (as on Bulletin settings). */
function ProfileSummary({ profile }: { profile: ChurchProfile }) {
  const hymnal = summaryHymnal(profile);
  return (
    <div className="grid gap-4">
      <Alert role="status">
        <AlertDescription>{ADMINS_ONLY}</AlertDescription>
      </Alert>
      <dl className="grid gap-3 rounded-lg border p-4">
        <SummaryItem label="Church name">{profile.name}</SummaryItem>
        <SummaryItem label="Time zone">{timezoneLabel(profile.timezone)}</SummaryItem>
        <SummaryItem label="Default Bible translation">{profile.effective_translation_label}</SummaryItem>
        <SummaryItem label="Default hymnal">{hymnal ?? <span className="text-muted-foreground">{NO_HYMNALS}</span>}</SummaryItem>
        <SummaryItem label="Default Benediction">
          {profile.default_benediction.trim() !== "" ? (
            profile.default_benediction
          ) : (
            <span className="text-muted-foreground">{NO_BENEDICTION}</span>
          )}
        </SummaryItem>
      </dl>
    </div>
  );
}

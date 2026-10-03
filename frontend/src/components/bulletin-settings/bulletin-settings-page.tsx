"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  useEffect,
  useRef,
  useState,
  type ComponentProps,
  type FormEvent,
  type MouseEvent,
  type ReactNode,
} from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { ErrorState } from "@/components/app/error-state";
import { PageHeader } from "@/components/app/page-header";
import { PendingButton } from "@/components/app/pending-button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api/client";
import type { BulletinSettings } from "@/lib/api/types";
import {
  addressError,
  ELEMENTS,
  formErrors,
  formFromSettings,
  isDirty,
  MAX_LENGTH,
  rebaseForm,
  ROLES,
  settingsFromForm,
  type BulletinForm,
  type ElementKey,
  type FormField,
  type Role,
  type TextField,
} from "@/lib/bulletin-settings";
import { isAdmin } from "@/lib/church";
import { useChurch } from "@/lib/church-context";
import { useBulletinSettings, useSaveBulletinSettings } from "@/lib/queries/bulletin-settings";

export const PAGE_DESCRIPTION = "What every printed bulletin uses. A field left blank is left off the bulletin.";
export const ADMINS_ONLY = "Only admins can edit the bulletin settings. You can read them below.";
export const DISCARD_TITLE = "Discard unsaved changes?";
const DISCARD_BODY = "Your changes on this page haven't been saved.";
const NOT_FILLED_IN = "Not filled in";
const BACK_HREF = "/builder/review";
const NO_ONE: string = "none"; // "No one" leads this part: a real choice, not a placeholder (F §4.9 item 3)
const LEADER_ITEMS: Record<string, string> = {
  [NO_ONE]: "No one",
  ...Object.fromEntries(ROLES.map((r) => [r.key, r.label])),
};

type TextSpec = { field: TextField; label: string; help?: string; long?: boolean };

const CHURCH_FIELDS: readonly TextSpec[] = [
  { field: "phone", label: "Phone" },
  { field: "email", label: "Email" },
  { field: "website", label: "Website" },
  { field: "facebook", label: "Facebook name", help: "Printed as FB: and the name." },
];
const SERVICE_FIELDS: readonly TextSpec[] = [
  { field: "service_time", label: "Service time", help: "Printed across from the date, for example 10:30 a.m." },
];
const PEOPLE_FIELDS: readonly TextSpec[] = [
  { field: "worship_leader", label: "Worship leader" },
  { field: "liturgist", label: "Liturgist" },
  { field: "organist", label: "Organist" },
];
const WORDS_FIELDS: readonly TextSpec[] = [
  { field: "stand_note", label: "Stand note", help: "Printed at the end of the service, after a star." },
  { field: "gloria_patri_words", label: "Gloria Patri words", long: true },
];

/**
 * The phone, email and website keyboards (no `type="email"` or `type="url"`:
 * the browser would refuse a website typed as "example.com"). The browser's
 * own autofill is off: these are the church's details, not the user's.
 */
const INPUT_PROPS: Partial<Record<TextField, ComponentProps<"input">>> = {
  phone: { type: "tel", inputMode: "tel", autoComplete: "off" },
  email: { inputMode: "email", autoComplete: "off", autoCapitalize: "none", spellCheck: false },
  website: { inputMode: "url", autoComplete: "off", autoCapitalize: "none", spellCheck: false },
};

function PageSkeleton() {
  return (
    <div role="status" aria-label="Loading" className="grid gap-4">
      {[0, 1, 2].map((i) => (
        <Skeleton key={i} className="h-40 w-full" />
      ))}
    </div>
  );
}

/**
 * `/bulletin-settings` (printed bulletin spec, PR 2a; PR 2 planning answers
 * 1-3): the church's standing bulletin settings, which every member's
 * printed bulletin uses. Admins and owners edit and save the whole form;
 * members read a plain summary, with a note that only admins can edit it.
 * Until 6a folds it into Settings, the Printed bulletin card on Review & send
 * links here.
 *
 * The settings are fetched again on opening the page (even when cached), and
 * the form shows only once that fetch is back, so it never starts from an
 * older value. 6a's rules for settings forms: newer server data rebases the
 * form (`rebaseForm`), and leaving with unsaved edits asks first (the
 * browser's warning on a reload or close, "Discard unsaved changes?" on
 * **Back to Review & send**).
 */
export function BulletinSettingsPage() {
  const church = useChurch();
  const canEdit = isAdmin(church.role);
  const settings = useBulletinSettings({ fresh: true });
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [leaving, setLeaving] = useState(false);
  // Shown once the fetch made on opening the page is back; then kept, so a failed background refetch keeps the form.
  if (!ready && settings.isFetchedAfterMount && settings.isSuccess) setReady(true);

  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  function onBack(event: MouseEvent<HTMLAnchorElement>) {
    if (!dirty) return;
    event.preventDefault();
    setLeaving(true);
  }

  return (
    <main className="mx-auto grid w-full max-w-2xl content-start gap-4 px-4 py-4">
      <PageHeader
        title="Bulletin settings"
        description={PAGE_DESCRIPTION}
        actions={
          <Link href={BACK_HREF} onClick={onBack} className={buttonVariants({ variant: "outline", size: "touch" })}>
            Back to Review &amp; send
          </Link>
        }
      />
      {ready && settings.data ? (
        canEdit ? (
          <SettingsForm settings={settings.data} onDirtyChange={setDirty} />
        ) : (
          <SettingsSummary settings={settings.data} />
        )
      ) : settings.isError ? (
        <ErrorState error={settings.error} onRetry={() => void settings.refetch()} retrying={settings.isFetching} />
      ) : (
        <PageSkeleton />
      )}
      <ConfirmDialog
        open={leaving}
        onOpenChange={setLeaving}
        title={DISCARD_TITLE}
        description={DISCARD_BODY}
        confirmLabel="Discard changes"
        cancelLabel="Keep editing"
        destructive
        onConfirm={() => {
          setLeaving(false);
          setDirty(false);
          router.push(BACK_HREF);
        }}
      />
    </main>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <fieldset className="grid gap-4 rounded-lg border p-4">
      <legend className="px-1 text-base font-medium">{title}</legend>
      {children}
    </fieldset>
  );
}

function FieldError({ id, message }: { id: string; message?: string }) {
  return message ? (
    <p id={id} role="alert" className="text-sm text-destructive">
      {message}
    </p>
  ) : null;
}

type FormState = { source: BulletinSettings; baseline: BulletinForm; form: BulletinForm };

function SettingsForm({
  settings,
  onDirtyChange,
}: {
  settings: BulletinSettings;
  onDirtyChange: (dirty: boolean) => void;
}) {
  const save = useSaveBulletinSettings();
  const [state, setState] = useState<FormState>(() => {
    const form = formFromSettings(settings);
    return { source: settings, baseline: form, form };
  });
  const [errors, setErrors] = useState<Partial<Record<FormField, string>>>({});
  const addressRef = useRef<HTMLTextAreaElement>(null);
  const { form, baseline } = state;
  const dirty = isDirty(baseline, form);

  // Newer server data (a refetch, or this page's own save in the cache): rebase (6a).
  if (settings !== state.source) {
    const next = formFromSettings(settings);
    setState({ source: settings, baseline: next, form: rebaseForm(baseline, form, next) });
  }

  useEffect(() => onDirtyChange(dirty), [dirty, onDirtyChange]);

  const update = (field: FormField | null, change: (f: BulletinForm) => BulletinForm) => {
    setState((s) => ({ ...s, form: change(s.form) }));
    if (field && errors[field]) setErrors((e) => ({ ...e, [field]: undefined }));
  };
  const setLeader = (key: ElementKey, role: Role | null) =>
    update(null, (f) => {
      const leaders = { ...f.leaders };
      if (role === null) delete leaders[key];
      else leaders[key] = role;
      return { ...f, leaders };
    });
  const setStarred = (key: ElementKey, on: boolean) =>
    update(null, (f) => ({ ...f, starred: on ? [...f.starred, key] : f.starred.filter((k) => k !== key) }));

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (save.isPending) return;
    const problem = addressError(form.address);
    setErrors(problem ? { address: problem } : {});
    if (problem) {
      addressRef.current?.focus();
      return;
    }
    const sent = form;
    save.mutate(settingsFromForm(sent), {
      // What was typed while saving stays; everything else shows what was stored.
      onSuccess: (saved) =>
        setState((s) => {
          const next = formFromSettings(saved);
          return { ...s, baseline: next, form: rebaseForm(sent, s.form, next) };
        }),
      onError: (e) => {
        if (!(e instanceof ApiError) || e.status !== 422 || !e.fields) return;
        const found = formErrors(e.fields);
        setErrors(found);
        const first = (Object.keys(found) as FormField[])[0];
        if (first) document.getElementById(`bulletin-${first}`)?.focus();
      },
    });
  }

  const describedBy = (...ids: (string | false | undefined)[]) => ids.filter(Boolean).join(" ") || undefined;

  const text = ({ field, label, help, long }: TextSpec) => {
    const id = `bulletin-${field}`;
    const error = errors[field];
    const props = {
      id,
      value: form[field],
      maxLength: MAX_LENGTH[field],
      "aria-invalid": error ? true : undefined,
      "aria-describedby": describedBy(help && `${id}-help`, error && `${id}-error`),
      onChange: (e: { target: { value: string } }) => update(field, (f) => ({ ...f, [field]: e.target.value })),
    };
    return (
      <div key={field} className="grid gap-1.5">
        <Label htmlFor={id}>{label}</Label>
        {long ? <Textarea {...props} /> : <Input {...INPUT_PROPS[field]} {...props} className="h-11" />}
        {help ? (
          <p id={`${id}-help`} className="text-sm text-muted-foreground">
            {help}
          </p>
        ) : null}
        <FieldError id={`${id}-error`} message={error} />
      </div>
    );
  };

  return (
    <form onSubmit={onSubmit} className="grid gap-4" aria-label="Bulletin settings">
      <Section title="Church details">
        <div className="grid gap-1.5">
          <Label htmlFor="bulletin-address">Address</Label>
          <Textarea
            id="bulletin-address"
            ref={addressRef}
            value={form.address}
            aria-invalid={errors.address ? true : undefined}
            aria-describedby={describedBy("bulletin-address-help", errors.address && "bulletin-address-error")}
            onChange={(e) => update("address", (f) => ({ ...f, address: e.target.value }))}
          />
          <p id="bulletin-address-help" className="text-sm text-muted-foreground">
            Up to 3 lines, as printed on the cover.
          </p>
          <FieldError id="bulletin-address-error" message={errors.address} />
        </div>
        {CHURCH_FIELDS.map(text)}
      </Section>
      <Section title="Service">{SERVICE_FIELDS.map(text)}</Section>
      <Section title="Who leads">{PEOPLE_FIELDS.map(text)}</Section>
      <Section title="Each part">
        <p className="text-sm text-muted-foreground">
          Who leads each part, and the parts the congregation stands for (printed with a star).
        </p>
        <ul className="grid gap-3">
          {ELEMENTS.map(({ key, label }) => (
            <li key={key} className="grid gap-2 border-t pt-3 first:border-t-0 first:pt-0 sm:grid-cols-[1fr_auto_auto] sm:items-center">
              <span className="text-sm font-medium">{label}</span>
              <Select
                value={form.leaders[key] ?? NO_ONE}
                items={LEADER_ITEMS}
                onValueChange={(value) => {
                  if (typeof value === "string") setLeader(key, value === NO_ONE ? null : (value as Role));
                }}
              >
                <SelectTrigger aria-label={`${label}: led by`} className="h-11 w-full sm:w-44 data-[size=default]:h-11">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(LEADER_ITEMS).map(([value, name]) => (
                    <SelectItem key={value} value={value}>
                      {name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <label className="flex h-11 items-center gap-3 text-sm">
                <Switch
                  checked={form.starred.includes(key)}
                  onCheckedChange={(checked) => setStarred(key, checked)}
                  aria-label={`${label}: congregation stands`}
                  className="after:-inset-y-3.5"
                />
                <span aria-hidden="true">Stands</span>
              </label>
            </li>
          ))}
        </ul>
      </Section>
      <Section title="Printed words">{WORDS_FIELDS.map(text)}</Section>
      <PendingButton type="submit" size="touch" className="w-full sm:w-fit" pending={save.isPending}>
        Save settings
      </PendingButton>
    </form>
  );
}

function SummarySection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="grid gap-3 rounded-lg border p-4">
      <h2 className="text-base font-medium">{title}</h2>
      {children}
    </section>
  );
}

function SummaryItem({ label, value }: { label: string; value: string | readonly string[] }) {
  const lines = typeof value === "string" ? [value].filter((v) => v.trim() !== "") : value;
  return (
    <div className="grid gap-0.5">
      <dt className="text-sm font-medium">{label}</dt>
      <dd className="text-sm whitespace-pre-line break-words">
        {lines.length > 0 ? lines.join("\n") : <span className="text-muted-foreground">{NOT_FILLED_IN}</span>}
      </dd>
    </div>
  );
}

/** What a member sees: the settings as plain text (6a's read-only view), no controls. */
function SettingsSummary({ settings }: { settings: BulletinSettings }) {
  const items = (specs: readonly TextSpec[]) =>
    specs.map(({ field, label }) => <SummaryItem key={field} label={label} value={settings[field]} />);
  const leader = (key: ElementKey) => ROLES.find((r) => r.key === settings.leaders[key])?.label ?? "No one";
  return (
    <div className="grid gap-4">
      <Alert role="status">
        <AlertDescription>{ADMINS_ONLY}</AlertDescription>
      </Alert>
      <SummarySection title="Church details">
        <dl className="grid gap-3">
          <SummaryItem label="Address" value={settings.address_lines} />
          {items(CHURCH_FIELDS)}
        </dl>
      </SummarySection>
      <SummarySection title="Service">
        <dl className="grid gap-3">{items(SERVICE_FIELDS)}</dl>
      </SummarySection>
      <SummarySection title="Who leads">
        <dl className="grid gap-3">{items(PEOPLE_FIELDS)}</dl>
      </SummarySection>
      <SummarySection title="Each part">
        <ul className="grid gap-1 text-sm">
          {ELEMENTS.map(({ key, label }) => (
            <li key={key}>
              <span className="font-medium">{label}:</span> {leader(key)}
              {settings.starred.includes(key) ? ", congregation stands" : ""}
            </li>
          ))}
        </ul>
      </SummarySection>
      <SummarySection title="Printed words">
        <dl className="grid gap-3">{items(WORDS_FIELDS)}</dl>
      </SummarySection>
    </div>
  );
}

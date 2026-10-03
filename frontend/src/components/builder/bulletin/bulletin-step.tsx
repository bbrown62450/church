"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import type { BulletinSettings } from "@/lib/api/types";
import { ELEMENTS, ROLES } from "@/lib/bulletin-settings";
import {
  keepCarried,
  MAX_LENGTH,
  setAnnouncement,
  setMusic,
  setPartLeader,
  setPastedText,
  setPerson,
  type Piece,
} from "@/lib/draft/bulletin";
import { useDraft } from "@/lib/draft/context";
import { effectivePicks } from "@/lib/draft/readings";
import type { AnnouncementKey, CarryKey, DraftV1, Person } from "@/lib/draft/schema";
import { useBulletinSettings } from "@/lib/queries/bulletin-settings";

import { useBulletinCarry } from "./use-bulletin-carry";
import { useKeptAlert } from "./use-kept-alert";

export const BULLETIN_INTRO =
  "Optional. What this week's printed bulletin adds to the service. A box left blank is left off the bulletin.";
export const FROM_LAST_WEEK = "From last week. Check before printing.";
export const CARRY_FAILED = "Last week's announcements could not be loaded.";
export const SETTINGS_FAILED = "Bulletin settings could not be loaded.";
export const WHO_LEADS_HELP = "From the bulletin settings. A change here is for this week only.";
export const PARTS_HELP = "A name here prints on that part this week only. Leave it blank for the usual leader.";
export const READINGS_HELP =
  "Paste a reading's text to print it instead of the text the app fetches, for a translation the app cannot fetch. Include the translation's notice if it asks for one.";
export const NO_READINGS = "Choose the readings on step 1 to paste their text.";

const ANNOUNCEMENTS: readonly { key: AnnouncementKey; label: string; long: boolean }[] = [
  { key: "ushers", label: "Ushers and counters", long: false },
  { key: "deacon", label: "Deacon of the week", long: false },
  { key: "coffee_hour", label: "Coffee hour", long: false },
  { key: "activities", label: "This week's activities", long: true },
  { key: "prayer_concerns", label: "Prayers and concerns", long: true },
  { key: "collection", label: "Items for collection", long: true },
  { key: "other", label: "Other announcements", long: true },
];

/**
 * "From last week. Check before printing." under a box still holding last
 * week's text, with "Keep as is" (named "Keep as is: {box}", its visible
 * words first, 2b-2 build review M3). Keep as is removes itself, so focus
 * moves to the box's field (`fieldId`, build review M2).
 */
function CarriedNote({ id, carryKey, name, fieldId }: { id: string; carryKey: CarryKey; name: string; fieldId: string }) {
  const { draft, update } = useDraft();
  if (!draft.bulletin.carried.includes(carryKey)) return null;
  function keep() {
    update((d) => keepCarried(d, carryKey));
    document.getElementById(fieldId)?.focus();
  }
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
      <p id={id} className="text-sm text-muted-foreground">
        {FROM_LAST_WEEK}
      </p>
      <Button type="button" variant="outline" size="touch" aria-label={`Keep as is: ${name}`} onClick={keep}>
        Keep as is
      </Button>
    </div>
  );
}

function Group({ id, title, help, children }: { id: string; title: string; help?: string; children: ReactNode }) {
  return (
    <fieldset aria-describedby={help ? `${id}-help` : undefined} className="grid min-w-0 gap-4 rounded-lg border p-4">
      <legend className="px-1 text-base font-medium">{title}</legend>
      {help ? (
        <p id={`${id}-help`} className="text-sm text-muted-foreground">
          {help}
        </p>
      ) : null}
      {children}
    </fieldset>
  );
}

function TextField({
  id,
  label,
  value,
  maxLength,
  long = false,
  describedBy,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  maxLength: number;
  long?: boolean;
  describedBy?: string;
  onChange: (value: string) => void;
}) {
  const shared = { id, value, maxLength, "aria-describedby": describedBy, onChange: (e: { target: { value: string } }) => onChange(e.target.value) };
  return (
    <div className="grid gap-2">
      <Label htmlFor={id}>{label}</Label>
      {long ? <Textarea {...shared} rows={3} /> : <Input {...shared} className="h-11" />}
    </div>
  );
}

function Music({ piece, name }: { piece: Piece; name: string }) {
  const { draft, update } = useDraft();
  const note = `bulletin-${piece}-carried`;
  const describedBy = draft.bulletin.carried.includes(piece) ? note : undefined;
  return (
    <div className="grid gap-3">
      <TextField
        id={`bulletin-${piece}-title`}
        label={`${name} title`}
        value={draft.bulletin[piece].title}
        maxLength={MAX_LENGTH.title}
        describedBy={describedBy}
        onChange={(v) => update((d) => setMusic(d, piece, "title", v))}
      />
      <TextField
        id={`bulletin-${piece}-composer`}
        label={`${name} composer`}
        value={draft.bulletin[piece].composer}
        maxLength={MAX_LENGTH.composer}
        describedBy={describedBy}
        onChange={(v) => update((d) => setMusic(d, piece, "composer", v))}
      />
      <CarriedNote id={note} carryKey={piece} name={name.toLowerCase()} fieldId={`bulletin-${piece}-title`} />
    </div>
  );
}

/** This week's name for a role: the week's change, else the settings' name. */
function weekName(draft: DraftV1, settings: BulletinSettings, role: Person): string {
  return draft.bulletin.people[role] ?? settings[role];
}

function WhoLeads() {
  const { draft, update } = useDraft();
  const settingsQuery = useBulletinSettings();
  const settings = settingsQuery.data;
  const [partsOpen, setPartsOpen] = useState(() => Object.keys(draft.bulletin.leaders).length > 0);
  // Kept while Try again runs; then focus goes to the first name (2b-2 build review M2).
  const failure = useKeptAlert(
    settings === undefined && settingsQuery.isError,
    settingsQuery.isFetching,
    settingsQuery.refetch,
    `bulletin-person-${ROLES[0].key}`,
  );
  if (settings === undefined && !failure.shown) {
    return (
      <Group id="bulletin-who" title="Who leads" help={WHO_LEADS_HELP}>
        <div role="status" aria-label="Loading who leads" className="grid gap-3">
          <Skeleton className="h-11 w-full" />
          <Skeleton className="h-11 w-full" />
          <Skeleton className="h-11 w-full" />
        </div>
      </Group>
    );
  }
  if (settings === undefined) {
    // Without the settings the usual names are unknown: no field that could store one as this week's change.
    return (
      <Group id="bulletin-who" title="Who leads" help={WHO_LEADS_HELP}>
        <div role="alert" className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <p className="text-sm">{SETTINGS_FAILED}</p>
          <Button type="button" variant="outline" size="touch" onClick={failure.retry}>
            Try again
          </Button>
        </div>
      </Group>
    );
  }
  return (
    <Group id="bulletin-who" title="Who leads" help={WHO_LEADS_HELP}>
      {ROLES.map(({ key, label }) => {
        const changed = draft.bulletin.people[key] !== null;
        return (
          <div key={key} className="grid gap-2">
            <TextField
              id={`bulletin-person-${key}`}
              label={label}
              value={weekName(draft, settings, key)}
              maxLength={MAX_LENGTH.person}
              describedBy={changed ? `bulletin-person-${key}-changed` : undefined}
              onChange={(v) => update((d) => setPerson(d, key, v === settings[key] ? null : v))}
            />
            {changed ? (
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <p id={`bulletin-person-${key}-changed`} className="text-sm text-muted-foreground">
                  Changed for this week.
                </p>
                <Button
                  type="button"
                  variant="outline"
                  size="touch"
                  aria-label={`Undo the change to ${label}`}
                  onClick={() => {
                    update((d) => setPerson(d, key, null));
                    // The button goes with the change: focus stays on the name (2b-2 build review M2).
                    document.getElementById(`bulletin-person-${key}`)?.focus();
                  }}
                >
                  Undo the change
                </Button>
              </div>
            ) : null}
          </div>
        );
      })}
      <Button
        type="button"
        variant="outline"
        size="touch"
        className="w-full sm:w-fit"
        aria-expanded={partsOpen}
        aria-controls={partsOpen ? "bulletin-parts" : undefined}
        onClick={() => setPartsOpen((open) => !open)}
      >
        Change who leads a part
      </Button>
      {partsOpen ? (
        <div id="bulletin-parts" className="grid gap-4">
          <p className="text-sm text-muted-foreground">{PARTS_HELP}</p>
          {ELEMENTS.map(({ key, label }) => {
            // The usual leader is the settings' name, not this week's change (plan review fix M6).
            const role = settings.leaders[key];
            const usual = role ? settings[role] : "";
            return (
              <div key={key} className="grid gap-2">
                <TextField
                  id={`bulletin-part-${key}`}
                  label={label}
                  value={draft.bulletin.leaders[key] ?? ""}
                  maxLength={MAX_LENGTH.person}
                  describedBy={`bulletin-part-${key}-usual`}
                  onChange={(v) => update((d) => setPartLeader(d, key, v))}
                />
                <p id={`bulletin-part-${key}-usual`} className="text-sm text-muted-foreground">
                  {usual ? `Usually ${usual}` : "Usually no one"}
                </p>
              </div>
            );
          })}
        </div>
      ) : null}
    </Group>
  );
}

function Announcements() {
  const { draft, update } = useDraft();
  return (
    <Group id="bulletin-announcements" title="Announcements">
      {ANNOUNCEMENTS.map(({ key, label, long }) => {
        const note = `bulletin-${key}-carried`;
        return (
          <div key={key} className="grid gap-2">
            <TextField
              id={`bulletin-${key}`}
              label={label}
              value={draft.bulletin.announcements[key]}
              maxLength={MAX_LENGTH[key]}
              long={long}
              describedBy={draft.bulletin.carried.includes(key) ? note : undefined}
              onChange={(v) => update((d) => setAnnouncement(d, key, v))}
            />
            <CarriedNote id={note} carryKey={key} name={label.toLowerCase()} fieldId={`bulletin-${key}`} />
          </div>
        );
      })}
    </Group>
  );
}

function ReadingTexts() {
  const { draft, update } = useDraft();
  const picks = effectivePicks(draft);
  const readings = [
    { slot: "ot", name: "First Reading", ref: picks.ot },
    { slot: "nt", name: "New Testament Reading", ref: picks.nt },
  ].filter((r): r is { slot: string; name: string; ref: string } => r.ref !== null);
  return (
    <Group id="bulletin-readings" title="Reading text" help={READINGS_HELP}>
      {readings.length === 0 ? <p className="text-sm text-muted-foreground">{NO_READINGS}</p> : null}
      {readings.map(({ slot, name, ref }) => (
        <TextField
          key={slot}
          id={`bulletin-text-${slot}`}
          label={`${name}: ${ref}`}
          value={draft.bulletin.pasted[ref] ?? ""}
          maxLength={MAX_LENGTH.reading_text}
          long
          onChange={(v) => update((d) => setPastedText(d, ref, v))}
        />
      ))}
    </Group>
  );
}

/**
 * Step 4, Bulletin (printed bulletin PR 2b; spec "The Bulletin step"; PR 2
 * planning answers 4-7): what the week's printed bulletin adds to the
 * service, all optional (it never blocks Review, the Word copies or the
 * printed bulletin). The prelude and postlude; who leads (the bulletin
 * settings' three people, changeable for this week, and each part's leader
 * behind "Change who leads a part"); the announcements; and per reading a
 * box for its pasted text. Last week's music and announcements carry in
 * (`useBulletinCarry`), each such box marked "From last week. Check before
 * printing." until it is edited or kept. It reads and writes only the
 * draft; the Bulletin settings button opens the standing settings.
 */
export function BulletinStep() {
  const carry = useBulletinCarry();
  // Kept while Try again runs; then focus goes to the step's heading (2b-2 build review M2).
  const failure = useKeptAlert(carry.failed, carry.fetching, carry.retry, "bulletin-step-title");
  return (
    <section aria-labelledby="bulletin-step-title" className="grid gap-6">
      <div className="grid gap-1">
        <h2 id="bulletin-step-title" tabIndex={-1} className="text-lg font-semibold">
          Bulletin
        </h2>
        <p className="text-sm text-muted-foreground">{BULLETIN_INTRO}</p>
      </div>
      {failure.shown ? (
        <div role="alert" className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <p className="text-sm">{CARRY_FAILED}</p>
          <Button type="button" variant="outline" size="touch" onClick={failure.retry}>
            Try again
          </Button>
        </div>
      ) : null}
      <Group id="bulletin-music" title="Music">
        <Music piece="prelude" name="Prelude" />
        <Music piece="postlude" name="Postlude" />
      </Group>
      <WhoLeads />
      <Announcements />
      <ReadingTexts />
      <Link href="/bulletin-settings" className={buttonVariants({ variant: "outline", size: "touch", className: "w-full sm:w-fit" })}>
        Bulletin settings
      </Link>
    </section>
  );
}

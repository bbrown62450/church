"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type ChangeEvent, type ReactNode } from "react";
import { toast } from "sonner";

import { PendingButton } from "@/components/app/pending-button";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { errorToastMessage, isNoChurchAccess } from "@/lib/api/errors";
import type { BulletinSettings } from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";
import { ELEMENTS, ROLES } from "@/lib/bulletin-settings";
import { formatServiceDate } from "@/lib/dates";
import {
  keepCarried,
  MAX_LENGTH,
  setAnnouncement,
  setCover,
  setMusic,
  setPartLeader,
  setPastedText,
  setPerson,
  type Piece,
} from "@/lib/draft/bulletin";
import { useDraft } from "@/lib/draft/context";
import { effectivePicks } from "@/lib/draft/readings";
import type { AnnouncementKey, CarryKey, DraftV1, Person } from "@/lib/draft/schema";
import {
  checkPicture,
  isLatestChoice,
  newChoice,
  useBulletinImage,
  useUploadBulletinImage,
  useUploadingPicture,
} from "@/lib/queries/bulletin-images";
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
export const COVER_HELP =
  "A JPEG or PNG picture for the front page, with the reading and the date printed over it. Without a picture, the reading and the date print alone.";
export const PICTURE_ALT = "This week's cover picture, as the front page trims it";
export const PICTURE_MISSING = "The picture could not be loaded.";
export const PICTURE_SMALL = "This picture is small and may print blurry.";
/** An upload that answered for a draft no longer open, or for another date (PR 3b build review M5). */
export const PICTURE_OTHER_SERVICE = "The picture was for another service, so it was not added.";
export const PICTURE_OTHER_WEEK = "The picture was for another week, so it was not added.";
/** A stored picture shorter than this on its long side fills the 5.2 in cover box at under about 150 dpi. */
export const SMALL_PICTURE_SIDE = 800;

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

/**
 * The picture's bytes as a URL the `<img>` can show. Made and released in
 * one effect keyed by the bytes, so StrictMode's second run (or any
 * remount) makes a new URL instead of showing one already released (plan
 * review I2).
 */
function useObjectUrl(blob: Blob | undefined): string | null {
  const [url, setUrl] = useState<{ blob: Blob; url: string } | null>(null);
  useEffect(() => {
    if (blob === undefined) return;
    const made = URL.createObjectURL(blob);
    setUrl({ blob, url: made }); // eslint-disable-line react-hooks/set-state-in-effect -- the URL is an external resource made here and released below
    return () => URL.revokeObjectURL(made);
  }, [blob]);
  return url !== null && url.blob === blob ? url.url : null;
}

/**
 * The cover picture (printed bulletin PR 3b; PR 3 planning answers 2-8): the
 * week's picture, trimmed to the cover's shape as the front page prints it
 * (a centered crop), with a dark band across its bottom holding the reading
 * and the date as they print over it, and **Choose a picture** (or **Choose
 * another picture**) and **Remove**. A file the server would refuse (not a
 * JPEG or PNG, empty, over 10 MB) is said at once; the upload's own refusal
 * or failure is said under the buttons; a small picture is said to print
 * blurry; a picture that could not be loaded offers **Try again** beside
 * **Remove**. The picture uploaded goes in the draft even when the step was
 * left meanwhile (the upload's own callback, written at once), unless the
 * draft is another one by then or has another date (a toast says so), or a
 * later choice or Remove came after it. While an upload is in flight, from
 * this visit to the step or an earlier one, the button says "Uploading…"
 * and Choose and Remove wait. A failure after the step was left is a toast.
 * Last week's picture carries in like the
 * music, with "From last week. Check before printing." and **Keep as is**.
 */
/**
 * Where an upload's failure is said while a Bulletin step shows, by church:
 * under the buttons. With no step showing (the step was left meanwhile), a
 * toast says it (PR 3b build review M5).
 */
const shownProblems = new Map<string, (message: string) => void>();

function CoverPicture() {
  const { draft, update, flush, sync, peek } = useDraft();
  const church = useChurch();
  const picture = draft.bulletin.cover_image_id;
  const draftId = `${church.id}:${draft.created_at}`;
  const [problem, setProblem] = useState<string | null>(null);
  useEffect(() => {
    shownProblems.set(church.id, setProblem);
    return () => {
      if (shownProblems.get(church.id) === setProblem) shownProblems.delete(church.id);
    };
  }, [church.id]);
  // In flight even when another visit to the step started it (PR 3b build review I1).
  const uploading = useUploadingPicture();
  const upload = useUploadBulletinImage({
    onStored: (stored, { choice }) => {
      if (!isLatestChoice(choice.draft, choice.token)) return; // a later choice, or Remove, wins (build review I1)
      // The builder may be gone and another page may have written a newer draft
      // meanwhile (New service, another service opened): take it first, so the
      // check below sees the draft now stored and this store never writes the
      // copy it had over it (PR 3b build review C1).
      sync();
      const now = peek();
      if (now.created_at !== choice.created) {
        toast.info(PICTURE_OTHER_SERVICE, { id: "bulletin-cover-dropped" });
        return;
      }
      if (now.readings.date_iso !== choice.date) {
        toast.info(PICTURE_OTHER_WEEK, { id: "bulletin-cover-dropped" });
        return;
      }
      update((d) => (d.created_at === choice.created && d.readings.date_iso === choice.date ? setCover(d, stored.id) : d));
      flush(); // the step may be gone by now (plan review I1)
    },
    onFailed: (e, { choice }) => {
      if (!isLatestChoice(choice.draft, choice.token)) return;
      const show = shownProblems.get(choice.church);
      if (show) show(errorToastMessage(e));
      // The step was left: said where the member is now (build review M5); a sign-out or a lost church says itself.
      else if (e.status !== 401 && !isNoChurchAccess(e)) toast.error(errorToastMessage(e));
    },
  });
  const preview = useBulletinImage(picture);
  // Try again beside Remove: a dropped connection is not a missing picture (PR 3b build review M6).
  // Kept while it runs; once the picture shows, focus goes to Choose another picture.
  const failure = useKeptAlert(picture !== null && preview.isError, preview.isFetching, preview.refetch, "bulletin-cover-choose");
  const url = useObjectUrl(preview.data);
  const [smallUrl, setSmallUrl] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const note = "bulletin-cover-carried";
  const { ot, nt } = effectivePicks(draft);
  const band = [nt ?? ot ?? "", formatServiceDate(draft.readings.date_iso)].filter((line) => line !== "");

  function choose(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = ""; // the same file can be chosen again
    if (!file) return;
    const refused = checkPicture(file);
    setProblem(refused);
    if (refused) return;
    const choice = { church: church.id, draft: draftId, created: draft.created_at, date: draft.readings.date_iso, token: newChoice(draftId) };
    upload.mutate({ file, choice });
  }

  return (
    <Group id="bulletin-cover" title="Cover picture" help={COVER_HELP}>
      {picture === null ? null : failure.shown ? (
        <p className="text-sm">{PICTURE_MISSING}</p>
      ) : url === null ? (
        <Skeleton role="status" aria-label="Loading the cover picture" className="aspect-[372/300] w-full max-w-sm" />
      ) : (
        <div className="grid gap-2">
          <div className="relative w-full max-w-sm overflow-hidden rounded-md border">
            {/* A blob URL of the church's own picture: next/image could not fetch it, and nothing here needs optimizing. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={url}
              alt={PICTURE_ALT}
              className="aspect-[372/300] w-full object-cover"
              onLoad={(e) => {
                const shown = e.currentTarget;
                setSmallUrl(Math.max(shown.naturalWidth, shown.naturalHeight) < SMALL_PICTURE_SIDE ? url : null);
              }}
            />
            {band.length > 0 ? (
              // The printed band, roughly: what it covers, and the words on it (plan review M8).
              <div
                aria-hidden="true"
                data-testid="cover-band"
                className="absolute inset-x-0 bottom-0 grid justify-items-center bg-black/55 px-2 py-1.5 text-center font-serif font-bold leading-tight text-white"
              >
                {band.map((line, i) => (
                  <span key={i} className={i === 0 ? "text-sm" : "text-xs"}>
                    {line}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
          {smallUrl === url ? <p className="text-sm">{PICTURE_SMALL}</p> : null}
        </div>
      )}
      <input
        ref={input}
        id="bulletin-cover-file"
        type="file"
        accept="image/jpeg,image/png"
        className="sr-only"
        tabIndex={-1}
        aria-hidden="true"
        onChange={choose}
      />
      <div className="flex flex-wrap gap-3">
        <PendingButton
          id="bulletin-cover-choose"
          type="button"
          variant="outline"
          size="touch"
          pending={uploading}
          pendingLabel="Uploading…"
          aria-describedby={draft.bulletin.carried.includes("cover") ? note : undefined}
          onClick={() => input.current?.click()}
        >
          {picture === null ? "Choose a picture" : "Choose another picture"}
        </PendingButton>
        {picture === null ? null : (
          <Button
            type="button"
            variant="outline"
            size="touch"
            aria-label="Remove the cover picture"
            disabled={uploading}
            onClick={() => {
              newChoice(draftId);
              setProblem(null);
              update((d) => setCover(d, null));
              document.getElementById("bulletin-cover-choose")?.focus();
            }}
          >
            Remove
          </Button>
        )}
        {picture !== null && failure.shown ? (
          <Button type="button" variant="outline" size="touch" aria-label="Try again: cover picture" onClick={failure.retry}>
            Try again
          </Button>
        ) : null}
      </div>
      <p role="status" className="sr-only">
        {uploading ? "Uploading the picture…" : ""}
      </p>
      {problem ? (
        <p role="alert" className="text-sm">
          {problem}
        </p>
      ) : null}
      <CarriedNote id={note} carryKey="cover" name="cover picture" fieldId="bulletin-cover-choose" />
    </Group>
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
 * printed bulletin). The cover picture (PR 3b); the prelude and postlude; who leads (the bulletin
 * settings' three people, changeable for this week, and each part's leader
 * behind "Change who leads a part"); the announcements; and per reading a
 * box for its pasted text. Last week's picture, music and announcements carry in
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
      <CoverPicture />
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

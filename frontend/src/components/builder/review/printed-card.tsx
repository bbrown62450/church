"use client";

import { DownloadIcon } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { PendingButton } from "@/components/app/pending-button";
import { useBulletinCarry } from "@/components/builder/bulletin/use-bulletin-carry";
import { useStillWorking } from "@/components/builder/liturgy/use-still-working";
import { buttonVariants } from "@/components/ui/button";
import { notFilledInLine } from "@/lib/bulletin-settings";
import { notChecked, notCheckedLine, printedNotFilledIn } from "@/lib/draft/bulletin";
import { useDraft } from "@/lib/draft/context";
import { hasReadingsError, hasServiceDate, reviewStatus } from "@/lib/draft/status";
import type { PrintedFormat } from "@/lib/download";
import { useBulletinSettings } from "@/lib/queries/bulletin-settings";
import { useDownloadPrinted } from "@/lib/queries/documents";

import { FIX_READINGS, NEEDS_DATE, SAVE_HINT } from "./documents-card";

type PrintedFile = { format: PrintedFormat; name: string; description: string; action: string };

const FILES: readonly PrintedFile[] = [
  {
    format: "pdf",
    name: "Printed bulletin",
    description: "Ready to print on legal paper, two pages to a side.",
    action: "Download printed bulletin",
  },
  {
    format: "docx",
    name: "Word version",
    description: "The same bulletin as a Word file, to change before printing.",
    action: "Download Word version",
  },
];

export const PRINTED_SUMMARY =
  "The booklet: the cover, the order of worship with the readings in full, and the announcements.";
export const SETTINGS_NOTE =
  "The church's details, the people who lead and the service time come from the bulletin settings.";
export const WEEKLY_NOTE = "The music, the announcements and this week's changes to who leads come from the Bulletin step.";

/**
 * What the printed bulletin leaves out (PR 2 planning answer 3: a blank field
 * prints nothing, so the card says which are blank), above the downloads so
 * it is read before printing: the blank standing settings (with this week's
 * people), then the prelude, the postlude and the announcements (PR 2b). The
 * settings' part is left out while they load or if they fail: the downloads
 * never wait for them. Then the boxes still holding last week's text,
 * unchecked.
 */
function NotFilledInLines() {
  const { draft } = useDraft();
  const settings = useBulletinSettings();
  const missing = printedNotFilledIn(settings.data, draft);
  const unchecked = notChecked(draft);
  return (
    <>
      {missing.length > 0 ? <p className="text-sm">{notFilledInLine(missing)}</p> : null}
      {unchecked.length > 0 ? <p className="text-sm">{notCheckedLine(unchecked)}</p> : null}
    </>
  );
}

function FileRow({ file, disabled, onDownloaded }: { file: PrintedFile; disabled: boolean; onDownloaded: () => void }) {
  const download = useDownloadPrinted(file.format);
  const slow = useStillWorking(download.isPending);
  const pendingLabel = slow ? "Still working…" : "Preparing…";
  const id = `printed-${file.format}`;
  return (
    <li className="grid gap-2">
      <p id={`${id}-description`} className="text-sm text-muted-foreground">
        {file.description}
      </p>
      <PendingButton
        size="touch"
        variant={file.format === "pdf" ? "default" : "outline"}
        className="w-full sm:w-fit"
        pending={download.isPending}
        pendingLabel={pendingLabel}
        disabled={disabled}
        aria-describedby={`${id}-description`}
        onClick={() => download.mutate(undefined, { onSuccess: onDownloaded })}
      >
        <DownloadIcon data-icon="inline-start" aria-hidden="true" />
        {file.action}
      </PendingButton>
      <p role="status" className="sr-only">
        {download.isPending ? `${file.name}: ${pendingLabel}` : ""}
      </p>
    </li>
  );
}

/**
 * The printed bulletin card (printed bulletin spec, PR 1; owner answers 1 and
 * 7, 2026-10-02): the booklet as a print-ready PDF (primary; two pages to a
 * legal sheet in reading order, layout B) and as a Word file to change, each built on the server from the draft at the tap,
 * with the readings in full in the translation step 1 shows. Pending labels,
 * errors, the date and readings gates and the save tip work as on the Word
 * documents card. PR 2a: the standing details come
 * from the church's bulletin settings; the card lists the blank ones above
 * the downloads and links to the Bulletin settings page below them (any
 * member; admins edit there). PR 2b: the week's own fields come from the
 * Bulletin step and replace PR 1's last [placeholders] (the cover picture's
 * stays until PR 3); the card lists the blank ones and the boxes from last
 * week not checked yet, and carries last week's in here too
 * (`useBulletinCarry`), so a bulletin printed without opening the Bulletin
 * step has them.
 */
export function PrintedCard() {
  const { draft } = useDraft();
  useBulletinCarry();
  const [downloaded, setDownloaded] = useState(false);
  const dated = hasServiceDate(draft);
  const readingsError = hasReadingsError(draft);
  return (
    <section aria-labelledby="printed-title" className="grid gap-4 rounded-lg border p-4">
      <div className="grid gap-1">
        <h2 id="printed-title" className="text-base font-medium">
          Printed bulletin
        </h2>
        <p className="text-sm text-muted-foreground">{PRINTED_SUMMARY}</p>
        <p className="text-sm text-muted-foreground">{SETTINGS_NOTE}</p>
        <p className="text-sm text-muted-foreground">{WEEKLY_NOTE}</p>
        <NotFilledInLines />
        {dated ? null : <p className="text-sm text-muted-foreground">{NEEDS_DATE}</p>}
        {readingsError ? <p className="text-sm text-muted-foreground">{FIX_READINGS}</p> : null}
      </div>
      <ul className="grid gap-6">
        {FILES.map((file) => (
          <FileRow key={file.format} file={file} disabled={!dated || readingsError} onDownloaded={() => setDownloaded(true)} />
        ))}
      </ul>
      {downloaded && reviewStatus(draft) !== "saved" ? <p className="text-sm text-muted-foreground">{SAVE_HINT}</p> : null}
      <Link href="/bulletin-settings" className={buttonVariants({ variant: "outline", size: "touch", className: "w-full sm:w-fit" })}>
        Bulletin settings
      </Link>
    </section>
  );
}

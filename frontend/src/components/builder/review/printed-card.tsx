"use client";

import { DownloadIcon } from "lucide-react";
import { useState } from "react";

import { PendingButton } from "@/components/app/pending-button";
import { useStillWorking } from "@/components/builder/liturgy/use-still-working";
import { useDraft } from "@/lib/draft/context";
import { hasReadingsError, hasServiceDate, reviewStatus } from "@/lib/draft/status";
import type { PrintedFormat } from "@/lib/download";
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
export const PLACEHOLDERS_NOTE =
  "For now, the church's details, the people who lead, the music and the announcements print as [placeholders].";

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
 * documents card. PR 1 prints what the app does not know yet as
 * [placeholders], and the card says so.
 */
export function PrintedCard() {
  const { draft } = useDraft();
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
        <p className="text-sm text-muted-foreground">{PLACEHOLDERS_NOTE}</p>
        {dated ? null : <p className="text-sm text-muted-foreground">{NEEDS_DATE}</p>}
        {readingsError ? <p className="text-sm text-muted-foreground">{FIX_READINGS}</p> : null}
      </div>
      <ul className="grid gap-6">
        {FILES.map((file) => (
          <FileRow key={file.format} file={file} disabled={!dated || readingsError} onDownloaded={() => setDownloaded(true)} />
        ))}
      </ul>
      {downloaded && reviewStatus(draft) !== "saved" ? <p className="text-sm text-muted-foreground">{SAVE_HINT}</p> : null}
    </section>
  );
}

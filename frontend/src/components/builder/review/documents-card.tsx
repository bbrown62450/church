"use client";

import { DownloadIcon } from "lucide-react";
import { useState } from "react";

import { PendingButton } from "@/components/app/pending-button";
import { useStillWorking } from "@/components/builder/liturgy/use-still-working";
import { useDraft } from "@/lib/draft/context";
import type { DraftV1 } from "@/lib/draft/schema";
import { hasReadingsError, hasServiceDate, reviewStatus } from "@/lib/draft/status";
import type { DocumentVariant } from "@/lib/download";
import { useDownloadDocument } from "@/lib/queries/documents";

type Copy = { variant: DocumentVariant; title: string; description: string; action: string };

const COPIES: readonly Copy[] = [
  {
    variant: "bulletin",
    title: "Bulletin copy",
    description: "The order of worship with hymns, readings and the sermon title. Leaves out Prayers of the People.",
    action: "Download bulletin copy",
  },
  {
    variant: "pastor",
    title: "Pastor's copy",
    description: "Everything in the bulletin copy, plus Prayers of the People.",
    action: "Download pastor's copy",
  },
];

export const SAME_AS_BULLETIN = "Same as the bulletin copy for this service. Prayers of the People is empty or turned off.";
export const NEEDS_DATE = "Choose a service date on step 1 to download.";
export const FIX_READINGS = "Fix the readings on step 1 to download.";
export const SAVE_HINT = "Tip: save this service so its hymns count as recently used.";

/** The pastor's copy prints nothing more when Prayers of the People is off or blank (inv F1). */
function sameAsBulletin(draft: DraftV1): boolean {
  const card = draft.liturgy.cards.prayers_of_the_people;
  return !card.enabled || card.text.trim() === "";
}

function CopyRow({
  copy,
  disabled,
  helper,
  onDownloaded,
}: {
  copy: Copy;
  disabled: boolean;
  helper: string | null;
  onDownloaded: () => void;
}) {
  const download = useDownloadDocument(copy.variant);
  const slow = useStillWorking(download.isPending);
  const pendingLabel = slow ? "Still working…" : "Preparing…";
  const id = `${copy.variant}-copy`;
  return (
    <li className="grid gap-2">
      <h3 id={`${id}-title`} className="text-base font-medium">
        {copy.title}
      </h3>
      <p id={`${id}-description`} className="text-sm text-muted-foreground">
        {copy.description}
      </p>
      {helper ? (
        <p id={`${id}-helper`} className="text-sm text-muted-foreground">
          {helper}
        </p>
      ) : null}
      <PendingButton
        size="touch"
        variant={copy.variant === "bulletin" ? "default" : "outline"}
        className="w-full sm:w-fit"
        pending={download.isPending}
        pendingLabel={pendingLabel}
        disabled={disabled}
        aria-describedby={helper ? `${id}-description ${id}-helper` : `${id}-description`}
        onClick={() => download.mutate(undefined, { onSuccess: onDownloaded })}
      >
        <DownloadIcon data-icon="inline-start" aria-hidden="true" />
        {copy.action}
      </PendingButton>
      <p role="status" className="sr-only">
        {download.isPending ? `${copy.title}: ${pendingLabel}` : ""}
      </p>
    </li>
  );
}

/**
 * The Word documents card (slice 5a spec, UX "Word documents card"; owner
 * answers 3 and 7, 2026-10-01): the bulletin copy and the pastor's copy, each
 * built on the server from the draft as it is at the tap. Each button has its
 * own "Preparing…" ("Still working…" after 8 s); the file then goes to the
 * browser's download (on iPhone, the share or preview sheet), with no toast;
 * a failure is a toast with the server's message (none after a 401 or a lost
 * church: the app's own handling says it; the toast comes from
 * `useDownloadDocument`, so it shows after the card unmounts too). Both
 * buttons need a valid service date and no Date & readings field message (an
 * occasion over 300, more than 20 readings or a line over 200: "Fix the
 * readings on step 1 to download.", build review fix 6), nothing else: what
 * is missing is listed above, and the file prints what there is ("[Sermon
 * title]" for a blank title). After a download while the draft is not saved
 * as it is (slice 5a-3), a tip says that saving is what records the hymns as
 * recently used.
 */
export function DocumentsCard() {
  const { draft } = useDraft();
  const [downloaded, setDownloaded] = useState(false);
  const dated = hasServiceDate(draft);
  const readingsError = hasReadingsError(draft);
  const same = sameAsBulletin(draft);
  return (
    <section aria-labelledby="documents-title" className="grid gap-4 rounded-lg border p-4">
      <div className="grid gap-1">
        <h2 id="documents-title" className="text-base font-medium">
          Word documents
        </h2>
        {dated ? null : <p className="text-sm text-muted-foreground">{NEEDS_DATE}</p>}
        {readingsError ? <p className="text-sm text-muted-foreground">{FIX_READINGS}</p> : null}
      </div>
      <ul className="grid gap-6">
        {COPIES.map((copy) => (
          <CopyRow
            key={copy.variant}
            copy={copy}
            disabled={!dated || readingsError}
            helper={copy.variant === "pastor" && same ? SAME_AS_BULLETIN : null}
            onDownloaded={() => setDownloaded(true)}
          />
        ))}
      </ul>
      {downloaded && reviewStatus(draft) !== "saved" ? <p className="text-sm text-muted-foreground">{SAVE_HINT}</p> : null}
    </section>
  );
}

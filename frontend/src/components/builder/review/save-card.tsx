"use client";

import { useId, useState } from "react";
import { toast } from "sonner";

import { PendingButton } from "@/components/app/pending-button";
import { useNewService } from "@/components/builder/new-service-menu-item";
import { Button } from "@/components/ui/button";
import { formatSavedAt, formatServiceDate, formatShortDate } from "@/lib/dates";
import { useDraft } from "@/lib/draft/context";
import type { DraftChurch, DraftV1 } from "@/lib/draft/schema";
import { hasReadingsError, hasServiceDate, reviewStatus, saveMode } from "@/lib/draft/status";
import { isConflict, useOpenService, useSaveService } from "@/lib/queries/services";

import { ConflictDialog } from "./conflict-dialog";

export const SAVE_NEEDS_DATE = "Choose a service date on step 1 to save.";
export const SAVE_FIX_READINGS = "Fix the readings on step 1 to save.";
export const CONFLICT_MESSAGE = "This service was changed by someone else. Reload it to see their changes.";
export const LOADED_LATEST = "Loaded the latest version.";

/** The line under the heading (S UX "Save card" status line). */
export function archiveStatusLine(draft: DraftV1): string {
  const editing = draft.editing;
  if (editing === null) return "Not in the archive yet.";
  const at = formatSavedAt(editing.saved_at);
  return reviewStatus(draft) === "saved" ? `Saved to the archive · ${at}` : `Unsaved changes · last saved ${at}`;
}

/** Why the button says "Save as new service" (S UX "Save card"); null in the other modes or without a date. */
function copyNote(draft: DraftV1): string | null {
  const editing = draft.editing;
  if (editing === null || saveMode(draft) !== "copy" || !hasServiceDate(draft)) return null;
  const now = formatServiceDate(draft.readings.date_iso);
  if (editing.date_iso === null) {
    return `The saved service has no date, so this will be saved as a new service on ${now}. The undated service stays in the archive.`;
  }
  return `The date changed from ${formatServiceDate(editing.date_iso)} to ${now}, so this will be saved as a new service. The ${formatShortDate(editing.date_iso)} service stays in the archive.`;
}

const LABELS = { new: "Save to archive", update: "Save changes", copy: "Save as new service" } as const;

/**
 * The Archive card (slice 5a spec, UX "Save card"; owner answer 4): where the
 * draft stands in the archive, the save button ("Save to archive", "Save
 * changes" or "Save as new service", with why when the date changed),
 * "Saving…" while it runs, and "Start a new service" (New service's own
 * question when there is something to lose). The button is off only without
 * a service date or while a Date & readings field shows its message, as the
 * downloads are. A 409 opens the conflict dialog; every other outcome is a
 * toast from `useSaveService`.
 */
export function SaveCard({ church }: { church: DraftChurch }) {
  const { draft } = useDraft();
  const save = useSaveService(church);
  const reload = useOpenService(church);
  const newService = useNewService(church);
  const [conflict, setConflict] = useState<string | null>(null);
  const mode = saveMode(draft);
  const dated = hasServiceDate(draft);
  const readingsError = hasReadingsError(draft);
  const note = copyNote(draft);
  const ids = { status: useId(), date: useId(), readings: useId(), note: useId() };
  // Why Save is off, or why it saves a copy, is part of the button's description (build review M4).
  const describedBy = [!dated && ids.date, readingsError && ids.readings, note && ids.note].filter(Boolean).join(" ") || undefined;

  function run(asNew: boolean) {
    save.mutate(
      { asNew },
      {
        onSuccess: () => setConflict(null),
        onError: (e) => {
          if (isConflict(e)) setConflict(e.message || CONFLICT_MESSAGE);
        },
      },
    );
  }

  function reloadTheirs() {
    const id = draft.editing?.service_id;
    if (!id) return;
    reload.mutate(id, {
      onSuccess: () => {
        setConflict(null);
        toast.success(LOADED_LATEST);
      },
      onError: () => setConflict(null),
    });
  }

  return (
    <section aria-labelledby="archive-title" className="grid gap-3 rounded-lg border p-4">
      <div className="grid gap-1">
        <h2 id="archive-title" className="text-base font-medium">
          Archive
        </h2>
        <p id={ids.status} aria-live="polite" className="text-sm text-muted-foreground">
          {archiveStatusLine(draft)}
        </p>
        {dated ? null : (
          <p id={ids.date} className="text-sm text-muted-foreground">
            {SAVE_NEEDS_DATE}
          </p>
        )}
        {readingsError ? (
          <p id={ids.readings} className="text-sm text-muted-foreground">
            {SAVE_FIX_READINGS}
          </p>
        ) : null}
      </div>
      {note ? (
        <p id={ids.note} className="text-sm text-muted-foreground">
          {note}
        </p>
      ) : null}
      <div className="flex flex-col gap-2 sm:flex-row">
        <PendingButton
          size="touch"
          className="w-full sm:w-fit"
          pending={save.isPending}
          disabled={!dated || readingsError}
          aria-describedby={describedBy}
          onClick={() => run(false)}
        >
          {LABELS[mode]}
        </PendingButton>
        <Button variant="outline" size="touch" className="w-full sm:w-fit" onClick={() => newService.start()}>
          Start a new service
        </Button>
      </div>
      <ConflictDialog
        open={conflict !== null}
        onOpenChange={(open) => {
          if (!open && !save.isPending && !reload.isPending) setConflict(null);
        }}
        message={conflict ?? CONFLICT_MESSAGE}
        onReload={reloadTheirs}
        reloading={reload.isPending}
        onSaveAsNew={() => run(true)}
        saving={save.isPending}
      />
      {newService.dialog}
    </section>
  );
}

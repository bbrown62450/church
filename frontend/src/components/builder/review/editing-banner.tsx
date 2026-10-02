"use client";

import Link from "next/link";

import { formatLongDate, formatServiceDate } from "@/lib/dates";
import { useDraft } from "@/lib/draft/context";

/**
 * The banner at the top of Review while the draft is a saved service (slice
 * 5a spec, UX "Review step" item 1): which saved service this is, and that
 * changes stay on this device until saved. A saved service with no date (a
 * legacy row; production had none on 2026-10-02) says so instead, with the
 * date it was given for now and a link to step 1. It is advice only. A hymn
 * that is not in the hymnal is listed in "Still to do" just below, so the
 * banner does not repeat it.
 */
export function EditingBanner() {
  const { draft } = useDraft();
  const editing = draft.editing;
  if (editing === null) return null;
  if (editing.date_iso === null) {
    const now = formatLongDate(draft.readings.date_iso);
    return (
      <div className="rounded-lg border bg-muted/40 p-4 text-sm">
        <p>
          This saved service has no date.{now ? ` It's set to ${now} for now.` : ""}{" "}
          <Link href="/builder/readings" className="font-medium underline underline-offset-4">
            Check the date
          </Link>
        </p>
      </div>
    );
  }
  return (
    <div className="rounded-lg border bg-muted/40 p-4 text-sm">
      <p>
        You&apos;re editing the saved service for {formatServiceDate(editing.date_iso)}. Changes stay on this device until you
        save.
      </p>
    </div>
  );
}

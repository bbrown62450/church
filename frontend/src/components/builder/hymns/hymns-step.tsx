"use client";

import { EmptyState } from "@/components/app/empty-state";
import { ErrorState } from "@/components/app/error-state";
import { buttonVariants } from "@/components/ui/button";
import type { Hymn } from "@/lib/api/types";
import { isValidDateIso } from "@/lib/dates";
import { useDraft } from "@/lib/draft/context";
import { SLOTS, type Slot } from "@/lib/draft/schema";
import { SETTINGS_HYMNS_READY } from "@/lib/features";
import { selectHymnal } from "@/lib/hymns/hymnal";
import { duplicateNotice, MISSING_NOTICE, recentUseNotice } from "@/lib/hymns/labels";
import { clearSlot, duplicateSlots, pickFromHymn, reconcilePick, setSlot, type Reconciled } from "@/lib/hymns/picks";
import { useHymnals, useHymnLists } from "@/lib/queries/hymns";

import { HymnSlotCard } from "./hymn-slot-card";
import { useUndoToasts } from "./use-undo-toasts";

/** The empty-hymnal state (S "Whole-step states"); the link waits for Settings → Hymns (6a). */
function EmptyHymnal() {
  return (
    <EmptyState
      title="This church's hymnal is empty"
      description={
        SETTINGS_HYMNS_READY
          ? "Add hymns on the Settings → Hymns page to choose hymns here."
          : "Add hymns in the current app under Settings → Hymns."
      }
      action={
        SETTINGS_HYMNS_READY ? (
          <a href="/settings/hymns" className={buttonVariants({ size: "touch" })}>
            Open Settings → Hymns
          </a>
        ) : undefined
      }
    />
  );
}

const MISSING: Reconciled = { status: "missing" };

/**
 * Step 2, Hymns (S "User experience"). It reads and writes only the draft
 * (F §4.6). The slot cards show the draft's picks at once; the pickers wait
 * for `GET /hymnals` and the selected hymnal's list, with no full-page
 * spinner. The selected hymnal is resolved only from a loaded `GET /hymnals`
 * and never written back (S Toolbar). Removing a hymn offers Undo in a toast
 * that never outlives the step.
 */
export function HymnsStep() {
  const { draft, update } = useDraft();
  const hymnalsQuery = useHymnals();
  const hymns = draft.hymns;
  const dateIso = draft.readings.date_iso;
  const dateValid = isValidDateIso(dateIso);
  const recentForDate = dateValid ? dateIso : null;
  const hymnals = hymnalsQuery.data;
  const empty = hymnals !== undefined && hymnals.items.length === 0;
  const selected = hymnals && !empty ? selectHymnal(hymns.hymnal, hymnals) : null;
  const code = selected?.code ?? null;
  // The picks' hymnals too (a pick keeps its own), once GET /hymnals has answered with some.
  const listed = selected === null ? [] : [code, ...SLOTS.map((slot) => hymns.slots[slot]?.hymnal ?? null)];
  const lists = useHymnLists(listed, recentForDate);
  const showUndo = useUndoToasts();

  const selectedList = code === null ? undefined : lists.lists.get(code);
  // A failed background refetch keeps what had loaded (TanStack Query v5 keeps `data` with
  // `isError`), so only a load that never succeeded replaces the pickers with the error.
  const failed =
    (hymnalsQuery.isError && hymnals === undefined) || (code !== null && lists.failed.has(code) && selectedList === undefined);
  const pickers = !failed && !empty;
  const showHymnal = (hymnals?.items.length ?? 0) >= 2;
  const excludeRecent = hymns.exclude_recent && dateValid;
  const duplicates = duplicateSlots(hymns.slots);

  function notices(slot: Slot, reconciled: Reconciled | null): string[] {
    const out: string[] = [];
    if (reconciled?.status === "ok" && dateValid && reconciled.live.recent_use_on) {
      out.push(recentUseNotice(reconciled.live.recent_use_on, dateIso));
    }
    if (reconciled?.status === "missing") out.push(MISSING_NOTICE);
    const duplicate = duplicateNotice(duplicates[slot]);
    if (duplicate) out.push(duplicate);
    return out;
  }

  function choose(slot: Slot, h: Hymn) {
    update((d) => setSlot(d, slot, pickFromHymn(h)));
  }

  function remove(slot: Slot, title: string) {
    const previous = hymns.slots[slot];
    if (!previous) return;
    update((d) => clearSlot(d, slot));
    // Undo only while the slot is still as ✕ left it; a hymn chosen since is never replaced.
    showUndo(`Removed ${title}.`, () => update((d) => (d.hymns.slots[slot] === null ? setSlot(d, slot, previous) : d)));
  }

  return (
    <section aria-labelledby="hymns-step-title" className="grid gap-6">
      <div>
        <h2 id="hymns-step-title" className="text-lg font-semibold">
          Hymns
        </h2>
        <p className="text-sm text-muted-foreground">Choose an opening, response and closing hymn.</p>
      </div>
      {failed ? (
        <ErrorState
          error={hymnalsQuery.error}
          message="Couldn't load this church's hymnal."
          retrying={hymnalsQuery.isFetching || lists.fetching}
          onRetry={() => {
            if (hymnals === undefined) void hymnalsQuery.refetch();
            else lists.retry();
          }}
        />
      ) : empty ? (
        <EmptyHymnal />
      ) : null}
      {SLOTS.map((slot) => {
        const pick = hymns.slots[slot];
        const reconciled = pick === null ? null : empty ? MISSING : reconcilePick(pick, lists.lists, code);
        const title = reconciled?.status === "ok" ? reconciled.live.title : (pick?.title ?? "");
        return (
          <HymnSlotCard
            key={slot}
            slot={slot}
            pick={pick}
            reconciled={reconciled}
            notices={notices(slot, reconciled)}
            list={selectedList}
            pickerAvailable={pickers}
            excludeRecent={excludeRecent}
            serviceDateIso={dateIso}
            showHymnal={showHymnal}
            onChoose={(h) => choose(slot, h)}
            onRemove={() => remove(slot, title)}
          />
        );
      })}
      <p className="text-xs text-muted-foreground">
        Hymn information and links courtesy of Hymnary.org. Individual hymns may carry their own copyright — see each
        hymn&apos;s page.
      </p>
    </section>
  );
}

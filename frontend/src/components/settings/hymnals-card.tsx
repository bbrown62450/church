"use client";

import type { UseQueryResult } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { ErrorState } from "@/components/app/error-state";
import { PendingButton } from "@/components/app/pending-button";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import type { ApiError } from "@/lib/api/client";
import type { HymnalSource, Hymnals, HymnalSummary } from "@/lib/api/types";
import { useAddHymnal, useHymnalSources, useRemoveHymnal } from "@/lib/queries/hymn-library";
import { hymnCount } from "@/lib/settings/hymns";

export const MEMBER_HYMNALS_NOTE = "Admins can add bundled hymnals.";
export const NO_REFS_NOTE =
  "This hymnal has no scripture references, so “Hymns for the readings” and AI suggestions work less well with it.";
export const STILL_WORKING = "Still working. This can take up to a minute.";
export const NO_SOURCES = "No bundled hymnals are available on this server.";
/** How long an add runs before the dialog says it is still working (6a spec UX §2a). */
export const STILL_WORKING_AFTER_MS = 8_000;
/** The codes `DELETE /hymnals/{code}` takes; another (only the ops CLI or the old app made one) has no Remove (plan review M4). */
export const REMOVABLE_CODE = /^[A-Za-z0-9_-]{2,20}$/;

const SHEET =
  "max-md:top-auto max-md:bottom-0 max-md:left-0 max-md:max-w-none! max-md:translate-x-0 max-md:translate-y-0 max-md:rounded-b-none max-md:max-h-[85dvh] max-md:overflow-y-auto md:max-w-lg";

function hymnalsLine(items: HymnalSummary[]): string {
  const total = items.reduce((sum, h) => sum + h.hymn_count, 0);
  return `${hymnCount(total)} in ${items.length} ${items.length === 1 ? "hymnal" : "hymnals"}.`;
}

function removeBody(hymnal: HymnalSummary, bundled: boolean | null): string {
  const what = hymnal.hymn_count === 1 ? "the 1 hymn" : `all ${hymnCount(hymnal.hymn_count)}`;
  const first =
    `This deletes ${what} in ${hymnal.code} from your church's hymnal, including hymns your church added to it. ` +
    "Saved services keep their hymns. Services in progress will ask you to choose replacements.";
  if (bundled === null) return first;
  return bundled
    ? `${first} You can add ${hymnal.code} again later, but edits you made to its hymns will be lost.`
    : `${first} It can't be added back from the bundled list.`;
}

/**
 * Settings → Hymns' "Hymnals" card (slice 6a-2; 6a spec UX §2a): one row per
 * hymnal with its name, its count and a Default badge on the effective
 * default. Owners and admins add a bundled hymnal (`AddHymnalDialog`) and
 * remove any hymnal but the default one (confirmed); the default row says
 * where to change the default. A member reads the list.
 */
export function HymnalsCard({ admin, hymnals }: { admin: boolean; hymnals: UseQueryResult<Hymnals, ApiError> }) {
  const sources = useHymnalSources(admin);
  const remove = useRemoveHymnal();
  const addButton = useRef<HTMLButtonElement>(null);
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<HymnalSummary | null>(null);
  // The confirmation keeps its words while it closes (removing is null by then).
  const [removeWords, setRemoveWords] = useState({ title: "", body: "", confirm: "" });
  // Focus goes to Add a hymnal after a removal (the row and its button are gone); otherwise back to Remove.
  const removed = useRef(false);

  const data = hymnals.data;
  let body;
  if (data) {
    body =
      data.items.length === 0 ? (
        <p className="text-sm text-muted-foreground">Your church has no hymnals yet.</p>
      ) : (
        <>
          <ul className="divide-y rounded-lg border" aria-label="Hymnals">
            {data.items.map((h) => {
              const isDefault = h.code === data.effective_hymnal;
              return (
                <li key={h.code} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-3">
                  <div className="grid min-w-0 flex-1 gap-0.5">
                    <p className="flex items-center gap-2 font-medium">
                      {h.code}
                      {isDefault ? <Badge variant="secondary">Default</Badge> : null}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {h.label ? `${h.label} · ` : ""}
                      {hymnCount(h.hymn_count)}
                    </p>
                  </div>
                  {admin && isDefault ? (
                    <p className="text-sm text-muted-foreground">
                      Default. Change it in{" "}
                      <Link href="/settings/church" className="underline underline-offset-4">
                        Church profile
                      </Link>
                      .
                    </p>
                  ) : null}
                  {admin && !isDefault && REMOVABLE_CODE.test(h.code) ? (
                    <Button
                      type="button"
                      variant="outline"
                      size="touch"
                      className="md:h-8"
                      aria-label={`Remove ${h.code}`}
                      onClick={() => {
                        const source = sources.data?.items.find((s) => s.code === h.code);
                        removed.current = false;
                        setRemoveWords({
                          title: `Remove ${h.code}?`,
                          body: removeBody(h, sources.data ? source !== undefined : null),
                          confirm: `Remove ${h.code}`,
                        });
                        setRemoving(h);
                      }}
                    >
                      Remove…
                    </Button>
                  ) : null}
                </li>
              );
            })}
          </ul>
          <p className="text-sm text-muted-foreground">{hymnalsLine(data.items)}</p>
        </>
      );
  } else if (hymnals.isError) {
    body = <ErrorState error={hymnals.error} onRetry={() => void hymnals.refetch()} retrying={hymnals.isFetching} />;
  } else {
    body = (
      <div role="status" aria-label="Loading" className="grid gap-2">
        <Skeleton className="h-14 w-full" />
      </div>
    );
  }

  return (
    <section aria-labelledby="hymnals-title" className="grid gap-3">
      <h3 id="hymnals-title" className="text-base font-medium">
        Hymnals
      </h3>
      {body}
      {admin ? (
        <Button ref={addButton} type="button" variant="outline" size="touch" className="w-full sm:w-fit md:h-8" onClick={() => setAdding(true)}>
          Add a hymnal
        </Button>
      ) : (
        <p className="text-sm text-muted-foreground">{MEMBER_HYMNALS_NOTE}</p>
      )}
      {admin && adding ? <AddHymnalDialog onClose={() => setAdding(false)} /> : null}
      <ConfirmDialog
        open={removing !== null}
        onOpenChange={(open) => {
          // while the removal runs the confirmation stays open (Cancel, Escape and a tap outside are ignored)
          if (!open && !remove.isPending) setRemoving(null);
        }}
        title={removeWords.title}
        description={removeWords.body}
        confirmLabel={removeWords.confirm}
        destructive
        pending={remove.isPending}
        finalFocus={() => (removed.current ? addButton.current : true)}
        onConfirm={() => {
          if (removing === null) return;
          const code = removing.code;
          remove.mutate(code, {
            onSuccess: () => {
              removed.current = true;
              toast.success(`Removed ${code}.`);
            },
            // a 404: it was removed elsewhere, so its row goes too (toasted, and the lists refreshed, by the mutation)
            onError: (e) => {
              if (e.status === 404) removed.current = true;
            },
            // closes the confirmation only while it still asks about this hymnal
            onSettled: () => setRemoving((current) => (current?.code === code ? null : current)),
          });
        }}
      />
    </section>
  );
}

/**
 * **Add a hymnal** (6a spec UX §2a): the bundled hymnals, each "{code} ·
 * {label} · {n} hymns" with **Add**, or **Added** when the church has it. The
 * dialog stays open after an add (the row turns to Added) and cannot be closed
 * while one runs; after 8 s it says the add is still working.
 */
export function AddHymnalDialog({ onClose }: { onClose(): void }) {
  const sources = useHymnalSources(true);
  const add = useAddHymnal();
  const [addingCode, setAddingCode] = useState<string | null>(null);
  const [added, setAdded] = useState<ReadonlySet<string>>(new Set());
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    if (!add.isPending) return;
    const timer = setTimeout(() => setSlow(true), STILL_WORKING_AFTER_MS);
    return () => clearTimeout(timer);
  }, [add.isPending]);

  function addSource(source: HymnalSource) {
    if (add.isPending) return;
    setSlow(false);
    setAddingCode(source.code);
    add.mutate(source.code, {
      onSuccess: (answer) => {
        setAdded((codes) => new Set(codes).add(answer.code));
        // nothing inserted or filled in: the church had it all already (another tab added it meanwhile)
        toast.success(
          answer.inserted + answer.updated === 0
            ? `${answer.code} is already added.`
            : `Added ${answer.code} (${hymnCount(answer.inserted)}).`,
        );
      },
      onSettled: () => setAddingCode(null),
    });
  }

  let body;
  if (sources.data) {
    body =
      sources.data.items.length === 0 ? (
        <p className="text-sm text-muted-foreground">{NO_SOURCES}</p>
      ) : (
        <ul className="divide-y rounded-lg border" aria-label="Bundled hymnals">
          {sources.data.items.map((source) => {
            const present = source.present || added.has(source.code);
            return (
              <li key={source.code} className="flex flex-wrap items-center gap-x-3 gap-y-2 px-4 py-3">
                <div className="grid min-w-0 flex-1 gap-0.5">
                  <p className="text-sm font-medium">
                    {[source.code, source.label, hymnCount(source.hymn_count)].filter(Boolean).join(" · ")}
                  </p>
                  {source.has_scripture_refs ? null : <p className="text-sm text-muted-foreground">{NO_REFS_NOTE}</p>}
                </div>
                {present ? (
                  <Button type="button" variant="outline" size="touch" className="md:h-8" disabled>
                    Added
                  </Button>
                ) : (
                  <PendingButton
                    type="button"
                    size="touch"
                    className="md:h-8"
                    aria-label={`Add ${source.code}`}
                    pending={addingCode === source.code}
                    pendingLabel="Adding…"
                    disabled={add.isPending && addingCode !== source.code}
                    onClick={() => addSource(source)}
                  >
                    Add
                  </PendingButton>
                )}
              </li>
            );
          })}
        </ul>
      );
  } else if (sources.isError) {
    body = <ErrorState error={sources.error} onRetry={() => void sources.refetch()} retrying={sources.isFetching} />;
  } else {
    body = (
      <div role="status" aria-label="Loading" className="grid gap-2">
        <Skeleton className="h-14 w-full" />
      </div>
    );
  }

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        // while an add runs the dialog stays open (Escape and a tap outside are ignored; Done is disabled)
        if (!open && !add.isPending) onClose();
      }}
    >
      <DialogContent showCloseButton={false} className={SHEET}>
        <DialogHeader>
          <DialogTitle>Add a hymnal</DialogTitle>
          <DialogDescription>Hymnals this app can add to your church, with their hymns.</DialogDescription>
        </DialogHeader>
        {body}
        {slow && add.isPending ? (
          <p role="status" className="text-sm text-muted-foreground">
            {STILL_WORKING}
          </p>
        ) : null}
        <DialogFooter className="max-md:rounded-b-none max-md:pb-[calc(1rem+env(safe-area-inset-bottom))]">
          <DialogClose disabled={add.isPending} render={<Button type="button" variant="outline" size="touch" className="md:h-8" />}>
            Done
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

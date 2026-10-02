"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { EmptyState } from "@/components/app/empty-state";
import { ErrorState } from "@/components/app/error-state";
import { PageHeader } from "@/components/app/page-header";
import { PendingButton } from "@/components/app/pending-button";
import { useNewService } from "@/components/builder/new-service-menu-item";
import { Button, buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { ChurchProfile, ServiceSummary } from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";
import { formatServiceDate } from "@/lib/dates";
import { DraftProvider, useDraft } from "@/lib/draft/context";
import { isDirty } from "@/lib/draft/status";
import { useMeContext } from "@/lib/me-context";
import { useChurchProfile } from "@/lib/queries/church";
import { useDeleteService, useOpenService, useServices } from "@/lib/queries/services";

import { serviceDateLabel, ServiceRow } from "./service-row";

/** The delete question's text (slice 5a spec, "Delete flow"). */
export function deleteDescription(s: ServiceSummary, churchName: string, editing: boolean): string {
  const name = `“${s.occasion.trim() || "Untitled service"}”`;
  const when = serviceDateLabel(s) === "No date" ? " (no date)" : ` on ${serviceDateLabel(s)}`;
  const text = `${name}${when} will be removed from the archive for everyone in ${churchName}. This can't be undone.`;
  return editing ? `${text} You're editing this service. Your current draft will be cleared too.` : text;
}

function ListSkeleton() {
  return (
    <div role="status" aria-label="Loading" className="grid gap-2">
      {[0, 1, 2, 3, 4].map((i) => (
        <Skeleton key={i} className="h-20 w-full" />
      ))}
    </div>
  );
}

/**
 * `/services` (slice 5a spec, "Services page"; F §4.1, §4.8): the church's
 * saved services, 20 at a time, newest service date first, and "New
 * service". The page has its own `DraftProvider` (the builder's is not
 * mounted here), so a row shows "Editing" for the service the draft holds,
 * opening a service replaces the draft (after "Replace your unsaved draft?"
 * when there is something to lose) and the builder then opens on Review, and
 * deleting the service being edited clears the draft. Every delete asks
 * first and is open to any member (owner decision 5).
 */
export function ServicesPage() {
  const me = useMeContext();
  const church = useChurch();
  const profile = useChurchProfile(church.id);
  return (
    <main className="mx-auto grid w-full max-w-2xl content-start gap-4 px-4 py-4">
      {profile.data ? (
        <DraftProvider key={`${me.user.id}:${church.id}`} userId={me.user.id} church={profile.data}>
          <ServicesArchive church={profile.data} />
        </DraftProvider>
      ) : (
        <ListSkeleton />
      )}
    </main>
  );
}

function ServicesArchive({ church }: { church: ChurchProfile }) {
  const { draft } = useDraft();
  const router = useRouter();
  const list = useServices();
  const open = useOpenService(church);
  const remove = useDeleteService(church);
  const newService = useNewService(church);
  const newButton = useRef<HTMLButtonElement>(null);
  const [replacing, setReplacing] = useState<ServiceSummary | null>(null);
  const [deleting, setDeleting] = useState<ServiceSummary | null>(null);
  const [opening, setOpening] = useState<string | null>(null);
  const editingId = draft.editing?.service_id ?? null;
  const draftDate = formatServiceDate(draft.readings.date_iso);

  function openNow(s: ServiceSummary) {
    setReplacing(null);
    setOpening(s.id);
    open.mutate(s.id, {
      onSuccess: () => router.push("/builder/review"),
      onSettled: () => setOpening(null),
    });
  }

  const items = list.data?.pages.flatMap((page) => page.items) ?? [];
  const total = list.data?.pages.at(-1)?.total ?? 0;

  let body;
  if (list.isPending) body = <ListSkeleton />;
  else if (list.isError && !list.data) body = <ErrorState error={list.error} onRetry={() => void list.refetch()} retrying={list.isRefetching} />;
  else if (items.length === 0) {
    body = (
      <EmptyState
        title="No saved services yet"
        description="Services you save from the builder appear here."
        action={
          <Link href="/builder" className={buttonVariants({ size: "touch" })}>
            Build a service
          </Link>
        }
      />
    );
  } else {
    body = (
      <>
        <ul className="grid gap-2">
          {items.map((s) => (
            <ServiceRow
              key={s.id}
              service={s}
              editing={s.id === editingId}
              opening={opening === s.id}
              disabled={opening !== null}
              onOpen={() => (isDirty(draft) ? setReplacing(s) : openNow(s))}
              onDelete={() => setDeleting(s)}
            />
          ))}
        </ul>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm text-muted-foreground">
            Showing {items.length} of {total}
          </p>
          {list.hasNextPage ? (
            <PendingButton
              variant="outline"
              size="touch"
              pending={list.isFetchingNextPage}
              pendingLabel="Loading…"
              onClick={() => void list.fetchNextPage()}
            >
              Show more
            </PendingButton>
          ) : null}
        </div>
        {list.isFetchNextPageError ? <ErrorState error={list.error} onRetry={() => void list.fetchNextPage()} /> : null}
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="Services"
        description={`Saved services for ${church.name}.`}
        actions={
          <Button ref={newButton} size="touch" onClick={() => newService.start()}>
            New service
          </Button>
        }
      />
      {body}
      <ConfirmDialog
        open={replacing !== null}
        onOpenChange={(next) => {
          if (!next) setReplacing(null);
        }}
        title="Replace your unsaved draft?"
        description={`Your current draft${draftDate ? ` for ${draftDate}` : ""} has changes that aren't saved to the archive. Opening this service replaces it.`}
        confirmLabel="Replace draft"
        onConfirm={() => {
          if (replacing) openNow(replacing);
        }}
        destructive
      />
      <ConfirmDialog
        open={deleting !== null}
        onOpenChange={(next) => {
          if (!next && !remove.isPending) setDeleting(null);
        }}
        title="Delete this service?"
        description={deleting ? deleteDescription(deleting, church.name, deleting.id === editingId) : undefined}
        confirmLabel="Delete service"
        pending={remove.isPending}
        onConfirm={() => {
          if (deleting) remove.mutate(deleting.id, { onSettled: () => setDeleting(null) });
        }}
        finalFocus={newButton}
        destructive
      />
      {newService.dialog}
    </>
  );
}

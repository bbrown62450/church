"use client";

import { useRef } from "react";

import { ErrorState } from "@/components/app/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useChurch } from "@/lib/church-context";
import { useMembers } from "@/lib/queries/people";
import { leaveBlock } from "@/lib/settings/people";

import { DeleteChurchCard } from "./delete-church-card";
import { LeaveChurchCard } from "./leave-church-card";
import { TransferOwnershipCard } from "./transfer-ownership-card";

export const OWNER_ONLY_NOTE = "Only the owner can transfer ownership or delete the church.";

/**
 * `/settings/danger` (slice 6b-2b; 6b spec UX §2). Admins and members see
 * that only the owner can transfer or delete, and Leave church. The owner
 * sees Leave church (off, with why), Transfer ownership and Delete church,
 * once the member list (who can become the owner; how many people a delete
 * removes) has loaded.
 */
export function DangerZonePage() {
  const church = useChurch();
  const heading = useRef<HTMLHeadingElement>(null);
  return (
    <section aria-labelledby="danger-title" className="grid gap-6">
      <h2 id="danger-title" ref={heading} tabIndex={-1} className="text-lg font-semibold outline-none">
        Danger zone
      </h2>
      {church.role === "owner" ? (
        <OwnerCards churchName={church.name} focusAfterTransfer={() => heading.current} />
      ) : (
        <>
          <p role="note" className="rounded-lg border bg-muted/50 px-3 py-2 text-sm">
            {OWNER_ONLY_NOTE}
          </p>
          <LeaveChurchCard churchName={church.name} block={null} />
        </>
      )}
    </section>
  );
}

function OwnerCards({ churchName, focusAfterTransfer }: { churchName: string; focusAfterTransfer(): HTMLElement | null }) {
  const members = useMembers();
  if (members.data) {
    const people = members.data.items;
    return (
      <>
        <LeaveChurchCard churchName={churchName} block={leaveBlock("owner", people.length)} />
        <TransferOwnershipCard churchName={churchName} members={people} onTransferred={focusAfterTransfer} />
        <DeleteChurchCard churchName={churchName} memberCount={people.length} />
      </>
    );
  }
  if (members.isError) {
    return <ErrorState error={members.error} onRetry={() => void members.refetch()} retrying={members.isFetching} />;
  }
  return (
    <div role="status" aria-label="Loading" className="grid gap-4">
      <Skeleton className="h-28 w-full" />
      <Skeleton className="h-36 w-full" />
      <Skeleton className="h-28 w-full" />
    </div>
  );
}

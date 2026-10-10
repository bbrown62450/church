"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { CopyLinkButton } from "@/components/app/copy-link-button";
import { EmptyState } from "@/components/app/empty-state";
import { ErrorState } from "@/components/app/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import type { Invite } from "@/lib/api/types";
import { roleLabel } from "@/lib/church";
import { useInvites, useRevokeInvite } from "@/lib/queries/people";
import { displayName, formatExpiry } from "@/lib/settings/people";
import { buildInviteUrl } from "@/lib/urls";

const ANYONE = "Anyone with the link";

/**
 * Pending invites ({n}) (owners and admins; 6b spec UX 1c): the live links,
 * newest first, each with who can use it, its role and type, when it
 * expires and who made it, **Copy link** and **Revoke** (after a
 * confirmation). Used single-use links, expired and revoked ones are not listed.
 */
export function PendingInvitesList({ churchName }: { churchName: string }) {
  const list = useInvites({ enabled: true });
  const revoke = useRevokeInvite();
  const headingRef = useRef<HTMLHeadingElement>(null);
  const [revoking, setRevoking] = useState<Invite | null>(null);
  // After a revoke the row and its button are gone, so focus goes to the heading.
  const revoked = useRef(false);

  let body: ReactNode;
  if (list.data) {
    body =
      list.data.items.length === 0 ? (
        <EmptyState title="No pending invites" description={`Create an invite link above to add someone to ${churchName}.`} />
      ) : (
        <ul className="divide-y rounded-lg border" aria-label="Pending invites">
          {list.data.items.map((invite) => (
            <InviteRow
              key={invite.id}
              invite={invite}
              onRevoke={() => {
                revoked.current = false;
                setRevoking(invite);
              }}
            />
          ))}
        </ul>
      );
  } else if (list.isError) {
    body = <ErrorState error={list.error} onRetry={() => void list.refetch()} retrying={list.isFetching} />;
  } else {
    body = (
      <div role="status" aria-label="Loading" className="grid gap-2">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
    );
  }

  return (
    <section aria-labelledby="invites-title" className="grid gap-3">
      <h3 id="invites-title" ref={headingRef} tabIndex={-1} className="text-base font-medium outline-none">
        {list.data ? `Pending invites (${list.data.items.length})` : "Pending invites"}
      </h3>
      {body}
      <ConfirmDialog
        open={revoking !== null}
        onOpenChange={(open) => {
          // while the revoke runs the confirmation stays open
          if (!open && !revoke.isPending) setRevoking(null);
        }}
        title="Revoke this invite?"
        description="The link will stop working. People who already joined stay in the church."
        confirmLabel="Revoke invite"
        pendingLabel="Revoking…"
        destructive
        pending={revoke.isPending}
        finalFocus={() => (revoked.current ? headingRef.current : true)}
        onConfirm={() => {
          if (revoking === null) return;
          const id = revoking.id;
          revoke.mutate(id, {
            onSuccess: () => {
              revoked.current = true;
            },
            onError: (e) => {
              if (e.status === 404) revoked.current = true; // gone elsewhere: gone all the same
            },
            onSettled: () => setRevoking((current) => (current?.id === id ? null : current)),
          });
        }}
      />
    </section>
  );
}

function InviteRow({ invite, onRevoke }: { invite: Invite; onRevoke(): void }) {
  const who = invite.email ?? ANYONE;
  const url = buildInviteUrl(invite.code);
  const expiry = formatExpiry(invite.expires_at);
  const creator = invite.created_by ? displayName(invite.created_by) : null;
  const [showLink, setShowLink] = useState(false);
  const linkRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!showLink) return;
    linkRef.current?.focus();
    linkRef.current?.select();
  }, [showLink]);

  return (
    <li className="grid gap-2 px-3 py-3 sm:px-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="min-w-0 font-medium [overflow-wrap:anywhere]">{who}</span>
        <Badge variant="outline">{roleLabel(invite.role)}</Badge>
        <Badge variant="secondary">{invite.reusable ? "Reusable" : "Single use"}</Badge>
      </div>
      <p className="text-sm text-muted-foreground [overflow-wrap:anywhere]">
        <time dateTime={invite.expires_at} title={expiry.full} aria-label={`Expires ${expiry.full}`}>
          Expires {expiry.relative}
        </time>
        {creator !== null ? ` · Created by ${creator}` : " · Created by a former member"}
      </p>
      {showLink ? (
        <Input ref={linkRef} readOnly value={url} aria-label={`Invite link for ${who}`} className="h-11 font-mono" />
      ) : null}
      <div className="flex flex-wrap gap-2">
        <CopyLinkButton
          text={url}
          label={`Copy link for ${who}`}
          onCopyFailed={() => {
            if (showLink) linkRef.current?.select();
            else setShowLink(true);
          }}
          variant="outline"
          size="touch"
          className="md:h-8"
        />
        <Button
          type="button"
          variant="destructive"
          size="touch"
          className="md:h-8"
          aria-label={`Revoke the invite for ${who}`}
          onClick={() => onRevoke()}
        >
          Revoke
        </Button>
      </div>
    </li>
  );
}

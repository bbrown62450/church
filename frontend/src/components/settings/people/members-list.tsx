"use client";

import { EllipsisVerticalIcon, Loader2Icon } from "lucide-react";
import { useRef, useState, type ReactNode } from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { ErrorState } from "@/components/app/error-state";
import { InitialsAvatar } from "@/components/app/initials-avatar";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import type { Church, InviteList, Member } from "@/lib/api/types";
import { isAdmin, roleLabel } from "@/lib/church";
import { useChangeRole, useInvites, useMembers, useRemoveMember } from "@/lib/queries/people";
import { displayName, invitesCreatedBy, memberActions, otherReusableInvites } from "@/lib/settings/people";
import { cn } from "@/lib/utils";

export const MEMBERS_NOTE = "Only admins can change roles or remove people. To add someone, ask an admin for an invite link.";

const ROLE_BADGE: Record<Member["role"], "default" | "secondary" | "outline"> = {
  owner: "default",
  admin: "secondary",
  member: "outline",
};

/** "1 invite link" or "2 invite links". */
function links(n: number, kind: string): string {
  return `${n} ${kind} link${n === 1 ? "" : "s"}`;
}

/**
 * Members ({n}) (6b spec UX 1b): every member in the server's order, with an
 * initials avatar, the name (a **You** badge on your own row), the email under
 * it and a role badge. For owners and admins, rows they may act on end in a
 * menu: **Make admin** or **Make member** (at once, no confirmation) and
 * **Remove from church** (after a confirmation that says which invite links
 * stop working).
 */
export function MembersList({ actor, churchName }: { actor: { id: string; role: Church["role"] }; churchName: string }) {
  const admin = isAdmin(actor.role);
  const list = useMembers();
  const invites = useInvites({ enabled: admin });
  const changeRole = useChangeRole();
  const remove = useRemoveMember();
  const headingRef = useRef<HTMLHeadingElement>(null);
  const [removing, setRemoving] = useState<Member | null>(null);
  // The confirmation keeps its person while it closes (removing is null by then).
  const [shown, setShown] = useState<Member | null>(null);
  const [revokeReusable, setRevokeReusable] = useState(true);
  // After a removal the row and its menu are gone, so focus goes to the heading.
  const removed = useRef(false);

  const changingId = changeRole.isPending ? changeRole.variables?.userId : undefined;

  let body: ReactNode;
  if (list.data) {
    body = (
      <ul className="divide-y rounded-lg border" aria-label="Members">
        {list.data.items.map((m) => (
          <MemberRow
            key={m.user_id}
            member={m}
            actor={actor}
            busy={changingId === m.user_id}
            onChangeRole={(role) => changeRole.mutate({ userId: m.user_id, role })}
            onRemove={() => {
              removed.current = false;
              setRevokeReusable(true);
              setShown(m);
              setRemoving(m);
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
        <Skeleton className="h-16 w-full" />
      </div>
    );
  }

  return (
    <section aria-labelledby="members-title" className="grid gap-3">
      <div className="grid gap-1">
        <h3 id="members-title" ref={headingRef} tabIndex={-1} className="text-base font-medium outline-none">
          {list.data ? `Members (${list.data.items.length})` : "Members"}
        </h3>
        {admin ? null : <p className="text-sm text-muted-foreground">{MEMBERS_NOTE}</p>}
      </div>
      {body}
      {admin ? (
        <RemoveMemberDialog
          member={removing}
          shown={shown}
          churchName={churchName}
          invites={invites.data}
          revokeReusable={revokeReusable}
          onRevokeReusableChange={setRevokeReusable}
          pending={remove.isPending}
          finalFocus={() => (removed.current ? headingRef.current : true)}
          onOpenChange={(open) => {
            // while the removal runs the confirmation stays open
            if (!open && !remove.isPending) setRemoving(null);
          }}
          onConfirm={(revoke) => {
            if (removing === null) return;
            const userId = removing.user_id;
            remove.mutate(
              { userId, revokeReusable: revoke },
              {
                onSuccess: () => {
                  removed.current = true;
                },
                onError: (e) => {
                  if (e.status === 404) removed.current = true; // removed elsewhere: gone all the same
                },
                onSettled: () => setRemoving((current) => (current?.user_id === userId ? null : current)),
              },
            );
          }}
        />
      ) : null}
    </section>
  );
}

function MemberRow({
  member,
  actor,
  busy,
  onChangeRole,
  onRemove,
}: {
  member: Member;
  actor: { id: string; role: Church["role"] };
  busy: boolean;
  onChangeRole(role: "admin" | "member"): void;
  onRemove(): void;
}) {
  const name = displayName(member);
  const actions = memberActions(actor, member);
  const hasName = name !== member.email;
  return (
    <li className="flex items-center gap-3 px-3 py-3 sm:px-4">
      <InitialsAvatar name={member.name} email={member.email} />
      <div className="grid min-w-0 flex-1 gap-0.5">
        <p className="flex flex-wrap items-center gap-2 font-medium [overflow-wrap:anywhere]">
          <span className="min-w-0">{name}</span>
          {member.is_me ? <Badge variant="secondary">You</Badge> : null}
        </p>
        {hasName ? <p className="text-sm text-muted-foreground [overflow-wrap:anywhere]">{member.email}</p> : null}
      </div>
      <Badge variant={ROLE_BADGE[member.role]} className="shrink-0">
        {roleLabel(member.role)}
      </Badge>
      {actions.changeRoleTo !== null || actions.canRemove ? (
        <DropdownMenu>
          <DropdownMenuTrigger
            aria-label={`Actions for ${name}`}
            disabled={busy}
            aria-busy={busy || undefined}
            className={cn(buttonVariants({ variant: "ghost", size: "icon-lg" }), "size-11 shrink-0")}
          >
            {busy ? (
              <Loader2Icon className="animate-spin" aria-hidden="true" />
            ) : (
              <EllipsisVerticalIcon aria-hidden="true" />
            )}
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-auto min-w-44">
            {actions.changeRoleTo !== null ? (
              <DropdownMenuItem className="min-h-11 md:min-h-0" onClick={() => onChangeRole(actions.changeRoleTo!)}>
                {actions.changeRoleTo === "admin" ? "Make admin" : "Make member"}
              </DropdownMenuItem>
            ) : null}
            {actions.changeRoleTo !== null && actions.canRemove ? <DropdownMenuSeparator /> : null}
            {actions.canRemove ? (
              <DropdownMenuItem variant="destructive" className="min-h-11 md:min-h-0" onClick={() => onRemove()}>
                Remove from church
              </DropdownMenuItem>
            ) : null}
          </DropdownMenuContent>
        </DropdownMenu>
      ) : null}
    </li>
  );
}

/**
 * **Remove from church** (6b spec UX 1b): says what the removal does to the
 * person's access and to the invite links, and offers (checked) to revoke the
 * church's other reusable links too, since a reusable link would let the
 * removed person rejoin. The counts come from Pending invites when it has
 * loaded; otherwise the sentences speak generally.
 */
function RemoveMemberDialog({
  member,
  shown,
  churchName,
  invites,
  revokeReusable,
  onRevokeReusableChange,
  pending,
  finalFocus,
  onOpenChange,
  onConfirm,
}: {
  member: Member | null;
  shown: Member | null;
  churchName: string;
  invites: InviteList | undefined;
  revokeReusable: boolean;
  onRevokeReusableChange(value: boolean): void;
  pending: boolean;
  finalFocus(): HTMLElement | null | true;
  onOpenChange(open: boolean): void;
  onConfirm(revokeReusable: boolean): void;
}) {
  const name = shown ? displayName(shown) : "";
  const made = shown && invites ? invitesCreatedBy(invites.items, shown.user_id) : null;
  const others = shown && invites ? otherReusableInvites(invites.items, shown.user_id) : null;
  const showBox = others === null || others > 0;
  let sentence: string | null;
  if (made === null) sentence = `Any invite links ${name} created will stop working.`;
  else if (made === 0) sentence = null;
  else sentence = `The ${links(made, "invite")} ${name} created will stop working.`;
  return (
    <ConfirmDialog
      open={member !== null}
      onOpenChange={onOpenChange}
      title={`Remove ${name}?`}
      description={`${name} will lose access to ${churchName}. Services they saved stay in the archive.`}
      confirmLabel="Remove member"
      pendingLabel="Removing…"
      destructive
      wrapAnywhere
      pending={pending}
      finalFocus={finalFocus}
      onConfirm={() => onConfirm(showBox && revokeReusable)}
    >
      {sentence !== null || showBox ? (
        <div className="grid gap-3 text-sm [overflow-wrap:anywhere]">
          {sentence !== null ? <p className="text-muted-foreground">{sentence}</p> : null}
          {showBox ? (
            <div className="grid gap-1">
              <label className="flex min-h-11 cursor-pointer items-start gap-3 py-1">
                <input
                  type="checkbox"
                  className="mt-0.5 size-5 shrink-0 accent-primary"
                  checked={revokeReusable}
                  disabled={pending}
                  aria-describedby="remove-revoke-help"
                  onChange={(event) => onRevokeReusableChange(event.target.checked)}
                />
                <span className="font-medium">
                  {others === null ? "Also revoke every reusable invite link" : `Also revoke the ${links(others, "reusable invite")}`}
                </span>
              </label>
              <p id="remove-revoke-help" className="text-muted-foreground">
                Anyone with a reusable link, including {name}, can use it to rejoin until it expires. You can create a
                new link for everyone else.
              </p>
            </div>
          ) : null}
        </div>
      ) : null}
    </ConfirmDialog>
  );
}

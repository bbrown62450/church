"use client";

import Link from "next/link";
import { useRef, useState } from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { Member } from "@/lib/api/types";
import { useTransferOwnership } from "@/lib/queries/church";
import { displayName, transferCandidates, transferChoiceLabel } from "@/lib/settings/people";

import { CARD } from "./leave-church-card";

export const TRANSFER_TEXT = "The new owner can transfer ownership and delete the church. You'll become an admin.";
export const INVITE_FIRST = "Invite another member first to transfer ownership.";

/**
 * Transfer ownership (6b spec UX 2b), for the owner: choose anyone else in
 * the church (admins first), confirm, and they become the owner while you
 * become an admin; the page then turns to its admin form. Alone, the card
 * says to invite someone first, with a link to People.
 */
export function TransferOwnershipCard({
  churchName,
  members,
  onTransferred,
}: {
  churchName: string;
  members: readonly Member[];
  /** Where focus goes once the transfer is done (the card is about to go). */
  onTransferred(): HTMLElement | null;
}) {
  const transfer = useTransferOwnership();
  const candidates = transferCandidates(members);
  const [chosen, setChosen] = useState<string | null>(null);
  const [confirming, setConfirming] = useState<Member | null>(null);
  // The confirmation keeps its person while it closes (confirming is null by then).
  const [shown, setShown] = useState<Member | null>(null);
  const sent = useRef(false);
  const done = useRef(false);
  // Someone chosen who has left meanwhile is no longer chosen.
  const target = candidates.find((m) => m.user_id === chosen) ?? null;
  const items = Object.fromEntries(candidates.map((m) => [m.user_id, transferChoiceLabel(m)]));
  const name = shown ? displayName(shown) : "";

  return (
    <section aria-labelledby="transfer-title" className={CARD}>
      <h3 id="transfer-title" className="text-base font-medium">
        Transfer ownership
      </h3>
      {candidates.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          {INVITE_FIRST}{" "}
          <Link href="/settings/people" className="inline-flex min-h-11 items-center font-medium text-foreground underline underline-offset-4 md:min-h-0">
            Invite someone
          </Link>
        </p>
      ) : (
        <>
          <p className="text-sm text-muted-foreground">{TRANSFER_TEXT}</p>
          <div className="grid gap-2">
            <Label htmlFor="transfer-new-owner">New owner</Label>
            <Select
              value={target?.user_id ?? null}
              items={items}
              onValueChange={(value) => {
                if (typeof value === "string") setChosen(value);
              }}
            >
              <SelectTrigger
                id="transfer-new-owner"
                className="h-11 w-full min-w-0 overflow-hidden data-[size=default]:h-11 md:h-9 md:data-[size=default]:h-9"
              >
                <SelectValue placeholder="Choose a person" className="min-w-0">
                  {/* A long name is shortened with an ellipsis here; the list below wraps it. */}
                  {(value: string | null) => (
                    <span className="truncate">{value === null ? "Choose a person" : items[value]}</span>
                  )}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {candidates.map((m) => (
                  <SelectItem
                    key={m.user_id}
                    value={m.user_id}
                    textClassName="whitespace-normal [overflow-wrap:anywhere]"
                  >
                    {items[m.user_id]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Button
              type="button"
              size="touch"
              className="md:h-8"
              disabled={target === null}
              onClick={() => {
                sent.current = false;
                done.current = false;
                setShown(target);
                setConfirming(target);
              }}
            >
              Transfer ownership…
            </Button>
          </div>
          <ConfirmDialog
            open={confirming !== null}
            onOpenChange={(next) => {
              // while the transfer runs the confirmation stays open
              if (!next && !transfer.isPending) setConfirming(null);
            }}
            title={`Make ${name} the owner?`}
            description={`${name} will become the owner of ${churchName} and you'll become an admin. Only the new owner can transfer ownership back.`}
            confirmLabel="Transfer ownership"
            pending={transfer.isPending}
            pendingLabel="Transferring…"
            wrapAnywhere
            finalFocus={() => (done.current ? onTransferred() : true)}
            onConfirm={() => {
              if (confirming === null || sent.current) return;
              sent.current = true;
              transfer.mutate(confirming.user_id, {
                onSuccess: () => {
                  done.current = true;
                  setChosen(null);
                },
                onSettled: () => {
                  sent.current = false;
                  setConfirming(null);
                },
              });
            }}
          />
        </>
      )}
    </section>
  );
}

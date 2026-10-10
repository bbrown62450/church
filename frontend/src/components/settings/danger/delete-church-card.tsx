"use client";

import { useRef, useState } from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { deleteNameError, useDeleteChurch } from "@/lib/queries/church";
import { deleteNameMatches } from "@/lib/settings/people";

import { DESTRUCTIVE_CARD } from "./leave-church-card";

export function deleteText(church: string): string {
  return `Deleting ${church} removes it for everyone. Pending invite links stop working.`;
}

/** The Delete dialog's body (6b spec UX 2c; its first two sentences in the singular when the owner is alone). */
export function deleteBody(church: string, people: number): string {
  const who =
    people === 1
      ? `This removes ${church}. You're the only person in it, and you'll lose access to its services, hymns, contacts and settings.`
      : `This removes ${church} for all ${people} people in it. They'll lose access to its services, hymns, contacts and settings.`;
  return `${who} Your unsaved draft for ${church} on this device will be discarded. This can't be undone.`;
}

/**
 * Delete {church} (6b spec UX 2c), for the owner: a confirmation that also
 * needs the church's name typed exactly (capitals included; spaces around it
 * do not count), then the same exit as Leave. The server checks the name too:
 * its "Church name did not match." shows under the box.
 */
export function DeleteChurchCard({ churchName, memberCount }: { churchName: string; memberCount: number }) {
  const remove = useDeleteChurch();
  const [open, setOpen] = useState(false);
  const [typed, setTyped] = useState("");
  const [error, setError] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const sent = useRef(false);
  const matches = deleteNameMatches(typed, churchName);
  return (
    <section aria-labelledby="delete-title" className={DESTRUCTIVE_CARD}>
      <h3 id="delete-title" className="text-base font-medium [overflow-wrap:anywhere]">
        Delete {churchName}
      </h3>
      <p className="text-sm text-muted-foreground [overflow-wrap:anywhere]">{deleteText(churchName)}</p>
      <div>
        <Button
          type="button"
          variant="destructive"
          size="touch"
          className="md:h-8"
          onClick={() => {
            sent.current = false;
            setTyped("");
            setError(null);
            setOpen(true);
          }}
        >
          Delete church…
        </Button>
      </div>
      <ConfirmDialog
        open={open}
        onOpenChange={(next) => {
          // while the delete runs the confirmation stays open
          if (!next && remove.isPending) return;
          setOpen(next);
        }}
        title={`Delete ${churchName}?`}
        description={deleteBody(churchName, memberCount)}
        confirmLabel="Delete church"
        pending={remove.isPending}
        pendingLabel="Deleting…"
        confirmDisabled={!matches}
        destructive
        wrapAnywhere
        onConfirm={() => {
          if (!matches || sent.current) return;
          sent.current = true;
          setError(null);
          remove.mutate(typed, {
            onError: (e) => {
              sent.current = false;
              const message = deleteNameError(e);
              if (message === null) {
                setOpen(false);
                return;
              }
              setError(message);
              input.current?.focus();
            },
          });
        }}
      >
        <div className="grid gap-2">
          <Label htmlFor="delete-confirm-name" className="block leading-snug [overflow-wrap:anywhere]">
            Type {churchName} to confirm
          </Label>
          <Input
            id="delete-confirm-name"
            ref={input}
            value={typed}
            onChange={(e) => {
              setTyped(e.target.value);
              setError(null);
            }}
            autoComplete="off"
            autoCapitalize="off"
            autoCorrect="off"
            spellCheck={false}
            className="h-11 md:h-9"
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? "delete-confirm-name-error" : undefined}
          />
          {error ? (
            <p id="delete-confirm-name-error" className="text-sm text-destructive">
              {error}
            </p>
          ) : null}
        </div>
      </ConfirmDialog>
    </section>
  );
}

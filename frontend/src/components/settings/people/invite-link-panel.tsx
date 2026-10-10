"use client";

import { useEffect, useRef } from "react";

import { CopyLinkButton } from "@/components/app/copy-link-button";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { Invite } from "@/lib/api/types";
import { formatDateTime, inviteSummary } from "@/lib/settings/people";
import { buildInviteUrl } from "@/lib/urls";

/**
 * **Invite link ready** (6b spec UX 1a): the new link in a read-only box (it
 * scrolls inside the box, never the page), **Copy link** (focused when the
 * panel opens), **Share…** where the device can share (phones), who can use
 * the link and until when, and **Done**. The invite stays in Pending invites.
 */
export function InviteLinkPanel({ invite, churchName, onDone }: { invite: Invite; churchName: string; onDone(): void }) {
  const url = buildInviteUrl(invite.code);
  const inputRef = useRef<HTMLInputElement>(null);
  const copyRef = useRef<HTMLButtonElement>(null);
  const canShare = typeof navigator !== "undefined" && typeof navigator.share === "function";

  useEffect(() => {
    copyRef.current?.focus();
  }, [invite.id]);

  function selectLink() {
    inputRef.current?.focus();
    inputRef.current?.select();
  }

  return (
    <div role="group" aria-labelledby="invite-ready-title" className="grid gap-3 rounded-lg border bg-muted/40 p-3">
      <h4 id="invite-ready-title" className="text-sm font-medium">
        Invite link ready
      </h4>
      <div className="grid gap-1.5">
        <Label htmlFor="invite-link">Invite link</Label>
        <Input
          id="invite-link"
          ref={inputRef}
          readOnly
          value={url}
          className="h-11 font-mono"
          onFocus={(event) => event.currentTarget.select()}
        />
      </div>
      <p className="text-sm text-muted-foreground [overflow-wrap:anywhere]">{inviteSummary(invite, churchName, (iso) => formatDateTime(iso))}</p>
      <div className="flex flex-col gap-2 sm:flex-row">
        <CopyLinkButton ref={copyRef} text={url} onCopyFailed={selectLink} size="touch" className="w-full sm:w-fit" />
        {canShare ? (
          <Button
            type="button"
            variant="outline"
            size="touch"
            className="w-full sm:w-fit"
            onClick={() => {
              navigator
                .share({ title: `Join ${churchName}`, text: `You're invited to plan worship with ${churchName}.`, url })
                .catch(() => {}); // a cancelled share does nothing
            }}
          >
            Share…
          </Button>
        ) : null}
        <Button type="button" variant="ghost" size="touch" className="w-full sm:w-fit" onClick={() => onDone()}>
          Done
        </Button>
      </div>
    </div>
  );
}

"use client";

import { useRef, useState, type FormEvent } from "react";

import { PendingButton } from "@/components/app/pending-button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import type { Invite, InviteBody } from "@/lib/api/types";
import { inviteFieldError, useCreateInvite, useInvites } from "@/lib/queries/people";

import { InviteLinkPanel } from "./invite-link-panel";

export const ROLE_HELP = {
  member: "Can build, save and email services, and edit hymns.",
  admin: "Can also change church settings, invite people and manage members.",
} as const;
export const EMAIL_HELP = "Only the Google account with this email will be able to use the link.";
export const REUSABLE_HELP = "Let several people join with the same link. Otherwise the link works once.";
export const ONE_EMAIL_ONCE = "A link for one email address works once.";
export const INVITE_CREATED = "Invite link created.";

type Role = InviteBody["role"];
type FieldErrors = Partial<Record<"email" | "reusable", string>>;

/**
 * Invite someone (owners and admins; 6b spec UX 1a): the role (Member by
 * default), an optional email (only that Google account can use the link)
 * and "Reusable for 7 days" (off, and off while an email is typed). **Create
 * invite link** sends a new request each time; the link then shows below.
 */
export function CreateInviteForm({ churchName }: { churchName: string }) {
  const create = useCreateInvite();
  const invites = useInvites({ enabled: true });
  const emailRef = useRef<HTMLInputElement>(null);
  const reusableRef = useRef<HTMLInputElement>(null);
  const submitRef = useRef<HTMLButtonElement>(null);
  const [role, setRole] = useState<Role>("member");
  const [email, setEmail] = useState("");
  const [reusable, setReusable] = useState(false);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [created, setCreated] = useState<Invite | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const emailBound = email.trim() !== "";
  // A link revoked since (in Pending invites, or by a removal) leaves the panel too.
  const shown =
    created !== null && (invites.data === undefined || invites.data.items.some((i) => i.id === created.id))
      ? created
      : null;

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (create.isPending) return;
    setAnnouncement("");
    const body: InviteBody = { role, email: emailBound ? email.trim() : null, reusable: emailBound ? false : reusable };
    create.mutate(body, {
      onSuccess: (invite) => {
        setRole("member");
        setEmail("");
        setReusable(false);
        setErrors({});
        setCreated(invite);
        setAnnouncement(INVITE_CREATED);
      },
      onError: (e) => {
        const found = inviteFieldError(e);
        if (found === null) return;
        setErrors({ [found.field]: found.message });
        (found.field === "email" ? emailRef : reusableRef).current?.focus();
      },
    });
  }

  return (
    <section aria-labelledby="invite-title" className="grid gap-4 rounded-lg border p-4">
      <h3 id="invite-title" className="text-base font-medium">
        Invite someone
      </h3>
      <form onSubmit={onSubmit} noValidate className="grid gap-4">
        <div className="grid gap-1.5">
          <span id="invite-role-label" className="text-sm font-medium">
            Role
          </span>
          <RadioGroup
            aria-labelledby="invite-role-label"
            value={role}
            onValueChange={(value) => setRole(value as Role)}
            className="grid gap-2 sm:grid-cols-2"
          >
            {(["member", "admin"] as const).map((value) => (
              <label
                key={value}
                className="flex min-h-11 cursor-pointer items-start gap-3 rounded-lg border p-3 has-data-checked:border-primary"
              >
                <RadioGroupItem value={value} aria-describedby={`invite-role-${value}-help`} className="mt-0.5" />
                <span className="grid min-w-0 gap-0.5">
                  <span className="text-sm font-medium">{value === "member" ? "Member" : "Admin"}</span>
                  <span id={`invite-role-${value}-help`} className="text-sm text-muted-foreground">
                    {ROLE_HELP[value]}
                  </span>
                </span>
              </label>
            ))}
          </RadioGroup>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="invite-email">Email (optional)</Label>
          <Input
            id="invite-email"
            ref={emailRef}
            type="email"
            inputMode="email"
            autoComplete="off"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            maxLength={320}
            value={email}
            className="h-11"
            aria-invalid={errors.email ? true : undefined}
            aria-describedby={errors.email ? "invite-email-error invite-email-help" : "invite-email-help"}
            onChange={(event) => {
              setEmail(event.target.value);
              if (errors.email || errors.reusable) setErrors({});
            }}
          />
          {errors.email ? (
            <p id="invite-email-error" role="alert" className="text-sm text-destructive">
              {errors.email}
            </p>
          ) : null}
          <p id="invite-email-help" className="text-sm text-muted-foreground">
            {EMAIL_HELP}
          </p>
        </div>
        <div className="grid gap-1">
          <label className={`flex min-h-11 items-center gap-3 ${emailBound ? "opacity-70" : "cursor-pointer"}`}>
            <input
              ref={reusableRef}
              type="checkbox"
              className="size-5 shrink-0 accent-primary"
              checked={!emailBound && reusable}
              disabled={emailBound}
              aria-describedby="invite-reusable-help"
              aria-invalid={errors.reusable ? true : undefined}
              onChange={(event) => {
                setReusable(event.target.checked);
                if (errors.reusable) setErrors({});
              }}
            />
            <span className="text-sm font-medium">Reusable for 7 days</span>
          </label>
          {errors.reusable ? (
            <p role="alert" className="text-sm text-destructive">
              {errors.reusable}
            </p>
          ) : null}
          <p id="invite-reusable-help" className="text-sm text-muted-foreground">
            {emailBound ? ONE_EMAIL_ONCE : REUSABLE_HELP}
          </p>
        </div>
        <PendingButton
          ref={submitRef}
          type="submit"
          size="touch"
          className="w-full sm:w-fit"
          pending={create.isPending}
          pendingLabel="Creating…"
        >
          Create invite link
        </PendingButton>
      </form>
      <p className="sr-only" aria-live="polite">
        {shown ? announcement : ""}
      </p>
      {shown ? (
        <InviteLinkPanel
          invite={shown}
          churchName={churchName}
          onDone={() => {
            setCreated(null);
            setAnnouncement("");
            submitRef.current?.focus();
          }}
        />
      ) : null}
    </section>
  );
}

"use client";

import { isAdmin } from "@/lib/church";
import { useChurch } from "@/lib/church-context";
import { useMeContext } from "@/lib/me-context";

import { CreateInviteForm } from "./create-invite-form";
import { MembersList } from "./members-list";
import { PendingInvitesList } from "./pending-invites-list";

/**
 * `/settings/people` (slice 6b-2a; 6b spec UX §1): everyone in the church,
 * with emails, for every role. Owners and admins also see Invite someone
 * above the list and Pending invites below it, change roles and remove
 * people.
 */
export function PeopleSettingsPage() {
  const church = useChurch();
  const me = useMeContext();
  const admin = isAdmin(church.role);
  return (
    <section aria-labelledby="people-title" className="grid gap-6">
      <div className="grid gap-1">
        <h2 id="people-title" className="text-lg font-semibold">
          People
        </h2>
        <p className="text-sm text-muted-foreground">Everyone in {church.name} can see this list.</p>
      </div>
      {admin ? <CreateInviteForm churchName={church.name} /> : null}
      <MembersList actor={{ id: me.user.id, role: church.role }} churchName={church.name} />
      {admin ? <PendingInvitesList churchName={church.name} /> : null}
    </section>
  );
}

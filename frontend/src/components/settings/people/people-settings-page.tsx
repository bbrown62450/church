"use client";

import { useChurch } from "@/lib/church-context";
import { useMeContext } from "@/lib/me-context";

import { MembersList } from "./members-list";

/**
 * `/settings/people` (slice 6b-2a; 6b spec UX §1): everyone in the church,
 * with emails, for every role; owners and admins also change roles and
 * remove people.
 */
export function PeopleSettingsPage() {
  const church = useChurch();
  const me = useMeContext();
  return (
    <section aria-labelledby="people-title" className="grid gap-6">
      <div className="grid gap-1">
        <h2 id="people-title" className="text-lg font-semibold">
          People
        </h2>
        <p className="text-sm text-muted-foreground">Everyone in {church.name} can see this list.</p>
      </div>
      <MembersList actor={{ id: me.user.id, role: church.role }} churchName={church.name} />
    </section>
  );
}

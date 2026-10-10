"use client";

import type { ReactNode } from "react";

import { PageHeader } from "@/components/app/page-header";
import { SettingsNav } from "@/components/settings/settings-nav";
import type { Church } from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";

const YOU_ARE: Record<Church["role"], string> = { owner: "the owner", admin: "an admin", member: "a member" };

/**
 * The Settings area (6a spec "Settings nav"; slice 6a-1): the "Settings"
 * heading with who you are in the church, the section nav, and the section's
 * page beside it from `md` (under it on phones).
 */
export default function SettingsLayout({ children }: { children: ReactNode }) {
  const church = useChurch();
  return (
    <main className="mx-auto grid w-full max-w-5xl content-start gap-4 px-4 py-4">
      <PageHeader
        title="Settings"
        description={`You're ${YOU_ARE[church.role]} of ${church.name}.`}
        // a long church name with no spaces wraps instead of widening the page
        descriptionClassName="[overflow-wrap:anywhere]"
      />
      <div className="grid gap-4 md:grid-cols-[11rem_minmax(0,1fr)] md:items-start">
        <SettingsNav />
        <div className="min-w-0 max-w-3xl">{children}</div>
      </div>
    </main>
  );
}

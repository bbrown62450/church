"use client";

import { isAdmin } from "@/lib/church";
import { useChurch } from "@/lib/church-context";
import { useHymnals } from "@/lib/queries/hymns";

import { HymnLibrary } from "./hymn-library";
import { HymnalsCard } from "./hymnals-card";

export const HYMNS_INTRO = "The hymnals and hymns the builder offers when you choose hymns.";

/**
 * `/settings/hymns` (slice 6a-2; 6a spec UX §2; owner's 6a-2 answers of
 * 2026-10-07): the church's hymnals (`HymnalsCard`) and its hymn library.
 * Every member reads both and adds and edits hymns; owners and admins also
 * delete hymns, set a hymn's year and familiarity, and add or remove hymnals.
 */
export function HymnsSettingsPage() {
  const church = useChurch();
  const admin = isAdmin(church.role);
  const hymnals = useHymnals();
  return (
    <section aria-labelledby="hymns-title" className="grid gap-6">
      <div className="grid gap-1">
        <h2 id="hymns-title" className="text-lg font-semibold">
          Hymns
        </h2>
        <p className="text-sm text-muted-foreground">{HYMNS_INTRO}</p>
      </div>
      <HymnalsCard admin={admin} hymnals={hymnals} />
      <HymnLibrary admin={admin} hymnals={hymnals.data} />
    </section>
  );
}

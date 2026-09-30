/**
 * The four builder steps (F §4.7; S "steps.ts"). Every step has its own
 * route and is always reachable (F D9).
 *
 * `SHIPPED_STEPS` holds the steps whose content has shipped. An unshipped
 * step shows the "Available soon" card, the muted status "Soon" (Review: "Not
 * in archive"), and `stillNeeded` ignores it. Slice 2b shipped none (owner
 * answer Q1, 2026-09-28); slice 2c ships "readings" and slice 3b "hymns".
 * Slice 4 adds "liturgy", 5a "review".
 */
import type { StepId } from "./schema";

export type { StepId } from "./schema";

export type Step = {
  id: StepId;
  /** 1-4, as shown in "Step 1 of 4". */
  number: number;
  label: string;
  /** The footer's "Next: …" name. */
  short: string;
  href: `/builder/${StepId}`;
  previous: StepId | null;
  next: StepId | null;
};

export const STEPS: readonly Step[] = [
  { id: "readings", number: 1, label: "Date & readings", short: "Readings", href: "/builder/readings", previous: null, next: "hymns" },
  { id: "hymns", number: 2, label: "Hymns", short: "Hymns", href: "/builder/hymns", previous: "readings", next: "liturgy" },
  { id: "liturgy", number: 3, label: "Liturgy", short: "Liturgy", href: "/builder/liturgy", previous: "hymns", next: "review" },
  { id: "review", number: 4, label: "Review & send", short: "Review", href: "/builder/review", previous: "liturgy", next: null },
];

export const SHIPPED_STEPS: ReadonlySet<StepId> = new Set<StepId>(["readings", "hymns"]);

export function stepById(id: StepId): Step {
  const step = STEPS.find((s) => s.id === id);
  if (!step) throw new Error(`Unknown step ${id}`);
  return step;
}

/** The step a builder path belongs to ("/builder/hymns" → "hymns"); null for "/builder" and anything else. */
export function stepFromPath(pathname: string): StepId | null {
  const match = /^\/builder\/([a-z]+)\/?$/.exec(pathname);
  if (!match) return null;
  return STEPS.some((s) => s.id === match[1]) ? (match[1] as StepId) : null;
}

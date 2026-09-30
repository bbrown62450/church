/**
 * The Hymns step's draft transitions and selectors (S "Pure-function
 * contracts"; F §4.6). Pure: each returns the same object when nothing
 * changes, so `update(recipe)` stays a no-op. The draft recipes (`setSlot`,
 * `clearSlot`, `setHymnal`, `setExcludeRecent`) take the whole draft; the
 * suggestion helpers take the `hymns` block, as S names them.
 */
import type { Hymn, HymnSuggestions } from "@/lib/api/types";
import { SLOTS, type DraftV1, type HymnPick, type Slot } from "@/lib/draft/schema";

type HymnsBlock = DraftV1["hymns"];

/** What a slot stores for a hymn: its id and a snapshot of its title, number and hymnal. */
export function pickFromHymn(h: Pick<Hymn, "id" | "title" | "number" | "hymnal">): HymnPick {
  return { hymn_id: h.id, title: h.title, number: h.number, hymnal: h.hymnal };
}

function samePick(a: HymnPick | null, b: HymnPick | null): boolean {
  if (a === null || b === null) return a === b;
  return a.hymn_id === b.hymn_id && a.title === b.title && a.number === b.number && a.hymnal === b.hymnal;
}

function withHymns(d: DraftV1, patch: Partial<HymnsBlock>): DraftV1 {
  return { ...d, hymns: { ...d.hymns, ...patch } };
}

/** Sets one slot (the picker, a match's "Add", Undo). */
export function setSlot(d: DraftV1, slot: Slot, pick: HymnPick | null): DraftV1 {
  if (samePick(d.hymns.slots[slot], pick)) return d;
  return withHymns(d, { slots: { ...d.hymns.slots, [slot]: pick } });
}

/** The ✕ button. */
export function clearSlot(d: DraftV1, slot: Slot): DraftV1 {
  return setSlot(d, slot, null);
}

/**
 * The hymnal Select. The church's effective hymnal is stored as `null`, like
 * the translation (2c), so choosing it again is not unsaved work and a later
 * default change flows through (owner answer 1; clarification 2). Picks are
 * never touched.
 */
export function setHymnal(d: DraftV1, code: string, effective: string | null): DraftV1 {
  const hymnal = code === effective ? null : code;
  return d.hymns.hymnal === hymnal ? d : withHymns(d, { hymnal });
}

/** The Exclude switch. It never changes a slot or an idea (AC12). */
export function setExcludeRecent(d: DraftV1, on: boolean): DraftV1 {
  return d.hymns.exclude_recent === on ? d : withHymns(d, { exclude_recent: on });
}

export type Reconciled = { status: "ok"; live: Hymn } | { status: "loading" } | { status: "missing" };

/**
 * A pick against its hymnal's loaded list (S "Live data"): the live hymn, or
 * "loading" while that list is not loaded, or "missing" when the pick has no
 * id or its id is not in the list. A pick with no hymnal (an archived one,
 * 5a) is looked up in `fallbackHymnal`, the selected one.
 */
export function reconcilePick(
  pick: HymnPick,
  lists: ReadonlyMap<string, readonly Hymn[] | undefined>,
  fallbackHymnal: string | null,
): Reconciled {
  if (pick.hymn_id === null) return { status: "missing" };
  const code = pick.hymnal ?? fallbackHymnal;
  const list = code === null ? undefined : lists.get(code);
  if (list === undefined) return { status: "loading" };
  const live = list.find((h) => h.id === pick.hymn_id);
  return live ? { status: "ok", live } : { status: "missing" };
}

/**
 * The AI's answer applied to the latest hymns (S "AI suggestion flow" 2; F
 * D16): an empty slot takes the first hymn that no other slot holds once the
 * slots before it are filled (a slot emptied while the request ran could
 * otherwise repeat another slot's hymn), and its ideas are the rest (2 to 4);
 * a filled slot keeps its pick and its ideas are the answer without it (3 to
 * 4). The ideas are dated, so they hide when the service date changes.
 */
export function applySuggestions(hymns: HymnsBlock, resp: HymnSuggestions, dateIso: string): HymnsBlock {
  const slots = { ...hymns.slots };
  const bySlot = { opening: [], response: [], closing: [] } as Record<Slot, HymnPick[]>;
  for (const slot of SLOTS) {
    const list = resp.slots[slot];
    const current = slots[slot];
    if (current === null) {
      const held = new Set(SLOTS.map((other) => slots[other]?.hymn_id ?? null));
      const top = list.find((h) => !held.has(h.id));
      if (top) slots[slot] = pickFromHymn(top);
      bySlot[slot] = list.filter((h) => h !== top).slice(0, 4).map(pickFromHymn);
    } else {
      bySlot[slot] = list.filter((h) => h.id !== current.hymn_id).slice(0, 4).map(pickFromHymn);
    }
  }
  return { ...hymns, slots, alternatives: { for_date_iso: dateIso, by_slot: bySlot } };
}

/**
 * A tap on an idea (S "Other ideas"): the slot takes it and the previous pick
 * takes its place among the ideas, unless there was none or it already is an
 * idea; so a second tap swaps back.
 */
export function swapAlternative(hymns: HymnsBlock, slot: Slot, hymnId: string): HymnsBlock {
  const ideas = hymns.alternatives?.by_slot[slot] ?? [];
  const at = ideas.findIndex((idea) => idea.hymn_id === hymnId);
  if (hymns.alternatives === null || at < 0) return hymns;
  const previous = hymns.slots[slot];
  const keepPrevious = previous !== null && !ideas.some((idea) => idea.hymn_id === previous.hymn_id);
  const next = keepPrevious ? ideas.map((idea, i) => (i === at ? previous : idea)) : ideas.filter((_, i) => i !== at);
  return {
    ...hymns,
    slots: { ...hymns.slots, [slot]: ideas[at] },
    alternatives: { ...hymns.alternatives, by_slot: { ...hymns.alternatives.by_slot, [slot]: next } },
  };
}

/** For each slot, the other slots holding the same hymn (the "Also chosen as…" notice). */
export function duplicateSlots(slots: DraftV1["hymns"]["slots"]): Record<Slot, Slot[]> {
  const result = { opening: [], response: [], closing: [] } as Record<Slot, Slot[]>;
  for (const slot of SLOTS) {
    const id = slots[slot]?.hymn_id ?? null;
    if (id === null) continue;
    result[slot] = SLOTS.filter((other) => other !== slot && slots[other]?.hymn_id === id);
  }
  return result;
}

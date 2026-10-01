"use client";

/**
 * `LiturgyGenerationProvider` and `useLiturgyGeneration()` (slice 4 spec,
 * Frontend `generation.tsx`; UX "Generate and Regenerate"). Mounted in the
 * builder shell inside the draft provider, so a run keeps going while the
 * member moves between steps and its result lands in the draft; leaving
 * `/builder`, switching church (the keyed remount) or signing out unmounts it
 * and cancels everything.
 *
 * - Runs, card errors and Undo live here, in memory, never in the draft
 *   (owner answer 1, 2026-09-30: none of them is unsaved work).
 * - `generate(keys, {aiAvailable, bulk})`: with AI off it sends nothing and
 *   marks each switched-on empty card "AI not configured" (S step 0).
 *   Otherwise every key is queued; the batch first reads the sermon text once
 *   (the effective NT reading, WEB for ESV, `queryClient.fetchQuery` through
 *   `passageQuery`, at most 10 s; a failure or a timeout just leaves it out),
 *   then each section is one request, at most 3 in flight.
 * - The card is captured (`captureCard`) when the member asks (the click, or
 *   "Replace text"), not when the request starts. Before a queued request is
 *   sent, and again when its answer arrives, `staleVerdict` decides against
 *   the current draft: "apply" sends it, then writes the text (origin "ai",
 *   Undo when it replaced text, inside the draft update); otherwise nothing
 *   is sent or written and S's toast says why. So text that became the
 *   member's while the card waited (Undo, another tab) is never replaced
 *   without the confirm dialog.
 * - "New service" (a new `created_at`) cancels every run silently and clears
 *   the errors and Undo; a bulk run ends with one toast, "The service
 *   changed, so the AI drafts were discarded.". A result racing that change
 *   (another tab) still meets the stale rule.
 * - A 429 stops the queue: that card and every queued one show the retry
 *   message, with the moment the wait ends (`retryAt`), so leaving the step
 *   and coming back does not restart it. A 401 or a lost church goes to the app's handling
 *   (`reportAuthErrors`) and shows nothing on the card.
 * - A bulk run ends with one toast: "Wrote n sections." or "Wrote k of n
 *   sections. The rest show what went wrong." (cancelled cards not counted).
 */
import { useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { isNoChurchAccess } from "@/lib/api/errors";
import type { ChurchProfile, SectionResult, SermonText } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import type { SectionKey } from "@/lib/draft/schema";
import { reportAuthErrors, useApi } from "@/lib/queries/client";
import { generateSection } from "@/lib/queries/liturgy";
import { passageQuery } from "@/lib/queries/passages";

import {
  applyGenerated,
  captureCard,
  restoreCard,
  staleVerdict,
  type CapturedCard,
  type CardSnapshot,
  type StaleVerdict,
} from "./cards";
import { cardErrorFrom, localAiNotConfigured, type CardError } from "./errors";
import { createTaskQueue, type TaskOutcome } from "./queue";
import { buildGenerateRequest, sermonSource, sermonText } from "./request";
import { SECTION_LABELS } from "./sections";

/** At most 3 requests in flight, leaving one of the server's 4 AI slots free (S step 3). */
export const MAX_IN_FLIGHT = 3;
/** How long a batch waits for the sermon text before going without it (S "Sermon text"). */
export const SERMON_WAIT_MS = 10_000;

export type CardRun = { phase: "queued" | "writing"; since: number };
export type UndoEntry = { kind: "replaced" | "cleared"; previous: CardSnapshot };
export type BulkRun = { total: number; done: number };
/**
 * A card's error as the step shows it: `retryAt` (ms since the epoch) is when
 * a 429's wait ends; `bulk` marks an error from "Generate empty sections",
 * announced politely rather than as one alert per card.
 */
export type CardErrorState = CardError & { retryAt?: number; bulk?: boolean };

export type LiturgyGeneration = {
  runs: Partial<Record<SectionKey, CardRun>>;
  errors: Partial<Record<SectionKey, CardErrorState>>;
  undo: Partial<Record<SectionKey, UndoEntry>>;
  /** "Generate empty sections" while it runs. */
  bulk: BulkRun | null;
  generate: (keys: SectionKey[], opts: { aiAvailable: boolean; bulk?: boolean }) => void;
  /** Cancels these cards' runs (every run when omitted); the cards return to where they were. */
  cancel: (keys?: SectionKey[]) => void;
  /** The AI bar's Cancel: the whole bulk run. */
  cancelBulk: () => void;
  dismissError: (key: SectionKey) => void;
  setUndo: (key: SectionKey, entry: UndoEntry | null) => void;
  clearUndo: () => void;
  applyUndo: (key: SectionKey) => void;
};

const GenerationContext = createContext<LiturgyGeneration | null>(null);

type Bulk = { keys: Set<SectionKey>; total: number; done: number; written: number };

/** A queued run that found its card changed before it was sent: nothing is sent. */
class StaleRun extends Error {
  constructor(readonly verdict: Exclude<StaleVerdict, "apply">) {
    super(verdict);
  }
}

export const SERVICE_CHANGED_BULK = "The service changed, so the AI drafts were discarded.";

function staleToast(key: SectionKey, verdict: Exclude<StaleVerdict, "apply">): void {
  const label = SECTION_LABELS[key];
  toast.message(
    verdict === "service_changed"
      ? `The service changed, so the AI draft for ${label} was discarded.`
      : `Kept your edits — the new AI draft for ${label} was not used.`,
  );
}

function errorState(error: CardError, bulk: boolean): CardErrorState {
  return error.retryAfterSeconds === undefined
    ? { ...error, bulk }
    : { ...error, bulk, retryAt: Date.now() + error.retryAfterSeconds * 1000 };
}

function without<T>(record: Partial<Record<SectionKey, T>>, keys: readonly SectionKey[]): Partial<Record<SectionKey, T>> {
  if (!keys.some((key) => key in record)) return record;
  const next = { ...record };
  for (const key of keys) delete next[key];
  return next;
}

function bulkToast(written: number, done: number): void {
  if (done === 0) return;
  if (written === done) toast.message(done === 1 ? "Wrote 1 section." : `Wrote ${done} sections.`);
  else toast.message(`Wrote ${written} of ${done} sections. The rest show what went wrong.`);
}

export function LiturgyGenerationProvider({
  church,
  sermonWaitMs = SERMON_WAIT_MS,
  children,
}: {
  church: Pick<ChurchProfile, "id" | "effective_translation">;
  /** Tests shorten the sermon-text wait. */
  sermonWaitMs?: number;
  children: ReactNode;
}) {
  const { draft, update, peek } = useDraft();
  const api = useApi();
  const queryClient = useQueryClient();
  const [queue] = useState(() => createTaskQueue({ concurrency: MAX_IN_FLIGHT }));
  const [runs, setRuns] = useState<Partial<Record<SectionKey, CardRun>>>({});
  const [errors, setErrors] = useState<Partial<Record<SectionKey, CardErrorState>>>({});
  const [undo, setUndoState] = useState<Partial<Record<SectionKey, UndoEntry>>>({});
  const [bulk, setBulk] = useState<BulkRun | null>(null);
  const mounted = useRef(true);
  /** Cards waiting for their batch's sermon text: key → batch id. */
  const pending = useRef(new Map<SectionKey, number>());
  /** Each batch's sermon-text wait, aborted when all of its cards are cancelled. */
  const batches = useRef(new Map<number, AbortController>());
  const captured = useRef(new Map<SectionKey, CapturedCard>());
  const bulkRef = useRef<Bulk | null>(null);
  const batchSeq = useRef(0);
  const service = useRef(draft.created_at);

  useEffect(() => {
    mounted.current = true;
    const waits = batches.current;
    return () => {
      mounted.current = false;
      queue.cancelAll();
      for (const controller of waits.values()) controller.abort();
    };
  }, [queue]);

  // "New service" (or a saved service loaded): the runs, errors and Undo belonged to the old draft.
  const createdAt = draft.created_at;
  useEffect(() => {
    if (service.current === createdAt) return;
    service.current = createdAt;
    queue.cancelAll();
    for (const controller of batches.current.values()) controller.abort();
    batches.current.clear();
    pending.current.clear();
    captured.current.clear();
    const hadBulk = bulkRef.current !== null;
    bulkRef.current = null;
    setRuns({});
    setErrors({});
    setUndoState({});
    setBulk(null);
    if (hadBulk) toast.message(SERVICE_CHANGED_BULK);
  }, [createdAt, queue]);

  const setError = useCallback((key: SectionKey, error: CardErrorState | null) => {
    setErrors((current) => (error === null ? without(current, [key]) : { ...current, [key]: error }));
  }, []);

  const setUndo = useCallback((key: SectionKey, entry: UndoEntry | null) => {
    setUndoState((current) => (entry === null ? without(current, [key]) : { ...current, [key]: entry }));
  }, []);

  /** A card left the bulk run: settled (counted, `wrote` when applied) or cancelled (not counted). */
  const leaveBulk = useCallback((key: SectionKey, how: "wrote" | "failed" | "cancelled") => {
    const b = bulkRef.current;
    if (b === null || !b.keys.has(key)) return;
    b.keys.delete(key);
    if (how === "cancelled") b.total -= 1;
    else b.done += 1;
    if (how === "wrote") b.written += 1;
    if (b.keys.size === 0) {
      bulkRef.current = null;
      setBulk(null);
      bulkToast(b.written, b.done);
    } else {
      setBulk({ total: b.total, done: b.done });
    }
  }, []);

  /** Drops a card's run: waiting for the sermon text, queued or writing. */
  const dropRun = useCallback(
    (key: SectionKey) => {
      const batch = pending.current.get(key);
      pending.current.delete(key);
      if (batch !== undefined && ![...pending.current.values()].includes(batch)) {
        batches.current.get(batch)?.abort();
        batches.current.delete(batch);
      }
      queue.cancel(key);
      captured.current.delete(key);
    },
    [queue],
  );

  const applyResult = useCallback(
    (key: SectionKey, text: string): boolean => {
      const cap = captured.current.get(key);
      captured.current.delete(key);
      if (!cap) return false;
      const out: { verdict: StaleVerdict; previous: CardSnapshot | null } = { verdict: "apply", previous: null };
      update((d) => {
        out.verdict = staleVerdict(d, key, cap);
        if (out.verdict !== "apply") return d;
        const card = d.liturgy.cards[key];
        out.previous = { text: card.text, origin: card.origin };
        return applyGenerated(d, key, text);
      });
      if (out.verdict !== "apply") {
        staleToast(key, out.verdict);
        return false;
      }
      // Over text: Undo brings it back. Over a blank card: any "Cleared." line is stale now.
      const replaced = out.previous !== null && out.previous.text.trim() !== "";
      setUndo(key, replaced && out.previous !== null ? { kind: "replaced", previous: out.previous } : null);
      return true;
    },
    [update, setUndo],
  );

  const settle = useCallback(
    (key: SectionKey, outcome: TaskOutcome<SectionResult>) => {
      if (!mounted.current) return;
      setRuns((current) => without(current, [key]));
      const inBulk = bulkRef.current?.keys.has(key) ?? false;
      if (!outcome.ok && outcome.error instanceof StaleRun) {
        captured.current.delete(key);
        staleToast(key, outcome.error.verdict);
        leaveBulk(key, "failed");
        return;
      }
      if (outcome.ok) {
        const result = outcome.value;
        if (result.status !== "error" && result.text !== null) {
          leaveBulk(key, applyResult(key, result.text) ? "wrote" : "failed");
          return;
        }
        captured.current.delete(key);
        const failure = cardErrorFrom(result.error ?? new Error("no text"));
        setError(key, failure === null ? null : errorState(failure, inBulk));
        leaveBulk(key, "failed");
        return;
      }
      captured.current.delete(key);
      const e = outcome.error;
      if (e instanceof ApiError && (e.status === 401 || isNoChurchAccess(e))) reportAuthErrors(e, church.id);
      const error = cardErrorFrom(e);
      setError(key, error === null ? null : errorState(error, inBulk));
      leaveBulk(key, error === null ? "cancelled" : "failed");
      if (error !== null && e instanceof ApiError && e.code === "rate_limited") {
        // S step 7: the whole queue stops, and every card still waiting shows the same message.
        const waiting = [...queue.waitingKeys(), ...pending.current.keys()] as SectionKey[];
        const stamped = errorState(error, inBulk);
        for (const other of waiting) {
          const otherInBulk = bulkRef.current?.keys.has(other) ?? false;
          dropRun(other);
          setError(other, { ...stamped, bulk: otherInBulk });
          leaveBulk(other, "failed");
        }
        setRuns((current) => without(current, waiting));
      }
    },
    [applyResult, church.id, dropRun, leaveBulk, queue, setError],
  );

  const loadSermon = useCallback(
    (signal: AbortSignal): Promise<SermonText | null> => {
      const source = sermonSource(peek(), church.effective_translation);
      if (source === null) return Promise.resolve(null);
      return new Promise((resolve) => {
        const done = (value: SermonText | null) => {
          clearTimeout(timer);
          signal.removeEventListener("abort", onAbort);
          resolve(value);
        };
        const onAbort = () => done(null);
        const timer = setTimeout(() => done(null), sermonWaitMs);
        signal.addEventListener("abort", onAbort, { once: true });
        queryClient.fetchQuery(passageQuery(api, source.translation, source.ref)).then(
          (passage) => done(sermonText(source.ref, passage)),
          () => done(null),
        );
      });
    },
    [api, church.effective_translation, peek, queryClient, sermonWaitMs],
  );

  const send = useCallback(
    (key: SectionKey, sermon: SermonText | null) => {
      queue.push(
        key,
        (signal) => {
          // S step 6 before sending: text that became the member's while the card waited is never replaced.
          const draft = peek();
          const cap = captured.current.get(key);
          const verdict = cap === undefined ? "service_changed" : staleVerdict(draft, key, cap);
          if (verdict !== "apply") return Promise.reject(new StaleRun(verdict));
          setRuns((current) => ({ ...current, [key]: { phase: "writing", since: Date.now() } }));
          return generateSection(api.church, key, buildGenerateRequest(draft, key, sermon), signal);
        },
        (outcome) => settle(key, outcome),
      );
    },
    [api, peek, queue, settle],
  );

  const generate = useCallback(
    (keys: SectionKey[], { aiAvailable, bulk: isBulk = false }: { aiAvailable: boolean; bulk?: boolean }) => {
      const draft = peek();
      if (!aiAvailable) {
        // S step 0: nothing is sent; each targeted switched-on empty card says so.
        const empty = keys.filter((key) => {
          const card = draft.liturgy.cards[key];
          return card.enabled && card.text.trim() === "";
        });
        const marked = errorState(localAiNotConfigured(), isBulk);
        setErrors((current) => ({ ...current, ...Object.fromEntries(empty.map((key) => [key, marked])) }));
        return;
      }
      const busy = new Set<SectionKey>([...pending.current.keys(), ...(queue.runningKeys() as SectionKey[]), ...(queue.waitingKeys() as SectionKey[])]);
      const fresh = keys.filter((key) => !busy.has(key));
      if (fresh.length === 0) return;
      const since = Date.now();
      // The card as the member saw it when they asked (the click, or "Replace text").
      for (const key of fresh) captured.current.set(key, captureCard(draft, key));
      setErrors((current) => without(current, fresh));
      setRuns((current) => ({ ...current, ...Object.fromEntries(fresh.map((key) => [key, { phase: "queued", since }])) }));
      if (isBulk) {
        bulkRef.current = { keys: new Set(fresh), total: fresh.length, done: 0, written: 0 };
        setBulk({ total: fresh.length, done: 0 });
      }
      const batch = ++batchSeq.current;
      const controller = new AbortController();
      batches.current.set(batch, controller);
      for (const key of fresh) pending.current.set(key, batch);
      void loadSermon(controller.signal).then((sermon) => {
        batches.current.delete(batch);
        if (!mounted.current) return;
        for (const key of fresh) {
          if (pending.current.get(key) !== batch) continue; // cancelled while waiting
          pending.current.delete(key);
          send(key, sermon);
        }
      });
    },
    [loadSermon, peek, queue, send],
  );

  const cancel = useCallback(
    (keys?: SectionKey[]) => {
      const targets =
        keys ?? ([...pending.current.keys(), ...queue.runningKeys(), ...queue.waitingKeys()] as SectionKey[]);
      for (const key of targets) {
        dropRun(key);
        leaveBulk(key, "cancelled");
      }
      setRuns((current) => without(current, targets));
    },
    [dropRun, leaveBulk, queue],
  );

  const cancelBulk = useCallback(() => {
    const b = bulkRef.current;
    if (b) cancel([...b.keys]);
  }, [cancel]);

  const dismissError = useCallback((key: SectionKey) => setError(key, null), [setError]);
  const clearUndo = useCallback(() => setUndoState({}), []);
  const applyUndo = useCallback(
    (key: SectionKey) => {
      const entry = undo[key];
      if (!entry) return;
      update((d) => restoreCard(d, key, entry.previous));
      setUndo(key, null);
    },
    [undo, update, setUndo],
  );

  const value = useMemo<LiturgyGeneration>(
    () => ({ runs, errors, undo, bulk, generate, cancel, cancelBulk, dismissError, setUndo, clearUndo, applyUndo }),
    [runs, errors, undo, bulk, generate, cancel, cancelBulk, dismissError, setUndo, clearUndo, applyUndo],
  );
  return <GenerationContext value={value}>{children}</GenerationContext>;
}

/** The generation state and actions. Throws outside `LiturgyGenerationProvider` (the builder shell mounts it). */
export function useLiturgyGeneration(): LiturgyGeneration {
  const value = useContext(GenerationContext);
  if (!value) throw new Error("useLiturgyGeneration() must be used inside <LiturgyGenerationProvider>.");
  return value;
}

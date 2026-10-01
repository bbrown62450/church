"use client";

/**
 * `LiturgyReviewProvider` and `useLiturgyReview()` (reviewer spec, "User
 * experience"; slice 4 spec, reviewer amendment "UI hooks"). Mounted in the
 * builder shell inside the generation provider, beside it, so a review keeps
 * going while the member moves between steps; leaving `/builder`, switching
 * church or signing out unmounts it and cancels everything.
 *
 * - The notes live here, in memory only (`notes.ts`): never in the draft, the
 *   archive or `localStorage`.
 * - `start()`: every switched-on card with text (`reviewTargets`), captured
 *   when pressed, with the same resolved sermon text as generation
 *   (`useSermonLoader`), in one `POST /liturgy/review` (100 s). Once the
 *   sermon text has loaded the cards are checked again (4b's pre-send check):
 *   a card changed meanwhile is left out, and a new service sends nothing.
 *   The answer replaces the last review; a card changed meanwhile gets no notes, and a
 *   new service drops the answer (`applyReview`). `cancel()` aborts the wait
 *   and keeps the notes already shown. A request-level failure (timeout, the
 *   network, a 5xx) keeps them too and shows its message in `error`; a 401 or
 *   a lost church goes to the app's handling and shows nothing.
 * - Every draft change prunes the notes of cards whose text or origin changed
 *   (`pruneReview`); a new service (a new `created_at`) cancels the review and
 *   every revision silently and drops all notes.
 * - `revise(key)`: an AI card with notes left; its text and remaining notes,
 *   with the sermon text, in one `POST /liturgy/revise` (100 s); it returns
 *   whether it started. Nothing is sent while a 429's wait is not over
 *   (`rateLimitedUntil`, Generate's or Revise's: the card shows the wait), nor
 *   when the card changed while the sermon text loaded (the same toast as
 *   below); a 429 here starts that wait for Generate too. The result
 *   replaces the card (origin "ai") only while the card still holds what was
 *   sent and the service is the same; then the generation provider's Undo
 *   line ("revised") keeps the previous text and origin. Otherwise nothing
 *   changes and a toast says why. A failure shows on the card's notes.
 * - `announcement`: the polite line read out when a review ends.
 */
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
import type { ChurchProfile } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import type { DraftV1, LiturgyCard, SectionKey } from "@/lib/draft/schema";
import { reportAuthErrors, useApi } from "@/lib/queries/client";
import { reviewService, reviseSection } from "@/lib/queries/liturgy";

import { applyGenerated, type CardSnapshot } from "./cards";
import { cardErrorFrom, rateLimitMessage, type CardError } from "./errors";
import { useLiturgyGeneration } from "./generation";
import { applyReview, canRevise, captureReview, dismissNote, noteCount, pruneReview, type ServiceReview } from "./notes";
import { buildReviewRequest, buildReviseRequest, reviewTargets } from "./request";
import { SECTION_LABELS } from "./sections";
import { useSermonLoader } from "./sermon";

export type LiturgyReview = {
  review: ServiceReview | null;
  running: boolean;
  /** The last review's request-level failure (its message), or null. */
  error: string | null;
  /** Read out politely when a review ends. */
  announcement: string;
  start: () => void;
  cancel: () => void;
  dismiss: (where: SectionKey | "service", id: string) => void;
  /** Cards whose revision is running. */
  revising: Partial<Record<SectionKey, true>>;
  reviseErrors: Partial<Record<SectionKey, CardError>>;
  /** True when the revision started (an AI card with notes left, not already revising). */
  revise: (key: SectionKey) => boolean;
  cancelRevise: (key: SectionKey) => void;
};

const ReviewContext = createContext<LiturgyReview | null>(null);

/** The line read out when a review ends; `quickOnly` when its AI part was missing. */
export function reviewDoneMessage(notes: number, quickOnly = false): string {
  const done = notes === 0 ? "Review finished. No notes." : notes === 1 ? "Review finished. 1 note." : `Review finished. ${notes} notes.`;
  return quickOnly ? `${done} Only quick checks ran.` : done;
}

type Sent = { createdAt: string; text: string; origin: LiturgyCard["origin"] };
type ReviseVerdict = "apply" | "service_changed" | "edited";

/** Slice 4's stale rule for a revision: the card must still hold what was sent, in the same service. */
function reviseVerdict(d: DraftV1, key: SectionKey, sent: Sent): ReviseVerdict {
  if (d.created_at !== sent.createdAt) return "service_changed";
  const now = d.liturgy.cards[key];
  return now.text !== sent.text || now.origin !== sent.origin ? "edited" : "apply";
}

function reviseToast(key: SectionKey, verdict: Exclude<ReviseVerdict, "apply">): void {
  const label = SECTION_LABELS[key];
  toast.message(
    verdict === "service_changed"
      ? `The service changed, so the revised draft for ${label} was discarded.`
      : `Kept your edits, so the revised draft for ${label} was not used.`,
  );
}

function without<T>(record: Partial<Record<SectionKey, T>>, key: SectionKey): Partial<Record<SectionKey, T>> {
  if (!(key in record)) return record;
  const next = { ...record };
  delete next[key];
  return next;
}

export function LiturgyReviewProvider({
  church,
  sermonWaitMs,
  children,
}: {
  church: Pick<ChurchProfile, "id" | "effective_translation">;
  /** Tests shorten the sermon-text wait. */
  sermonWaitMs?: number;
  children: ReactNode;
}) {
  const { draft, update, peek } = useDraft();
  const api = useApi();
  const { setUndo, rateLimitedUntil, noteRateLimit } = useLiturgyGeneration();
  const loadSermon = useSermonLoader(church, sermonWaitMs);
  const [review, setReview] = useState<ServiceReview | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const [revising, setRevising] = useState<Partial<Record<SectionKey, true>>>({});
  const [reviseErrors, setReviseErrors] = useState<Partial<Record<SectionKey, CardError>>>({});
  const reviewRef = useRef<ServiceReview | null>(null);
  const active = useRef<AbortController | null>(null);
  const revisions = useRef(new Map<SectionKey, AbortController>());
  const mounted = useRef(true);
  const service = useRef(draft.created_at);

  useEffect(() => {
    reviewRef.current = review;
  }, [review]);

  useEffect(() => {
    mounted.current = true;
    const waits = revisions.current;
    return () => {
      mounted.current = false;
      active.current?.abort();
      for (const controller of waits.values()) controller.abort();
    };
  }, []);

  // Every draft change, during render: notes whose card changed go (typing, Regenerate, Revise, Clear text, the
  // church default, Undo), so they never show for a single frame, and an Undo never brings them back.
  const [pruned, setPruned] = useState(draft);
  if (pruned !== draft) {
    setPruned(draft);
    setReview((current) => pruneReview(current, draft));
  }

  // A new service (or a saved one loaded): the review and every revision belonged to the old draft.
  const createdAt = draft.created_at;
  useEffect(() => {
    if (service.current === createdAt) return;
    service.current = createdAt;
    active.current?.abort();
    active.current = null;
    for (const controller of revisions.current.values()) controller.abort();
    revisions.current.clear();
    setRunning(false);
    setRevising({});
    setReviseErrors({});
    setError(null);
    setReview(null);
  }, [createdAt]);

  const handleFailure = useCallback(
    (e: unknown): CardError | null => {
      if (e instanceof ApiError && (e.status === 401 || isNoChurchAccess(e))) reportAuthErrors(e, church.id);
      return cardErrorFrom(e);
    },
    [church.id],
  );

  const start = useCallback(() => {
    if (active.current !== null) return;
    const asked = peek();
    const keys = reviewTargets(asked);
    if (keys.length === 0) return;
    const ask = captureReview(asked, keys);
    const controller = new AbortController();
    active.current = controller;
    setRunning(true);
    setError(null);
    setAnnouncement("");
    setReviseErrors({});
    void (async () => {
      try {
        const sermon = await loadSermon(controller.signal);
        if (controller.signal.aborted) return;
        // 4b's pre-send check: after the sermon wait a new service sends nothing, and a card changed meanwhile is left out.
        const now = peek();
        const fresh = keys.filter((key) => {
          const was = ask.cards[key];
          const card = now.liturgy.cards[key];
          return was !== undefined && card.text === was.text && card.origin === was.origin;
        });
        if (now.created_at !== ask.createdAt || fresh.length === 0) return;
        const result = await reviewService(api.church, buildReviewRequest(asked, fresh, sermon), controller.signal);
        if (!mounted.current || active.current !== controller) return;
        const { review: next } = applyReview(peek(), ask, result);
        setReview(next);
        if (next !== null) setAnnouncement(reviewDoneMessage(noteCount(next), next.aiStatus !== "ok"));
      } catch (e) {
        if (!mounted.current || active.current !== controller) return;
        setError(handleFailure(e)?.message ?? null);
      } finally {
        if (active.current === controller) {
          active.current = null;
          if (mounted.current) setRunning(false);
        }
      }
    })();
  }, [api, handleFailure, loadSermon, peek]);

  const cancel = useCallback(() => {
    active.current?.abort();
    active.current = null;
    setRunning(false);
  }, []);

  const dismiss = useCallback((where: SectionKey | "service", id: string) => {
    setReview((current) => (current === null ? null : dismissNote(current, where, id)));
  }, []);

  const revise = useCallback(
    (key: SectionKey) => {
      if (revisions.current.has(key)) return false;
      const asked = peek();
      const card = asked.liturgy.cards[key];
      const notes = reviewRef.current?.cards[key];
      if (!canRevise(card, notes) || notes === undefined) return false;
      if (rateLimitedUntil !== null && Date.now() < rateLimitedUntil) {
        // A 429's wait (Generate's or Revise's) is not over: nothing is sent, and the card shows the wait.
        const seconds = Math.ceil((rateLimitedUntil - Date.now()) / 1000);
        const waiting: CardError = { code: "rate_limited", message: rateLimitMessage(seconds), retryable: true, retryAfterSeconds: seconds };
        setReviseErrors((current) => ({ ...current, [key]: waiting }));
        return false;
      }
      const sent: Sent = { createdAt: asked.created_at, text: card.text, origin: card.origin };
      const controller = new AbortController();
      revisions.current.set(key, controller);
      setRevising((current) => ({ ...current, [key]: true }));
      setReviseErrors((current) => without(current, key));
      void (async () => {
        try {
          const sermon = await loadSermon(controller.signal);
          if (controller.signal.aborted) return;
          // 4b's pre-send check: a card changed while the sermon text loaded sends nothing.
          const before = reviseVerdict(peek(), key, sent);
          if (before !== "apply") {
            reviseToast(key, before);
            return;
          }
          const body = buildReviseRequest(asked, key, notes.notes.map((n) => n.text), sermon);
          const text = await reviseSection(api.church, body, controller.signal);
          if (!mounted.current || revisions.current.get(key) !== controller) return;
          const out: { verdict: ReviseVerdict; previous: CardSnapshot | null } = { verdict: "apply", previous: null };
          update((d) => {
            out.verdict = reviseVerdict(d, key, sent);
            if (out.verdict !== "apply") return d;
            const now = d.liturgy.cards[key];
            out.previous = { text: now.text, origin: now.origin };
            return applyGenerated(d, key, text);
          });
          if (out.verdict !== "apply") reviseToast(key, out.verdict);
          else if (out.previous !== null) setUndo(key, { kind: "revised", previous: out.previous, after: text });
        } catch (e) {
          if (!mounted.current || revisions.current.get(key) !== controller) return;
          const failure = handleFailure(e);
          if (failure?.retryAfterSeconds !== undefined) noteRateLimit(Date.now() + failure.retryAfterSeconds * 1000);
          if (failure !== null) setReviseErrors((current) => ({ ...current, [key]: failure }));
        } finally {
          if (revisions.current.get(key) === controller) {
            revisions.current.delete(key);
            if (mounted.current) setRevising((current) => without(current, key));
          }
        }
      })();
      return true;
    },
    [api, handleFailure, loadSermon, noteRateLimit, peek, rateLimitedUntil, setUndo, update],
  );

  const cancelRevise = useCallback((key: SectionKey) => {
    revisions.current.get(key)?.abort();
    revisions.current.delete(key);
    setRevising((current) => without(current, key));
  }, []);

  const value = useMemo<LiturgyReview>(
    () => ({ review, running, error, announcement, start, cancel, dismiss, revising, reviseErrors, revise, cancelRevise }),
    [review, running, error, announcement, start, cancel, dismiss, revising, reviseErrors, revise, cancelRevise],
  );
  return <ReviewContext value={value}>{children}</ReviewContext>;
}

/** The review state and actions. Throws outside `LiturgyReviewProvider` (the builder shell mounts it). */
export function useLiturgyReview(): LiturgyReview {
  const value = useContext(ReviewContext);
  if (!value) throw new Error("useLiturgyReview() must be used inside <LiturgyReviewProvider>.");
  return value;
}

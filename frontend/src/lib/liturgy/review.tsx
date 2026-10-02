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
 * - `start()`: every switched-on card with text (`reviewTargets`; never a
 *   Benediction following the church default, owner 2026-10-02), captured
 *   when pressed, with the same resolved sermon text as generation
 *   (`useSermonLoader`), in one `POST /liturgy/review` (100 s). Once the
 *   sermon text has loaded the cards are checked again (4b's pre-send check):
 *   a card changed meanwhile is left out, and a new service sends nothing.
 *   The answer replaces the last review; a card changed meanwhile gets no notes, and a
 *   new service drops the answer (`applyReview`). `cancel()` aborts the wait
 *   and keeps the notes already shown. A request-level failure (timeout, the
 *   network, a 5xx) keeps them too and shows its message in `error`; a 401 or
 *   a lost church goes to the app's handling and shows nothing.
 * - Every draft change marks the notes of cards whose text or origin changed
 *   as stale, shown faded until the next review (`pruneReview`; reviewer
 *   follow-up 1); a successful Regenerate (`onWritten`) or Revise drops the
 *   card's notes (`forgetCard`); a new service (a new `created_at`) cancels
 *   the review and every revision silently and drops all notes.
 * - `revise(key)`: a card with notes left (`canRevise`: AI, typed or saved
 *   text; the card asks first for the last two); its text and remaining notes,
 *   with the sermon text, in one `POST /liturgy/revise` (100 s); it returns
 *   whether it started. Nothing is sent while the AI writes the card, nor while a 429's wait is not over
 *   (`rateLimitedUntil`, Generate's or Revise's: the card shows the wait), nor
 *   when the card changed while the sermon text loaded (the same toast as
 *   below); a 429 here starts that wait for Generate too. The result
 *   replaces the card (origin "ai") only while the card still holds what was
 *   sent and the service is the same; then the generation provider's Undo
 *   line ("revised") keeps the previous text and origin. Otherwise nothing
 *   changes and a toast says why. A failure shows on the card's notes.
 * - `reviseAcross(noteId)` (reviewer follow-up 2): "Revise the other
 *   prayers" on a "Several prayers open with "…"." note. The prayers are
 *   found again from the draft (`acrossTargets`); nothing is sent while any
 *   of them is being written, revised or waiting in a batch, or while a
 *   429's wait is not over. The others are revised one at a time, in service
 *   order (owner decision A), each through the same path as `revise` (its
 *   own stale rule, failure and Undo), with the one note `acrossNote`
 *   instead of its own notes; each later note also names the new openings
 *   the batch has produced so far. Every one of them shows as revising from
 *   the start, with its own Cancel: a Cancel on one not sent yet skips it,
 *   on the running one moves to the next. One edited meanwhile (its text or
 *   origin no longer what it was when the button was pressed), switched
 *   off (silently), or whose revision failed, is skipped and the batch goes
 *   on; a 429 stops it (the
 *   rest are not sent), as does one that cannot be sent at its turn (a 429's
 *   wait began meanwhile, shown on that card, or the AI is writing it) or the
 *   kept first prayer no longer opening with the words. Each success drops
 *   that card's own notes, as any revision does. The note goes once every one
 *   of them was revised, fewer than two prayers still share the opening (an
 *   Undo may have brought it back, or the AI kept it), and only while the review it came from is
 *   still the one shown (`generation`); otherwise it stays.
 * - `announcement`: the polite line read out when a review ends.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useLayoutEffect,
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
import {
  acrossNote,
  acrossTargets,
  applyReview,
  canRevise,
  captureReview,
  dismissNote,
  forgetCard,
  noteCount,
  openingWords,
  pruneReview,
  revisable,
  sharedOpening,
  type ServiceReview,
} from "./notes";
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
  /** A revision's failure; a 429's carries `retryAt` (ms since the epoch), when its wait ends. */
  reviseErrors: Partial<Record<SectionKey, ReviseError>>;
  /** True when the revision started (`canRevise`, not already revising, not being written, no 429 wait). */
  revise: (key: SectionKey) => boolean;
  /** "Revise the other prayers" on a shared-opening note, one at a time; true when the first revision started. */
  reviseAcross: (noteId: string) => boolean;
  /** Stops a card's revision, or takes it out of a "Revise the other prayers" batch before it is sent. */
  cancelRevise: (key: SectionKey) => void;
};

export type ReviseError = CardError & { retryAt?: number };

const ReviewContext = createContext<LiturgyReview | null>(null);

/** The line read out when a review ends; `quickOnly` when its AI part was missing. */
export function reviewDoneMessage(notes: number, quickOnly = false): string {
  const done = notes === 0 ? "Review finished. No notes." : notes === 1 ? "Review finished. 1 note." : `Review finished. ${notes} notes.`;
  return quickOnly ? `${done} Only quick checks ran.` : done;
}

type Sent = { createdAt: string; text: string; origin: LiturgyCard["origin"] };
type ReviseVerdict = "apply" | "service_changed" | "edited";
/** How one revision ended: the text put in the card (null when none was), and whether it was a 429. */
type ReviseEnd = { text: string | null; limited: boolean };
/** True when it started; "limited" when a 429's wait is not over; false for any other refusal. */
type StartRevise = (key: SectionKey, instead?: string[], onDone?: (end: ReviseEnd) => void) => boolean | "limited";

/** "Revise the other prayers" while it runs (owner decision A): one prayer at a time, in service order. */
type AcrossBatch = {
  noteId: string;
  /** The review the note came from (`ServiceReview.generation`). */
  generation: number | undefined;
  words: string;
  /** The kept prayer the note names ("like the …"). */
  first: SectionKey;
  firstLabel: string;
  /** The prayers not sent yet, each as it was when the button was pressed. */
  queue: { key: SectionKey; sent: Sent }[];
  /** The new openings so far, oldest first. */
  openings: string[];
  started: number;
  /** Every one so far was revised. */
  all: boolean;
};

function inBatch(batches: Set<AcrossBatch>, key: SectionKey): boolean {
  for (const batch of batches) if (batch.queue.some((q) => q.key === key)) return true;
  return false;
}

/** A Cancel on a prayer not sent yet: it leaves its batch, which then keeps the note. */
function leaveBatch(batches: Set<AcrossBatch>, key: SectionKey): void {
  for (const batch of batches) {
    const at = batch.queue.findIndex((q) => q.key === key);
    if (at < 0) continue;
    batch.queue.splice(at, 1);
    batch.all = false;
  }
}

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
  const { draft, update, peek, defaultBenediction } = useDraft();
  const api = useApi();
  const { runs, setUndo, rateLimitedUntil, noteRateLimit, onWritten } = useLiturgyGeneration();
  const loadSermon = useSermonLoader(church, sermonWaitMs);
  const [review, setReview] = useState<ServiceReview | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const [revising, setRevising] = useState<Partial<Record<SectionKey, true>>>({});
  const [reviseErrors, setReviseErrors] = useState<Partial<Record<SectionKey, ReviseError>>>({});
  const reviewRef = useRef<ServiceReview | null>(null);
  const active = useRef<AbortController | null>(null);
  const revisions = useRef(new Map<SectionKey, AbortController>());
  const mounted = useRef(true);
  const service = useRef(draft.created_at);
  const batches = useRef(new Set<AcrossBatch>());
  const startReviseRef = useRef<StartRevise | null>(null);
  /** `rateLimitedUntil` at commit, for a batch's refusal message. */
  const rateLimitedRef = useRef(rateLimitedUntil);
  /** Numbers each review shown (`ServiceReview.generation`). */
  const generation = useRef(0);

  // At commit, not after paint: a Revise pressed as soon as the notes show must see them (a passive effect could lag).
  useLayoutEffect(() => {
    reviewRef.current = review;
  }, [review]);

  useEffect(() => {
    mounted.current = true;
    const waits = revisions.current;
    const queued = batches.current;
    return () => {
      queued.clear();
      mounted.current = false;
      active.current?.abort();
      for (const controller of waits.values()) controller.abort();
    };
  }, []);

  // Every draft change, during render: notes whose card changed fade (typing, Undo, the church default, another
  // tab), and a blank card's go, so neither shows for a single frame as if nothing had changed.
  const [pruned, setPruned] = useState(draft);
  if (pruned !== draft) {
    setPruned(draft);
    setReview((current) => pruneReview(current, draft));
  }

  // A Regenerate (or Generate) wrote a new AI draft: the card's notes were about the text it replaced.
  useEffect(() => onWritten((key) => setReview((current) => forgetCard(current, key))), [onWritten]);

  // A new service (or a saved one loaded): the review and every revision belonged to the old draft.
  const createdAt = draft.created_at;
  useEffect(() => {
    if (service.current === createdAt) return;
    service.current = createdAt;
    active.current?.abort();
    active.current = null;
    batches.current.clear();
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
    const keys = reviewTargets(asked, defaultBenediction);
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
        generation.current += 1;
        setReview(next === null ? null : { ...next, generation: generation.current });
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
  }, [api, defaultBenediction, handleFailure, loadSermon, peek]);

  const cancel = useCallback(() => {
    active.current?.abort();
    active.current = null;
    setRunning(false);
  }, []);

  const dismiss = useCallback((where: SectionKey | "service", id: string) => {
    setReview((current) => (current === null ? null : dismissNote(current, where, id)));
  }, []);

  // One card's revision: with its remaining notes (`revise`), or with `instead` (`reviseAcross`). `onDone` hears
  // how it ended. A card waiting in a "Revise the other prayers" batch is left to the batch.
  const startRevise = useCallback<StartRevise>(
    (key, instead, onDone) => {
      if (revisions.current.has(key) || inBatch(batches.current, key)) return false;
      const asked = peek();
      const card = asked.liturgy.cards[key];
      const own = reviewRef.current?.cards[key];
      const notes = instead ?? (canRevise(card, own) && own !== undefined ? own.notes.map((n) => n.text) : []);
      if (!revisable(card) || notes.length === 0) return false;
      // The AI is writing this card (Generate, Regenerate, Try again): one request at a time per card.
      if (runs[key] !== undefined) return false;
      // A 429's wait (Generate's or Revise's) is not over: nothing is sent (the card shows the wait, its Revise off).
      if (rateLimitedUntil !== null && Date.now() < rateLimitedUntil) return "limited";
      const sent: Sent = { createdAt: asked.created_at, text: card.text, origin: card.origin };
      const controller = new AbortController();
      revisions.current.set(key, controller);
      setRevising((current) => ({ ...current, [key]: true }));
      setReviseErrors((current) => without(current, key));
      const end: ReviseEnd = { text: null, limited: false };
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
          const body = buildReviseRequest(asked, key, notes, sermon);
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
          else if (out.previous !== null) {
            setUndo(key, { kind: "revised", previous: out.previous, after: text });
            setReview((current) => forgetCard(current, key)); // the notes were addressed
            end.text = text;
          }
        } catch (e) {
          if (!mounted.current || revisions.current.get(key) !== controller) return;
          const failure = handleFailure(e);
          if (failure === null) return;
          // A 429's alert goes when its wait ends (`CardNotes`); Generate waits as long.
          const retryAt = failure.retryAfterSeconds === undefined ? undefined : Date.now() + failure.retryAfterSeconds * 1000;
          if (retryAt !== undefined) {
            noteRateLimit(retryAt);
            end.limited = true;
          }
          setReviseErrors((current) => ({ ...current, [key]: retryAt === undefined ? failure : { ...failure, retryAt } }));
        } finally {
          if (revisions.current.get(key) === controller) {
            revisions.current.delete(key);
            if (mounted.current) setRevising((current) => without(current, key));
          }
          if (mounted.current) onDone?.(end);
        }
      })();
      return true;
    },
    [api, handleFailure, loadSermon, noteRateLimit, peek, rateLimitedUntil, runs, setUndo, update],
  );

  // A batch moves on from a revision's end (its `finally`), which can come before any passive effect of the latest
  // render: kept at commit, so the next one is started with the latest committed guards (runs, the 429's wait).
  useLayoutEffect(() => {
    startReviseRef.current = startRevise;
    rateLimitedRef.current = rateLimitedUntil;
  }, [startRevise, rateLimitedUntil]);

  const revise = useCallback((key: SectionKey) => startRevise(key) === true, [startRevise]);

  // Sends a batch's next prayer, skipping one edited meanwhile; when none is left, the note goes if every one was
  // revised, fewer than two prayers still share the opening (an Undo may have brought one back) and its review is
  // still the one shown.
  const runAcross = useCallback(
    (batch: AcrossBatch) => {
      // Stops the batch: the rest (and `also`, the one at hand) are not sent and stop showing as revising; the note stays.
      const stop = (also: SectionKey[] = []): void => {
        const left = [...also, ...batch.queue.map((q) => q.key)];
        batch.queue = [];
        batch.all = false;
        setRevising((current) => left.reduce((acc, k) => without(acc, k), current));
      };
      const step = (): void => {
        if (!batches.current.has(batch)) return; // a new service, or the provider went
        for (let next = batch.queue.shift(); next !== undefined; next = batch.queue.shift()) {
          const { key, sent } = next;
          const now = peek();
          // The kept prayer no longer opens with the words (edited, revised, an Undo): the note's ask no longer holds.
          if (openingWords(now.liturgy.cards[batch.first].text).join(" ").toLowerCase() !== batch.words.toLowerCase()) {
            stop([key]);
            break;
          }
          const verdict = reviseVerdict(now, key, sent);
          // Switched off before its turn (in another tab; here its switch cancels it): skipped silently, never sent.
          const off = !now.liturgy.cards[key].enabled;
          if (!off && verdict === "apply") {
            const ask = acrossNote(batch.words, batch.firstLabel, batch.openings);
            const started = startReviseRef.current?.(key, [ask], (end) => {
              if (!batches.current.has(batch)) return;
              if (end.text === null) batch.all = false;
              else {
                const opening = openingWords(end.text).join(" ");
                const seen = [batch.words, ...batch.openings].some((w) => w.toLowerCase() === opening.toLowerCase());
                if (opening !== "" && !seen) batch.openings.push(opening);
              }
              // A 429: the rest are not sent (the wait shows on that card and beside the button).
              if (end.limited) stop();
              step();
            });
            if (started === true) {
              batch.started += 1;
              return;
            }
            // Refused (a 429's wait began meanwhile, or the AI is writing it): the rest are not sent, as after a 429.
            if (started === "limited") {
              const until = rateLimitedRef.current ?? Date.now();
              const seconds = Math.max(1, Math.ceil((until - Date.now()) / 1000));
              const failure: ReviseError = { code: "rate_limited", message: rateLimitMessage(seconds), retryable: true, retryAfterSeconds: seconds, retryAt: until };
              setReviseErrors((current) => ({ ...current, [key]: failure }));
            }
            stop([key]);
            break;
          } else if (!off && verdict !== "apply") reviseToast(key, verdict);
          batch.all = false;
          setRevising((current) => without(current, key));
        }
        batches.current.delete(batch);
        if (!batch.all || acrossTargets(peek(), batch.words, defaultBenediction) !== null) return;
        // Every one was revised: the note goes, unless a newer review has replaced it meanwhile.
        setReview((current) =>
          current !== null && current.generation === batch.generation && current.service.some((n) => n.id === batch.noteId)
            ? dismissNote(current, "service", batch.noteId)
            : current,
        );
      };
      step();
    },
    [defaultBenediction, peek],
  );

  const reviseAcross = useCallback(
    (noteId: string) => {
      const current = reviewRef.current;
      const note = current?.service.find((n) => n.id === noteId);
      const words = note === undefined ? null : sharedOpening(note);
      if (current === null || note === undefined || words === null) return false;
      const asked = peek();
      const targets = acrossTargets(asked, words, defaultBenediction);
      if (targets === null) return false;
      // Any of these prayers being written, revised or waiting in a batch: nothing is sent (the button is off).
      const busy = (key: SectionKey) => runs[key] !== undefined || revisions.current.has(key) || inBatch(batches.current, key);
      if ([targets.first, ...targets.others].some(busy)) return false;
      if (rateLimitedUntil !== null && Date.now() < rateLimitedUntil) return false;
      const batch: AcrossBatch = {
        noteId: note.id,
        generation: current.generation,
        words,
        first: targets.first,
        firstLabel: SECTION_LABELS[targets.first],
        queue: targets.others.map((key) => {
          const card = asked.liturgy.cards[key];
          return { key, sent: { createdAt: asked.created_at, text: card.text, origin: card.origin } };
        }),
        openings: [],
        started: 0,
        all: true,
      };
      batches.current.add(batch);
      // Every one shows as revising, with its own Cancel, from the start.
      setRevising((now) => {
        const next = { ...now };
        for (const key of targets.others) next[key] = true;
        return next;
      });
      runAcross(batch);
      return batch.started > 0;
    },
    [defaultBenediction, peek, rateLimitedUntil, runAcross, runs],
  );

  const cancelRevise = useCallback((key: SectionKey) => {
    // Not sent yet: it leaves its batch. Running: its batch moves on to the next.
    leaveBatch(batches.current, key);
    revisions.current.get(key)?.abort();
    revisions.current.delete(key);
    setRevising((current) => without(current, key));
  }, []);

  const value = useMemo<LiturgyReview>(
    () => ({ review, running, error, announcement, start, cancel, dismiss, revising, reviseErrors, revise, reviseAcross, cancelRevise }),
    [review, running, error, announcement, start, cancel, dismiss, revising, reviseErrors, revise, reviseAcross, cancelRevise],
  );
  return <ReviewContext value={value}>{children}</ReviewContext>;
}

/** The review state and actions. Throws outside `LiturgyReviewProvider` (the builder shell mounts it). */
export function useLiturgyReview(): LiturgyReview {
  const value = useContext(ReviewContext);
  if (!value) throw new Error("useLiturgyReview() must be used inside <LiturgyReviewProvider>.");
  return value;
}

"use client";

/**
 * `PewsProvider` and `usePews()` (pew voices spec 2026-10-20, "The liturgy
 * step"). Mounted in the builder shell inside the review provider, so an
 * answer keeps coming while the member moves between steps; leaving
 * `/builder`, switching church or signing out unmounts it and cancels it.
 *
 * - The panel lives here, in memory only (`pews.ts`).
 * - `start()`: the same cards as "Review service" (`reviewTargets`), captured
 *   when pressed, with the same resolved sermon text, in one
 *   `POST /liturgy/pews` (100 s). After the sermon text loads, a card changed
 *   meanwhile is left out and a new service sends nothing (4b's pre-send
 *   check). The answer replaces the last (`applyPews`: stale reactions
 *   dropped). One request at a time: a second `start()` while one runs does
 *   nothing.
 * - `cancel()` aborts the wait and keeps the panel already shown. A failure
 *   keeps it too and shows its message in `error` (a 429 in the server's own
 *   words; a 404, from a server not yet deployed, as `PEWS_UNAVAILABLE`); a
 *   401 or a lost church goes to the app's handling. A 429 with its wait
 *   starts a wait (`limitedUntil`): nothing is sent and the button is off
 *   until it ends, when its alert goes too (as Generate's and Revise's waits).
 * - Every draft change drops reactions whose prayer's text changed
 *   (`prunePews`); a new service cancels the request and drops the panel.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { ApiError } from "@/lib/api/client";
import { isNoChurchAccess } from "@/lib/api/errors";
import type { ChurchProfile } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import { reportAuthErrors, useApi } from "@/lib/queries/client";
import { hearFromThePews } from "@/lib/queries/liturgy";

import { cardErrorFrom } from "./errors";
import { captureReview } from "./notes";
import { applyPews, dismissReaction, PEWS_UNAVAILABLE, pewsDoneMessage, prunePews, type PewsPanel } from "./pews";
import { buildReviewRequest, reviewTargets } from "./request";
import { useSermonLoader } from "./sermon";

export type Pews = {
  panel: PewsPanel | null;
  running: boolean;
  error: string | null;
  /** A 429's wait (ms since the epoch): until then "Hear it from the pews" is off and its alert shows the wait. */
  limitedUntil: number | null;
  announcement: string;
  start: () => void;
  cancel: () => void;
  dismiss: (id: string) => void;
};

const PewsContext = createContext<Pews | null>(null);

export function PewsProvider({
  church,
  sermonWaitMs,
  children,
}: {
  church: Pick<ChurchProfile, "id" | "effective_translation">;
  sermonWaitMs?: number;
  children: ReactNode;
}) {
  const { draft, peek, defaultBenediction } = useDraft();
  const api = useApi();
  const loadSermon = useSermonLoader(church, sermonWaitMs);
  const [panel, setPanel] = useState<PewsPanel | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [limitedUntil, setLimitedUntil] = useState<number | null>(null);
  const limitedRef = useRef<number | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const active = useRef<AbortController | null>(null);
  const mounted = useRef(true);
  const answers = useRef(0);
  const service = useRef(draft.created_at);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      active.current?.abort();
    };
  }, []);

  // Every draft change, during render: a reaction whose prayer changed goes at once.
  const [pruned, setPruned] = useState(draft);
  if (pruned !== draft) {
    setPruned(draft);
    setPanel((current) => prunePews(current, draft));
  }

  // A 429's wait: when it ends, the button comes back and the wait's alert goes. A new service does not end it
  // (the bucket is the member's, as Generate's wait).
  useEffect(() => {
    if (limitedUntil === null) return;
    const timer = setTimeout(() => {
      limitedRef.current = null;
      setLimitedUntil(null);
      setError(null);
    }, Math.max(limitedUntil - Date.now(), 0));
    return () => clearTimeout(timer);
  }, [limitedUntil]);

  const createdAt = draft.created_at;
  useEffect(() => {
    if (service.current === createdAt) return;
    service.current = createdAt;
    active.current?.abort();
    active.current = null;
    setRunning(false);
    setError(null);
    setPanel(null);
  }, [createdAt]);

  const start = useCallback(() => {
    if (active.current !== null) return;
    if (limitedRef.current !== null && Date.now() < limitedRef.current) return; // a 429's wait is not over
    const asked = peek();
    const keys = reviewTargets(asked, defaultBenediction);
    if (keys.length === 0) return;
    const ask = captureReview(asked, keys);
    const controller = new AbortController();
    active.current = controller;
    setRunning(true);
    setError(null);
    setAnnouncement("");
    void (async () => {
      try {
        const sermon = await loadSermon(controller.signal);
        if (controller.signal.aborted) return;
        const now = peek();
        const fresh = keys.filter((key) => {
          const was = ask.cards[key];
          const card = now.liturgy.cards[key];
          return was !== undefined && card.text === was.text && card.origin === was.origin;
        });
        if (now.created_at !== ask.createdAt || fresh.length === 0) return;
        const result = await hearFromThePews(api.church, buildReviewRequest(asked, fresh, sermon), controller.signal);
        if (!mounted.current || active.current !== controller) return;
        answers.current += 1;
        const next = applyPews(peek(), ask, result, `pews${answers.current}`);
        setPanel(next);
        if (next !== null) setAnnouncement(pewsDoneMessage(next.found));
      } catch (e) {
        if (!mounted.current || active.current !== controller) return;
        if (e instanceof ApiError && (e.status === 401 || isNoChurchAccess(e))) reportAuthErrors(e, church.id);
        // A 429 in the server's words ("Too many requests. Try again in 15 seconds."); a 404 in its own.
        if (e instanceof ApiError && e.status === 404) setError(PEWS_UNAVAILABLE);
        else setError(e instanceof ApiError && e.code === "rate_limited" ? e.message : (cardErrorFrom(e)?.message ?? null));
        // A 429 starts a wait: the button is off, and the alert stays, until it ends.
        if (e instanceof ApiError && e.code === "rate_limited" && e.retryAfterSeconds !== undefined) {
          const until = Date.now() + e.retryAfterSeconds * 1000;
          limitedRef.current = until;
          setLimitedUntil(until);
        }
      } finally {
        if (active.current === controller) {
          active.current = null;
          if (mounted.current) setRunning(false);
        }
      }
    })();
  }, [api, church.id, defaultBenediction, loadSermon, peek]);

  const cancel = useCallback(() => {
    active.current?.abort();
    active.current = null;
    setRunning(false);
  }, []);

  const dismiss = useCallback((id: string) => {
    setPanel((current) => (current === null ? null : dismissReaction(current, id)));
  }, []);

  const value = useMemo<Pews>(
    () => ({ panel, running, error, limitedUntil, announcement, start, cancel, dismiss }),
    [panel, running, error, limitedUntil, announcement, start, cancel, dismiss],
  );
  return <PewsContext value={value}>{children}</PewsContext>;
}

/** The panel's state and actions. Throws outside `PewsProvider` (the builder shell mounts it). */
export function usePews(): Pews {
  const value = useContext(PewsContext);
  if (!value) throw new Error("usePews() must be used inside <PewsProvider>.");
  return value;
}

"use client";

import { Fragment, useEffect } from "react";

import { ErrorState } from "@/components/app/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useChurch } from "@/lib/church-context";
import { useDraft } from "@/lib/draft/context";
import { useLiturgyGeneration } from "@/lib/liturgy/generation";
import { useChurchProfile } from "@/lib/queries/church";
import { useLiturgyConfig } from "@/lib/queries/liturgy";

import { OutlineLandmark } from "./outline-landmark";
import { SectionCard } from "./section-card";
import { SermonTitleField } from "./sermon-title-field";

/** The step's shape while `GET /liturgy/config` loads (S "Loading, error and empty states"). */
function LiturgySkeleton() {
  return (
    <div role="status" aria-label="Loading the liturgy" className="grid gap-4">
      <Skeleton className="h-16 w-full" />
      <Skeleton className="h-40 w-full" />
      <Skeleton className="h-40 w-full" />
      <Skeleton className="h-40 w-full" />
    </div>
  );
}

/**
 * Step 3, Liturgy (slice 4 spec, "User experience"): the sermon title, then
 * the order of worship from `GET /liturgy/config`'s outline, in the order the
 * Word files print it: a card for each section, muted landmark rows for the
 * hymns, readings, sermon and creed. It reads and writes only the draft (F
 * §4.6); the AI runs live in the builder shell's generation provider, and the
 * step's Undo lines go when it unmounts. On mount it scrolls to the card the
 * address names (`#card-…`, `#custom-…`).
 */
export function LiturgyStep() {
  const configQuery = useLiturgyConfig();
  const config = configQuery.data;
  const church = useChurch();
  const profile = useChurchProfile(church.id).data;
  const { draft } = useDraft();
  const { clearUndo } = useLiturgyGeneration();
  const loaded = config !== undefined;

  // "Just replaced" and "Cleared" lines disappear when the step unmounts (S "Section card").
  useEffect(() => () => clearUndo(), [clearUndo]);

  useEffect(() => {
    if (!loaded) return;
    let id = "";
    try {
      id = decodeURIComponent(window.location.hash.slice(1));
    } catch {
      return; // a malformed address ("#card-%E0") scrolls nowhere
    }
    if (id !== "") document.getElementById(id)?.scrollIntoView({ block: "start" });
  }, [loaded]);

  if (config === undefined) {
    // A failed background refetch keeps the config (TanStack Query v5), so only a first load that failed shows this.
    return configQuery.isError ? (
      <ErrorState
        title="Couldn't load the liturgy sections."
        error={configQuery.error}
        onRetry={() => void configQuery.refetch()}
        retrying={configQuery.isFetching}
      />
    ) : (
      <LiturgySkeleton />
    );
  }

  const sections = new Map(config.sections.map((spec) => [spec.key as string, spec]));
  const defaultBenediction = profile?.default_benediction ?? config.default_benediction_fallback;

  return (
    <div className="grid gap-6">
      <h2 className="text-lg font-semibold">Liturgy</h2>
      <SermonTitleField maxLength={config.limits.max_sermon_title} />
      <section aria-labelledby="order-of-worship" className="grid gap-3">
        <h3 id="order-of-worship" className="text-base font-medium">
          Order of worship
        </h3>
        <ol aria-labelledby="order-of-worship" className="grid gap-3">
          {config.outline.map((item) => {
            const spec = sections.get(item.key);
            return (
              <Fragment key={item.key}>
                {item.kind === "section" && spec ? (
                  <li>
                    <SectionCard
                      spec={spec}
                      assuranceResponse={config.assurance_response}
                      defaultBenediction={defaultBenediction}
                      maxLength={config.limits.max_section_text}
                    />
                  </li>
                ) : item.kind === "landmark" ? (
                  <li>
                    <OutlineLandmark item={item} draft={draft} />
                  </li>
                ) : null}
              </Fragment>
            );
          })}
        </ol>
      </section>
    </div>
  );
}

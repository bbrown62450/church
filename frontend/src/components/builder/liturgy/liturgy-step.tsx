"use client";

import { PlusIcon } from "lucide-react";
import { Fragment, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { ErrorState } from "@/components/app/error-state";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useChurch } from "@/lib/church-context";
import { useDraft } from "@/lib/draft/context";
import {
  addCustomElement,
  normalizePlacement,
  removeCustomElement,
  restoreCustomElement,
  type CustomElement,
} from "@/lib/liturgy/cards";
import { useLiturgyGeneration } from "@/lib/liturgy/generation";
import { useChurchProfile } from "@/lib/queries/church";
import { useLiturgyConfig } from "@/lib/queries/liturgy";

import { useUndoToasts } from "../hymns/use-undo-toasts";

import { AddCustomElementDialog } from "./add-custom-element-dialog";
import { AiBar } from "./ai-bar";
import { CommunionCard } from "./communion-card";
import { CustomElementCard } from "./custom-element-card";
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
 * hymns, readings, sermon and creed, the communion card after the Second
 * Hymn, and each custom element right after the item that owns its place (an
 * unknown place reads as the end), then "Add custom element" (at most 30;
 * Remove offers Undo in a toast that never outlives the step). It reads and
 * writes only the draft (F
 * §4.6); the AI runs live in the builder shell's generation provider, and the
 * step's Undo lines go when it unmounts. On mount it scrolls to the card the
 * address names (`#card-…`, `#custom-…`).
 */
export function LiturgyStep() {
  const configQuery = useLiturgyConfig();
  const config = configQuery.data;
  const church = useChurch();
  const profile = useChurchProfile(church.id).data;
  const { draft, update, peek } = useDraft();
  const { clearUndo } = useLiturgyGeneration();
  const showUndo = useUndoToasts();
  const [adding, setAdding] = useState(false);
  const scrollTo = useRef<string | null>(null);
  /** After Remove: the id of the heading that takes focus (the next card's), or null for the Add button. */
  const focusAfterRemove = useRef<string | null | undefined>(undefined);
  const addRef = useRef<HTMLButtonElement>(null);
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

  // After Add, the page scrolls to the new card once it has rendered.
  useEffect(() => {
    if (scrollTo.current === null) return;
    const element = document.getElementById(`custom-${scrollTo.current}`);
    if (element === null) return;
    scrollTo.current = null;
    element.scrollIntoView({ block: "center" });
  });

  // After Remove the element's card is gone: focus goes to the next card's heading, or the Add button.
  useEffect(() => {
    const target = focusAfterRemove.current;
    if (target === undefined) return;
    focusAfterRemove.current = undefined;
    (target === null ? addRef.current : document.getElementById(target))?.focus();
  });

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
  const customs = draft.liturgy.custom_elements;
  const maxCustom = config.limits.max_custom_elements;
  const full = customs.length >= maxCustom;

  function after(anchors: readonly string[]): CustomElement[] {
    return anchors.flatMap((anchor) => customs.filter((e) => normalizePlacement(e.insert_after) === anchor));
  }

  function add(element: Omit<CustomElement, "id">) {
    const id = crypto.randomUUID();
    update((d) => addCustomElement(d, element, id));
    scrollTo.current = id;
    setAdding(false);
  }

  function remove(element: CustomElement) {
    const found = removeCustomElement(draft, element.id);
    if (found === null) return;
    const headings = [...document.querySelectorAll<HTMLElement>("[data-card-heading]")];
    const at = headings.findIndex((h) => h.id === `custom-${element.id}-title`);
    focusAfterRemove.current = at >= 0 && at + 1 < headings.length ? headings[at + 1].id : null;
    update((d) => removeCustomElement(d, element.id)?.draft ?? d);
    const label = element.label.trim() === "" ? "Custom element" : element.label.trim();
    showUndo(`Removed “${label}”.`, () => {
      // Another element may have been added meanwhile: never past the limit.
      if (peek().liturgy.custom_elements.length >= maxCustom) {
        toast.message(`You can add up to ${maxCustom} custom elements.`);
        return;
      }
      update((d) => restoreCustomElement(d, found.element, found.index, maxCustom));
    });
  }

  return (
    <section aria-labelledby="liturgy-step-title" className="grid gap-6">
      <h2 id="liturgy-step-title" className="text-lg font-semibold">
        Liturgy
      </h2>
      <SermonTitleField maxLength={config.limits.max_sermon_title} />
      <AiBar aiAvailable={config.ai_available} />
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
                      aiAvailable={config.ai_available}
                    />
                  </li>
                ) : item.kind === "landmark" ? (
                  <li>
                    <OutlineLandmark item={item} draft={draft} />
                  </li>
                ) : item.kind === "communion" ? (
                  <li>
                    <CommunionCard communion={config.communion} />
                  </li>
                ) : null}
                {after(item.anchors_after).map((element) => (
                  <li key={element.id}>
                    <CustomElementCard
                      element={element}
                      placements={config.custom_placements}
                      limits={config.limits}
                      onRemove={() => remove(element)}
                    />
                  </li>
                ))}
              </Fragment>
            );
          })}
        </ol>
        <div className="grid gap-1.5">
          <div>
            <Button ref={addRef} variant="outline" size="touch" disabled={full} onClick={() => setAdding(true)}>
              <PlusIcon aria-hidden="true" data-icon="inline-start" />
              Add custom element
            </Button>
          </div>
          {full ? (
            <p className="text-sm text-muted-foreground">
              You can add up to {maxCustom} custom elements.
            </p>
          ) : null}
        </div>
      </section>
      <AddCustomElementDialog
        open={adding}
        onOpenChange={setAdding}
        placements={config.custom_placements}
        limits={config.limits}
        onAdd={add}
      />
    </section>
  );
}

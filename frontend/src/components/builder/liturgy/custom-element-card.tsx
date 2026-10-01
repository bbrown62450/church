"use client";

import { EllipsisIcon } from "lucide-react";
import { useRef } from "react";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type { LiturgyConfig } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import { normalizePlacement, updateCustomElement, type CustomElement } from "@/lib/liturgy/cards";
import { useAutosize } from "@/lib/use-autosize";

export type Placements = LiturgyConfig["custom_placements"];

/**
 * A custom element in its printed position (S UX "Custom elements"; BC-12):
 * a dashed card with the "Custom" chip and inline Label, Text and Place. A
 * blank label says the element will not be printed without one; ⋯ → Remove
 * takes it out (the step offers Undo). No AI Generate (F D17). The card's id
 * is `custom-{id}`.
 */
export function CustomElementCard({
  element,
  placements,
  limits,
  onRemove,
}: {
  element: CustomElement;
  placements: Placements;
  limits: LiturgyConfig["limits"];
  onRemove: () => void;
}) {
  const { update } = useDraft();
  const textRef = useRef<HTMLTextAreaElement>(null);
  useAutosize(textRef, element.text);
  const id = element.id;
  const name = element.label.trim() === "" ? "Custom element" : element.label.trim();
  const blank = element.label.trim() === "";
  const items = Object.fromEntries(placements.map((p) => [p.key, p.label]));
  const edit = (patch: Partial<Omit<CustomElement, "id">>) => update((d) => updateCustomElement(d, id, patch));

  return (
    <section
      id={`custom-${id}`}
      aria-labelledby={`custom-${id}-title`}
      className="grid scroll-mt-24 gap-3 rounded-lg border border-dashed p-4"
    >
      <div className="flex min-w-0 items-center gap-2">
        <h3
          id={`custom-${id}-title`}
          tabIndex={-1}
          data-card-heading=""
          className="min-w-0 flex-1 text-base font-medium wrap-anywhere outline-none"
        >
          {name}
        </h3>
        <Badge variant="outline">Custom</Badge>
        <DropdownMenu>
          <DropdownMenuTrigger
            aria-label={`More actions for ${name}`}
            className={`${buttonVariants({ variant: "ghost", size: "icon-lg" })} size-11 shrink-0 md:size-8`}
          >
            <EllipsisIcon aria-hidden="true" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-auto min-w-44">
            <DropdownMenuItem onClick={onRemove} className="min-h-11 md:min-h-8">
              Remove
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      <div className="grid gap-1.5">
        <Label htmlFor={`custom-${id}-label`}>Label</Label>
        <Input
          id={`custom-${id}-label`}
          value={element.label}
          maxLength={limits.max_custom_label}
          aria-invalid={blank ? true : undefined}
          aria-describedby={blank ? `custom-${id}-blank` : undefined}
          onChange={(event) => edit({ label: event.target.value })}
          className="h-11"
        />
        {blank ? (
          <p id={`custom-${id}-blank`} className="text-sm text-destructive">
            Add a label, or remove this element — it won&apos;t be printed without one.
          </p>
        ) : null}
      </div>
      <div className="grid gap-1.5">
        <Label htmlFor={`custom-${id}-text`}>Text</Label>
        <Textarea
          id={`custom-${id}-text`}
          ref={textRef}
          value={element.text}
          maxLength={limits.max_custom_text}
          className="max-h-[60vh] overflow-y-auto"
          onChange={(event) => edit({ text: event.target.value })}
        />
      </div>
      <div className="grid gap-1.5">
        <Label id={`custom-${id}-place`}>Place</Label>
        <Select
          value={normalizePlacement(element.insert_after)}
          items={items}
          onValueChange={(value) => {
            if (typeof value === "string") edit({ insert_after: value });
          }}
        >
          <SelectTrigger aria-labelledby={`custom-${id}-place`} className="h-11 w-full sm:w-80 data-[size=default]:h-11">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {placements.map((p) => (
              <SelectItem key={p.key} value={p.key}>
                {p.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </section>
  );
}

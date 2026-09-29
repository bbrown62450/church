"use client";

import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { ChurchProfile, Translations } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import { effectiveTranslation, setTranslation } from "@/lib/draft/readings";

/**
 * "Bible translation" (S UX item 6; "Other states": translations list
 * failed). The choice is stored only when it differs from the church's
 * translation. Until the list loads, or when it fails, the select is
 * disabled and shows the church's translation.
 */
export function TranslationSelect({
  church,
  translations,
}: {
  church: Pick<ChurchProfile, "effective_translation" | "effective_translation_label">;
  translations: Translations | undefined;
}) {
  const { draft, update } = useDraft();
  const current = effectiveTranslation(draft, church, translations);
  const items: Record<string, string> = translations
    ? Object.fromEntries(translations.items.map((item) => [item.id, item.label]))
    : { [church.effective_translation]: church.effective_translation_label };
  const label = items[current] ?? church.effective_translation_label;

  return (
    <div className="grid gap-2">
      <Label id="translation-label">Bible translation</Label>
      <Select
        value={current}
        items={items}
        disabled={!translations}
        onValueChange={(value) => {
          if (typeof value === "string") update((d) => setTranslation(d, value, church.effective_translation));
        }}
      >
        <SelectTrigger
          aria-labelledby="translation-label"
          aria-describedby="translation-help"
          className="h-11 w-full sm:w-80 data-[size=default]:h-11"
        >
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {Object.entries(items).map(([id, text]) => (
            <SelectItem key={id} value={id}>
              {text}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <p id="translation-help" className="text-sm text-muted-foreground">
        For the passage text shown here. The bulletin lists the references, not the verse text.
      </p>
      <p className="text-sm">Passage text shown in {label}.</p>
    </div>
  );
}

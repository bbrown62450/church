"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useDraft } from "@/lib/draft/context";
import { setSermonTitle } from "@/lib/liturgy/cards";

/** The field's id: the Sermon row in the order of worship focuses it. */
export const SERMON_TITLE_ID = "sermon-title";

/**
 * The sermon title (S UX "Sermon title"; BC-15): printed in the bulletin and
 * the pastor's copy, never sent to the AI; 300 characters at most.
 */
export function SermonTitleField({ maxLength }: { maxLength: number }) {
  const { draft, update } = useDraft();
  return (
    <div className="grid gap-2">
      <Label htmlFor={SERMON_TITLE_ID}>Sermon title</Label>
      <Input
        id={SERMON_TITLE_ID}
        value={draft.liturgy.sermon_title}
        placeholder="e.g. Living Water"
        maxLength={maxLength}
        aria-describedby="sermon-title-help"
        onChange={(event) => {
          const next = event.target.value;
          update((d) => setSermonTitle(d, next));
        }}
        className="h-11"
      />
      <p id="sermon-title-help" className="text-sm text-muted-foreground">
        Printed in the bulletin and the pastor&apos;s copy. If blank, both show “[Sermon title]”.
      </p>
    </div>
  );
}

"use client";

import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useDraft } from "@/lib/draft/context";
import { commitScriptureLines, editScriptureLines } from "@/lib/draft/readings";
// The limits live with the step status (`status.ts`), which counts a field with a message as not done.
import { MAX_LINE, MAX_READINGS } from "@/lib/draft/status";

/** The inline messages for the raw lines (S UX item 5); blank lines are allowed and not counted, and a line is measured trimmed. */
export function scriptureProblems(lines: readonly string[]): string[] {
  const problems: string[] = [];
  if (lines.filter((line) => line.trim() !== "").length > MAX_READINGS) problems.push("Up to 20 readings.");
  const long = lines.findIndex((line) => line.trim().length > MAX_LINE);
  if (long >= 0) problems.push(`Line ${long + 1} is too long (max 200 characters).`);
  return problems;
}

/**
 * Scripture readings (S UX item 5): one reference per line, raw lines kept
 * while typing. Leaving the field drops a bulletin pick that is no longer a
 * line (`commitScriptureLines`).
 */
export function ScriptureLinesField() {
  const { draft, update } = useDraft();
  const problems = scriptureProblems(draft.readings.scriptures);

  return (
    <div className="grid gap-2">
      <Label htmlFor="scriptures">Scripture readings</Label>
      <p id="scriptures-help" className="text-sm text-muted-foreground">
        One reference per line, for example Matthew 17:1-9. Filled from the lectionary; edit if needed.
      </p>
      <Textarea
        id="scriptures"
        rows={5}
        value={draft.readings.scriptures.join("\n")}
        placeholder="Matthew 17:1-9"
        aria-describedby={problems.length > 0 ? "scriptures-help scriptures-error" : "scriptures-help"}
        aria-invalid={problems.length > 0 ? true : undefined}
        onChange={(event) => {
          const raw = event.target.value;
          update((d) => editScriptureLines(d, raw));
        }}
        onBlur={() => update(commitScriptureLines)}
        className="min-h-32"
      />
      {problems.length > 0 ? (
        <div id="scriptures-error" className="grid gap-1 text-sm text-destructive">
          {problems.map((problem) => (
            <p key={problem}>{problem}</p>
          ))}
        </div>
      ) : null}
    </div>
  );
}

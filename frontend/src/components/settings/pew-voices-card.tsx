"use client";

import { useRef } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { MAX_VOICES, TOO_MANY_VOICES, type VoiceRow } from "@/lib/settings/prayers";
import { useAutosize } from "@/lib/use-autosize";

export const PEWS_INTRO =
  "When you tap Hear it from the pews on the Liturgy step, these voices react to the whole service. They are kinds of people, not real people. Turn on up to 6.";
export const NO_VOICES = "No voices yet.";
export const RESTORE_STARTERS = "Restore the starter voices";

/** The id of a voice's description box (a check or a refusal focuses it). */
export function voiceTextId(key: string): string {
  return `voice-text-${key}`;
}

/** The id of a voice's "On" checkbox. */
export function voiceOnId(key: string): string {
  return `voice-on-${key}`;
}

/**
 * A voice's description: a one-row box that grows with its text (up to 60 vh,
 * then it scrolls; `useAutosize` where the browser cannot size it itself), at
 * least 44 px tall on phones. Line breaks become spaces when saved.
 */
function VoiceText({
  id,
  value,
  label,
  error,
  onChange,
}: {
  id: string;
  value: string;
  label: string;
  error?: string;
  onChange: (value: string) => void;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);
  useAutosize(ref, value);
  return (
    <Textarea
      ref={ref}
      id={id}
      rows={1}
      value={value}
      aria-label={label}
      aria-invalid={error ? true : undefined}
      aria-describedby={error ? `${id}-error` : undefined}
      className="max-h-[60vh] min-h-11 min-w-0 flex-1 basis-48 resize-none overflow-y-auto [overflow-wrap:anywhere] md:min-h-9"
      onChange={(event) => onChange(event.target.value)}
    />
  );
}

/**
 * "From the pews" on Settings → Prayers (pew voices spec 2026-10-20), under
 * the voice profile, saved by the page's one Save. Admins get a row per voice
 * (an "On" checkbox, the description, Remove), "Add a voice" (off at 12) and
 * "Restore the starter voices" (the owner's five back in the form, saved only
 * by Save); members read each voice with "On" or "Off" and get no control. Each
 * description is a box that grows with its text (`VoiceText`). The checks'
 * messages show under the box they name, and "Turn on at most 6 voices."
 * under the heading. Descriptions are React text only and wrap at 375 px.
 */
export function PewVoicesCard({
  voices,
  admin,
  errors,
  listError,
  onChange,
  onAdd,
  onRemove,
  onRestore,
}: {
  voices: VoiceRow[];
  admin: boolean;
  errors?: Record<string, string>;
  listError?: string;
  onChange: (key: string, patch: Partial<VoiceRow>) => void;
  onAdd: () => void;
  onRemove: (key: string) => void;
  onRestore: () => void;
}) {
  return (
    <section aria-labelledby="pew-voices-title" className="grid min-w-0 gap-3">
      <div className="grid gap-1">
        <h3 id="pew-voices-title" className="text-base font-medium">
          From the pews
        </h3>
        <p className="text-sm text-muted-foreground">{PEWS_INTRO}</p>
        {listError ? (
          <p id="pew-voices-error" role="alert" className="text-sm text-destructive">
            {listError}
          </p>
        ) : null}
      </div>
      {voices.length === 0 ? <p className="text-sm text-muted-foreground">{NO_VOICES}</p> : null}
      {voices.length > 0 ? (
        <ol aria-labelledby="pew-voices-title" className="grid gap-2">
          {voices.map((voice, i) => {
            const n = i + 1;
            const error = errors?.[voice.key];
            if (!admin) {
              return (
                <li key={voice.key} className="flex min-w-0 items-start gap-2 rounded-lg border p-3">
                  <p className="min-w-0 flex-1 text-sm [overflow-wrap:anywhere]">{voice.description}</p>
                  <span className="shrink-0 text-sm text-muted-foreground">{voice.on ? "On" : "Off"}</span>
                </li>
              );
            }
            return (
              <li key={voice.key} className="grid min-w-0 gap-1 rounded-lg border p-3">
                <div className="flex min-w-0 flex-wrap items-start gap-2">
                  <label className="flex min-h-11 cursor-pointer items-center gap-2 md:min-h-9">
                    <input
                      id={voiceOnId(voice.key)}
                      type="checkbox"
                      className="size-5 shrink-0 accent-primary"
                      checked={voice.on}
                      aria-label={`Turn on voice ${n}`}
                      aria-describedby={listError ? "pew-voices-error" : undefined}
                      onChange={(event) => onChange(voice.key, { on: event.target.checked })}
                    />
                    <span className="text-sm">On</span>
                  </label>
                  <VoiceText
                    id={voiceTextId(voice.key)}
                    value={voice.description}
                    label={`Voice ${n}`}
                    error={error}
                    onChange={(description) => onChange(voice.key, { description })}
                  />
                  <Button type="button" variant="ghost" size="touch" className="md:h-9" aria-label={`Remove voice ${n}`} onClick={() => onRemove(voice.key)}>
                    Remove
                  </Button>
                </div>
                {error ? (
                  <p id={`${voiceTextId(voice.key)}-error`} role="alert" className="text-sm text-destructive">
                    {error}
                  </p>
                ) : null}
              </li>
            );
          })}
        </ol>
      ) : null}
      {admin ? (
        <div className="grid gap-1">
          <div className="flex min-w-0 flex-wrap gap-2">
            <Button
              id="add-voice"
              type="button"
              variant="outline"
              size="touch"
              className="w-full sm:w-fit"
              disabled={voices.length >= MAX_VOICES}
              onClick={onAdd}
            >
              Add a voice
            </Button>
            <Button type="button" variant="ghost" size="touch" className="w-full sm:w-fit" onClick={onRestore}>
              {RESTORE_STARTERS}
            </Button>
          </div>
          {voices.length >= MAX_VOICES ? <p className="text-sm text-muted-foreground">{TOO_MANY_VOICES}</p> : null}
        </div>
      ) : null}
    </section>
  );
}

/**
 * Settings → Liturgy prompts' form rules (slice 6a-3a; 6a spec "Pure helpers"
 * `prompts.ts`). The form holds one text per prompt; a prompt counts as the
 * church's own only when its text, read as the server reads it
 * (`clean_prompt_overrides`: CRLF as LF, trimmed), is not blank and differs
 * from its default. So a save sends exactly what the server would keep, and a
 * card cleared or set back to its default text goes back to the default.
 */
import { ApiError } from "@/lib/api/client";
import type { LiturgyPrompts, PromptField, PromptKey } from "@/lib/api/types";

import { rebaseForm } from "./profile";

export type PromptValues = Record<PromptKey, string>;
export type PromptErrors = Partial<Record<PromptKey, string>>;

/** Every prompt, in the server's order: the system prompt, then the sections (`liturgy_prompts.PROMPT_KEYS`). */
export const PROMPT_KEYS: readonly PromptKey[] = [
  "system",
  "call_to_worship",
  "opening_prayer",
  "prayer_of_confession",
  "assurance",
  "prayer_for_illumination",
  "prayers_of_the_people",
  "offertory_prayer",
  "benediction",
];

/** The longest prompt the server takes (`PUT`'s `max_length`). */
export const MAX_PROMPT_LENGTH = 8000;

/** A prompt's text as the server compares and stores it: CRLF line ends as LF, trimmed. */
export function cleanPrompt(text: string): string {
  return text.replace(/\r\n/g, "\n").trim();
}

/** The form a read starts at, and its baseline: the church's own wording, else the default. */
export function promptValuesFrom(out: LiturgyPrompts): PromptValues {
  return Object.fromEntries(out.fields.map((f) => [f.key, f.override ?? f.default])) as PromptValues;
}

/** True when this text would be stored as the church's own wording (the card's **Customized** badge). */
export function isCustomized(text: string, field: PromptField): boolean {
  const clean = cleanPrompt(text);
  return clean !== "" && clean !== cleanPrompt(field.default);
}

/** `PUT`'s `prompts`: every prompt whose cleaned text is the church's own, cleaned, in the server's order. */
export function promptsPayload(values: PromptValues, fields: readonly PromptField[]): Partial<PromptValues> {
  const payload: Partial<PromptValues> = {};
  for (const field of fields) {
    if (isCustomized(values[field.key], field)) payload[field.key] = cleanPrompt(values[field.key]);
  }
  return payload;
}

/** True while a save would change what is stored. */
export function hasPromptChanges(baseline: PromptValues, current: PromptValues, fields: readonly PromptField[]): boolean {
  return JSON.stringify(promptsPayload(baseline, fields)) !== JSON.stringify(promptsPayload(current, fields));
}

/**
 * 6a's rebase for the prompts: newer server wording replaces each card the
 * user has not edited (cleaned text still equal to the old baseline's) and
 * each edited card keeps the edit.
 */
export function rebasePrompts(oldBaseline: PromptValues, current: PromptValues, next: PromptValues): PromptValues {
  return rebaseForm(oldBaseline, current, next, (_key, a, b) => cleanPrompt(a) === cleanPrompt(b));
}

/** A failed save's messages for the cards (a 422's `fields` "prompts.<key>"), or null when it names none. */
export function promptFieldErrors(e: unknown, keys: readonly PromptKey[]): PromptErrors | null {
  if (!(e instanceof ApiError) || e.status !== 422 || !e.fields) return null;
  const found: PromptErrors = {};
  for (const key of keys) {
    const message = e.fields[`prompts.${key}`];
    if (message) found[key] = message;
  }
  return Object.keys(found).length > 0 ? found : null;
}

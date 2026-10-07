/**
 * Settings → Hymns' forms (slice 6a-2; 6a spec UX §2, "Pure helpers" `hymns.ts`).
 * The client checks what it can with the server's own words, so a mistake
 * shows at once; the server checks everything again (and tidies line breaks
 * into spaces). A member's form never sends the year or the familiarity.
 */
import type { Hymn, HymnBody, HymnPatch } from "@/lib/api/types";

export type HymnForm = {
  title: string;
  number: string;
  hymnal: string;
  scripture_refs: string;
  themes: string;
  link: string;
  text_year: string;
  hymnal_count: string;
};

export type HymnFieldErrors = Partial<Record<keyof HymnForm, string>>;

export const TITLE_REQUIRED = "Hymn title is required.";
export const NUMBER_INVALID = "Hymn number must be a whole number.";
export const LINK_INVALID = "Links must start with https://.";
export const COUNT_INVALID = "Number of hymnals must be a whole number from 0 to 100000.";

export function yearInvalid(thisYear: number): string {
  return `Year must be a whole number from 1 to ${thisYear}.`;
}

/** `text` as a whole number from `min` to `max`: blank is null, anything else out of reach "invalid". */
function parseWhole(text: string, min: number, max: number): number | null | "invalid" {
  const trimmed = text.trim();
  if (trimmed === "") return null;
  if (!/^\d{1,9}$/.test(trimmed)) return "invalid";
  const value = Number(trimmed);
  return value >= min && value <= max ? value : "invalid";
}

export function parseHymnNumber(text: string): number | null | "invalid" {
  return parseWhole(text, 1, 99999);
}

export function parseTextYear(text: string, thisYear: number): number | null | "invalid" {
  return parseWhole(text, 1, thisYear);
}

export function parseHymnalCount(text: string): number | null | "invalid" {
  return parseWhole(text, 0, 100000);
}

/** The add form, in `hymnal` (the church's default). */
export function emptyHymnForm(hymnal: string): HymnForm {
  return { title: "", number: "", hymnal, scripture_refs: "", themes: "", link: "", text_year: "", hymnal_count: "" };
}

/** The edit form a hymn starts at, and its baseline; Themes start at the parsed themes joined by ", ". */
export function hymnFormFrom(h: Hymn): HymnForm {
  const text = (n: number | null | undefined) => (n === null || n === undefined ? "" : String(n));
  return {
    title: h.title,
    number: text(h.number),
    hymnal: h.hymnal,
    scripture_refs: h.scripture_refs ?? "",
    themes: h.themes.join(", "),
    link: h.link ?? "",
    text_year: text(h.text_year),
    hymnal_count: text(h.hymnal_count),
  };
}

/** What the client can tell is wrong, in the form's order, with the server's messages. */
export function hymnFormErrors(form: HymnForm, { thisYear, admin }: { thisYear: number; admin: boolean }): HymnFieldErrors {
  const errors: HymnFieldErrors = {};
  if (form.title.trim() === "") errors.title = TITLE_REQUIRED;
  if (parseHymnNumber(form.number) === "invalid") errors.number = NUMBER_INVALID;
  const link = form.link.trim();
  if (link !== "" && !link.toLowerCase().startsWith("https://")) errors.link = LINK_INVALID;
  if (admin && parseTextYear(form.text_year, thisYear) === "invalid") errors.text_year = yearInvalid(thisYear);
  if (admin && parseHymnalCount(form.hymnal_count) === "invalid") errors.hymnal_count = COUNT_INVALID;
  return errors;
}

const blankToNull = (text: string): string | null => (text.trim() === "" ? null : text.trim());
const whole = (value: number | null | "invalid"): number | null => (value === "invalid" ? null : value);

/** `POST /hymns`'s body (check `hymnFormErrors` first). The year and familiarity only for an admin. */
export function newHymnBody(form: HymnForm, { thisYear, admin }: { thisYear: number; admin: boolean }): HymnBody {
  const body: HymnBody = {
    title: form.title.trim(),
    number: whole(parseHymnNumber(form.number)),
    hymnal: blankToNull(form.hymnal),
    scripture_refs: blankToNull(form.scripture_refs),
    theme: blankToNull(form.themes),
    link: blankToNull(form.link),
  };
  if (admin) {
    body.text_year = whole(parseTextYear(form.text_year, thisYear));
    body.hymnal_count = whole(parseHymnalCount(form.hymnal_count));
  }
  return body;
}

/**
 * `PATCH /hymns/{id}`'s body: each field whose value changed (text trimmed,
 * numbers compared as numbers); a cleared field is null. The year and
 * familiarity only for an admin, so a member's edit never sends them.
 */
export function hymnPatch(baseline: HymnForm, form: HymnForm, { thisYear, admin }: { thisYear: number; admin: boolean }): HymnPatch {
  const patch: HymnPatch = {};
  if (form.title.trim() !== baseline.title.trim()) patch.title = form.title.trim();
  const number = whole(parseHymnNumber(form.number));
  if (number !== whole(parseHymnNumber(baseline.number))) patch.number = number;
  if (form.hymnal !== baseline.hymnal) patch.hymnal = form.hymnal;
  if (form.scripture_refs.trim() !== baseline.scripture_refs.trim()) patch.scripture_refs = blankToNull(form.scripture_refs);
  if (form.themes.trim() !== baseline.themes.trim()) patch.theme = blankToNull(form.themes);
  if (form.link.trim() !== baseline.link.trim()) patch.link = blankToNull(form.link);
  if (admin) {
    const year = whole(parseTextYear(form.text_year, thisYear));
    if (year !== whole(parseTextYear(baseline.text_year, thisYear))) patch.text_year = year;
    const count = whole(parseHymnalCount(form.hymnal_count));
    if (count !== whole(parseHymnalCount(baseline.hymnal_count))) patch.hymnal_count = count;
  }
  return patch;
}

/** A hymn as the library lists it: "#403 Come, Thou Almighty King", or the title alone with no number. */
export function hymnLabel(h: Pick<Hymn, "number" | "title">): string {
  return h.number === null || h.number === undefined ? h.title : `#${h.number} ${h.title}`;
}

/** The library's count line: "853 hymns", "1 hymn", or "12 matching hymns" while searching or filtered. */
export function countLine(total: number, filtered: boolean): string {
  const noun = total === 1 ? "hymn" : "hymns";
  return filtered ? `${total} matching ${noun}` : `${total} ${noun}`;
}

/** "{n} hymns" / "1 hymn". */
export function hymnCount(n: number): string {
  return `${n} ${n === 1 ? "hymn" : "hymns"}`;
}

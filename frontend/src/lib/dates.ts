/**
 * Date-only values (F §4.10; S "lib/dates.ts"). A service date is a
 * `YYYY-MM-DD` string, and every helper here works on its calendar fields.
 * Nothing in `src/` may call `new Date("YYYY-MM-DD")` (it parses as UTC
 * midnight, the previous evening in US time zones); `dates.guard.test.ts`
 * scans for it. This file does its arithmetic on UTC calendar days.
 */

export type CalendarDate = { y: number; m: number; d: number };

const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
] as const;

const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"] as const;

function daysInMonth(y: number, m: number): number {
  if (m === 2) return (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0 ? 29 : 28;
  return [4, 6, 9, 11].includes(m) ? 30 : 31;
}

/** The calendar fields of a real `YYYY-MM-DD` date, or null ("2026-02-30", "2026-9-4" and "" are null). */
export function parseIsoDate(s: string): CalendarDate | null {
  const match = ISO_DATE.exec(s);
  if (!match) return null;
  const [y, m, d] = [Number(match[1]), Number(match[2]), Number(match[3])];
  if (m < 1 || m > 12 || d < 1 || d > daysInMonth(y, m)) return null;
  return { y, m, d };
}

export function isValidDateIso(s: string): boolean {
  return parseIsoDate(s) !== null;
}

function pad(n: number, width: number): string {
  return String(n).padStart(width, "0");
}

function toIso({ y, m, d }: CalendarDate): string {
  return `${pad(y, 4)}-${pad(m, 2)}-${pad(d, 2)}`;
}

/** A UTC midnight for the calendar day; setUTCFullYear keeps years below 100 as written. */
function utcDay({ y, m, d }: CalendarDate): Date {
  const t = new Date(0);
  t.setUTCFullYear(y, m - 1, d);
  return t;
}

function fromUtcDay(t: Date): CalendarDate {
  return { y: t.getUTCFullYear(), m: t.getUTCMonth() + 1, d: t.getUTCDate() };
}

function mustParse(iso: string): CalendarDate {
  const parsed = parseIsoDate(iso);
  if (!parsed) throw new RangeError(`Not a YYYY-MM-DD date: ${JSON.stringify(iso)}`);
  return parsed;
}

/** `iso` moved by `n` calendar days (negative goes back). Throws on an invalid date. */
export function addDays(iso: string, n: number): string {
  const t = utcDay(mustParse(iso));
  t.setUTCDate(t.getUTCDate() + n);
  return toIso(fromUtcDay(t));
}

/** 0 = Sunday … 6 = Saturday. Throws on an invalid date. */
export function weekday(iso: string): number {
  return utcDay(mustParse(iso)).getUTCDay();
}

export function isSunday(iso: string): boolean {
  return isValidDateIso(iso) && weekday(iso) === 0;
}

/** "October 4, 2026"; "" for an invalid date. */
export function formatServiceDate(iso: string): string {
  const p = parseIsoDate(iso);
  return p ? `${MONTHS[p.m - 1]} ${p.d}, ${p.y}` : "";
}

/** "Sunday, October 4, 2026"; "" for an invalid date. */
export function formatLongDate(iso: string): string {
  return isValidDateIso(iso) ? `${WEEKDAYS[weekday(iso)]}, ${formatServiceDate(iso)}` : "";
}

/** "October 4"; "" for an invalid date. */
export function formatShortDate(iso: string): string {
  const p = parseIsoDate(iso);
  return p ? `${MONTHS[p.m - 1]} ${p.d}` : "";
}

function formatterFor(tz: string | null | undefined): Intl.DateTimeFormat {
  const options: Intl.DateTimeFormatOptions = { year: "numeric", month: "2-digit", day: "2-digit" };
  if (tz) {
    try {
      return new Intl.DateTimeFormat("en-CA", { ...options, timeZone: tz });
    } catch {
      // An unknown zone (RangeError): fall back to the browser's own zone (F §4.10).
    }
  }
  return new Intl.DateTimeFormat("en-CA", options);
}

/**
 * Today's date in `tz` as `YYYY-MM-DD`. A missing, empty or unknown zone falls
 * back to the browser's zone; callers pass `undefined` when the church
 * profile says `timezone_valid: false`.
 */
export function todayIn(tz: string | null | undefined, now: Date = new Date()): string {
  const parts = formatterFor(tz).formatToParts(now);
  const field = (type: Intl.DateTimeFormatPartTypes) => Number(parts.find((p) => p.type === type)?.value);
  return toIso({ y: field("year"), m: field("month"), d: field("day") });
}

/** The first Sunday strictly after `iso` (a Sunday gives the following Sunday). */
export function nextSunday(iso: string): string {
  return addDays(iso, 7 - weekday(iso));
}

/** A Sunday in the first seven days of its month (the communion default). */
export function isFirstSundayOfMonth(iso: string): boolean {
  const p = parseIsoDate(iso);
  return p !== null && weekday(iso) === 0 && p.d <= 7;
}

/** Years 1900–2199: the range the lectionary lookup accepts. */
export function inSupportedRange(iso: string): boolean {
  const p = parseIsoDate(iso);
  return p !== null && p.y >= 1900 && p.y <= 2199;
}

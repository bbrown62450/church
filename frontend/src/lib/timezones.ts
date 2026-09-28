/**
 * Time zones for the church form (S "Storage and URL helpers"; F §7.4 "Church timezone").
 * The list is the browser's own `Intl.supportedValuesOf("timeZone")` (ICU's canonical ids,
 * e.g. `Asia/Calcutta`; no `UTC` or `Etc/*`, 1b clarification 43). The server's
 * `timezones.is_valid_timezone` accepts every one of them. Without the list, the combobox
 * falls back to a plain text input.
 */

/** The default when the browser's zone is unknown or not in the list (S Flow A). */
export const FALLBACK_TIMEZONE = "America/New_York";

/** Every zone id the browser knows, or null when it cannot list them. */
export function listTimezones(): string[] | null {
  if (typeof Intl.supportedValuesOf !== "function") return null;
  try {
    const zones = Intl.supportedValuesOf("timeZone");
    return zones.length > 0 ? zones : null;
  } catch {
    return null;
  }
}

/** The browser's own zone id, or null when it reports none. */
export function browserTimezone(): string | null {
  try {
    const zone = new Intl.DateTimeFormat().resolvedOptions().timeZone;
    return typeof zone === "string" && zone !== "" ? zone : null;
  } catch {
    return null;
  }
}

/** The browser's zone when `list` has it, else `America/New_York` (also when there is no list). */
export function defaultTimezone(list: string[] | null): string {
  const zone = browserTimezone();
  return list !== null && zone !== null && list.includes(zone) ? zone : FALLBACK_TIMEZONE;
}

/** What the combobox shows for a zone: its id with `_` as a space (`America/New York`). */
export function timezoneLabel(id: string): string {
  return id.replaceAll("_", " ");
}

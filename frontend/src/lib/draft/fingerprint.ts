/**
 * The fingerprint behind unsaved-changes detection (F §4.6 "Unsaved changes";
 * S "fingerprint.ts"): 32-bit FNV-1a over the UTF-8 bytes of a stable JSON
 * string (object keys sorted at every level), as 8 hex digits. `isDirty`,
 * which compares it, is in `status.ts` (slice 5a-3), beside the Review
 * statuses that read it.
 */

function stable(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(stable);
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, stable((value as Record<string, unknown>)[key])]),
    );
  }
  return value;
}

/** JSON with every object's keys sorted, so key order never changes the fingerprint. */
export function stableStringify(value: unknown): string {
  return JSON.stringify(stable(value));
}

const utf8 = new TextEncoder();

/** 32-bit FNV-1a of the UTF-8 bytes, as 8 hex digits (standard FNV-1a, so any language can match it). */
export function fnv1a32(text: string): string {
  let hash = 0x811c9dc5;
  for (const byte of utf8.encode(text)) {
    hash ^= byte;
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

export function fingerprint(payload: unknown): string {
  return fnv1a32(stableStringify(payload));
}

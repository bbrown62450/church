"use client";

/**
 * Textareas grow with their content up to 60 vh, then scroll (slice 4 spec,
 * UX "Layout"). The kit's `Textarea` already sizes itself to its content with
 * `field-sizing: content` where the browser supports it; this hook does the
 * same for a browser that does not (older iOS Safari), by setting the height
 * from `scrollHeight` whenever the value changes. The caller caps the field
 * with `max-h-[60vh]` so it scrolls past that.
 */
import { useLayoutEffect, type RefObject } from "react";

/** The share of the window a field may grow to. */
export const AUTOSIZE_MAX_SHARE = 0.6;

function sizesItself(): boolean {
  return typeof CSS !== "undefined" && typeof CSS.supports === "function" && CSS.supports("field-sizing", "content");
}

/** `shown`: false while the field is not rendered (a card switched off), so it is sized again when it comes back. */
export function useAutosize(ref: RefObject<HTMLTextAreaElement | null>, value: string, shown = true): void {
  useLayoutEffect(() => {
    const field = ref.current;
    if (field === null || sizesItself()) return;
    field.style.height = "auto";
    // scrollHeight leaves out the 1 px borders.
    const height = Math.min(field.scrollHeight + 2, Math.round(window.innerHeight * AUTOSIZE_MAX_SHARE));
    field.style.height = `${height}px`;
  }, [ref, value, shown]);
}

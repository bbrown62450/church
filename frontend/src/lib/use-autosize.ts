"use client";

/**
 * Textareas grow with their content up to 60 vh, then scroll (slice 4 spec,
 * UX "Layout"). The kit's `Textarea` already sizes itself to its content with
 * `field-sizing: content` where the browser supports it; this hook does the
 * same for a browser that does not (older iOS Safari), by setting the height
 * from `scrollHeight` whenever the value changes, and again when the window
 * is resized or the field's width changes (`ResizeObserver` where there is
 * one), since the text wraps to another height and the cap is 60% of the new
 * window. The caller caps the field with `max-h-[60vh]` so it scrolls past that.
 */
import { useEffect, useLayoutEffect, type RefObject } from "react";

/** The share of the window a field may grow to. */
export const AUTOSIZE_MAX_SHARE = 0.6;

function sizesItself(): boolean {
  return typeof CSS !== "undefined" && typeof CSS.supports === "function" && CSS.supports("field-sizing", "content");
}

function fit(field: HTMLTextAreaElement): void {
  field.style.height = "auto";
  // scrollHeight leaves out the 1 px borders.
  const height = Math.min(field.scrollHeight + 2, Math.round(window.innerHeight * AUTOSIZE_MAX_SHARE));
  field.style.height = `${height}px`;
}

/** `shown`: false while the field is not rendered (a card switched off), so it is sized again when it comes back. */
export function useAutosize(ref: RefObject<HTMLTextAreaElement | null>, value: string, shown = true): void {
  useLayoutEffect(() => {
    const field = ref.current;
    if (field === null || sizesItself()) return;
    fit(field);
  }, [ref, value, shown]);

  useEffect(() => {
    const field = ref.current;
    if (field === null || sizesItself()) return;
    const refit = () => fit(field);
    window.addEventListener("resize", refit);
    // Only a width change re-wraps the text; the height this hook sets must not trigger it again.
    let width = field.clientWidth;
    const observer =
      typeof ResizeObserver === "undefined"
        ? null
        : new ResizeObserver(() => {
            if (field.clientWidth === width) return;
            width = field.clientWidth;
            refit();
          });
    observer?.observe(field);
    return () => {
      window.removeEventListener("resize", refit);
      observer?.disconnect();
    };
  }, [ref, shown]);
}

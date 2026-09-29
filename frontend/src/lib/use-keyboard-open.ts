"use client";

/**
 * True while a text input, a textarea or an editable element has focus (S
 * "Builder shell": below `md` the step footer hides then, so the iOS keyboard
 * does not stack on it). Focus-based, because the visual viewport is not
 * reliable across mobile browsers. Slice 4 reuses it for the liturgy cards.
 */
import { useSyncExternalStore } from "react";

/** Input types that open a picker or no keyboard at all. */
const NO_KEYBOARD = new Set([
  "button", "checkbox", "color", "date", "datetime-local", "file", "hidden", "image",
  "month", "radio", "range", "reset", "submit", "time", "week",
]);

export function isTextEntry(element: Element | null): boolean {
  if (element instanceof HTMLTextAreaElement) return !element.readOnly;
  if (element instanceof HTMLInputElement) return !element.readOnly && !NO_KEYBOARD.has(element.type);
  return element instanceof HTMLElement && element.isContentEditable;
}

function subscribe(onChange: () => void): () => void {
  document.addEventListener("focusin", onChange);
  document.addEventListener("focusout", onChange);
  return () => {
    document.removeEventListener("focusin", onChange);
    document.removeEventListener("focusout", onChange);
  };
}

export function useKeyboardOpen(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => isTextEntry(document.activeElement),
    () => false,
  );
}

/**
 * `useAutosize` (slice 4 spec, UX "Layout": textareas grow with their content
 * up to 60 vh, then scroll): where the browser sizes a field to its content
 * itself (`field-sizing: content`) the hook does nothing; elsewhere it sets
 * the height from the content, capped at 60% of the window, and again when
 * the field comes back (a card switched on), the window is resized or the
 * field's width changes.
 */
import { act, render, screen } from "@testing-library/react";
import { useRef } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useAutosize } from "./use-autosize";

function Field({ value }: { value: string }) {
  const ref = useRef<HTMLTextAreaElement>(null);
  useAutosize(ref, value);
  return <textarea ref={ref} aria-label="Text" value={value} readOnly />;
}

/** A card's field, rendered only while the card is on. */
function Toggled({ on, value }: { on: boolean; value: string }) {
  const ref = useRef<HTMLTextAreaElement>(null);
  useAutosize(ref, value, on);
  return on ? <textarea ref={ref} aria-label="Text" value={value} readOnly /> : null;
}

function withScrollHeight(px: number) {
  vi.spyOn(HTMLElement.prototype, "scrollHeight", "get").mockReturnValue(px);
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("useAutosize (S Layout)", () => {
  it("grows the field to its content and stops at 60% of the window, where the browser cannot", () => {
    vi.stubGlobal("CSS", { supports: () => false });
    vi.spyOn(window, "innerHeight", "get").mockReturnValue(1000);
    withScrollHeight(240);
    const view = render(<Field value="Leader: Come!" />);
    expect(screen.getByRole("textbox", { name: "Text" }).style.height).toBe("242px");
    withScrollHeight(900);
    view.rerender(<Field value={"Leader: Come!\n".repeat(40)} />);
    expect(screen.getByRole("textbox", { name: "Text" }).style.height).toBe("600px");
  });

  it("sizes the field again when it comes back with the same text", () => {
    vi.stubGlobal("CSS", { supports: () => false });
    vi.spyOn(window, "innerHeight", "get").mockReturnValue(1000);
    withScrollHeight(240);
    const view = render(<Toggled on value="Leader: Come!" />);
    view.rerender(<Toggled on={false} value="Leader: Come!" />);
    expect(screen.queryByRole("textbox")).toBeNull();
    view.rerender(<Toggled on value="Leader: Come!" />);
    expect(screen.getByRole("textbox", { name: "Text" }).style.height).toBe("242px");
  });

  it("sizes the field again when the window is resized or the field's width changes", () => {
    vi.stubGlobal("CSS", { supports: () => false });
    const observers: { callback: () => void; target?: Element; disconnected: boolean }[] = [];
    vi.stubGlobal(
      "ResizeObserver",
      class {
        entry: (typeof observers)[number];
        constructor(callback: () => void) {
          this.entry = { callback, disconnected: false };
          observers.push(this.entry);
        }
        observe(target: Element) {
          this.entry.target = target;
        }
        disconnect() {
          this.entry.disconnected = true;
        }
      },
    );
    const innerHeight = vi.spyOn(window, "innerHeight", "get").mockReturnValue(1000);
    withScrollHeight(900);
    const view = render(<Field value="Leader: Come!" />);
    const field = screen.getByRole("textbox", { name: "Text" });
    expect(field.style.height).toBe("600px");
    // A phone turned sideways: the cap is 60% of the new window.
    innerHeight.mockReturnValue(500);
    act(() => {
      window.dispatchEvent(new Event("resize"));
    });
    expect(field.style.height).toBe("300px");
    // The column narrows, so the text wraps taller.
    innerHeight.mockReturnValue(1000);
    withScrollHeight(400);
    const width = vi.spyOn(field, "clientWidth", "get").mockReturnValue(200);
    expect(observers[0].target).toBe(field);
    act(() => observers[0].callback());
    expect(field.style.height).toBe("402px");
    // The height it set does not trigger it again: only a width change does.
    withScrollHeight(100);
    act(() => observers[0].callback());
    expect(field.style.height).toBe("402px");
    width.mockReturnValue(300);
    act(() => observers[0].callback());
    expect(field.style.height).toBe("102px");
    view.unmount();
    expect(observers[0].disconnected).toBe(true);
  });

  it("leaves the height to the browser when it sizes fields to their content", () => {
    vi.stubGlobal("CSS", { supports: (property: string, value: string) => property === "field-sizing" && value === "content" });
    withScrollHeight(240);
    render(<Field value="Leader: Come!" />);
    expect(screen.getByRole("textbox", { name: "Text" }).style.height).toBe("");
  });
});

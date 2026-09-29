import { act, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useKeyboardOpen } from "./use-keyboard-open";

function Probe() {
  const open = useKeyboardOpen();
  return (
    <div>
      <p>Keyboard: {open ? "open" : "closed"}</p>
      <label>
        Occasion <input type="text" />
      </label>
      <label>
        Readings <textarea />
      </label>
      <label>
        Service date <input type="date" />
      </label>
      <button type="button">Next</button>
    </div>
  );
}

describe("useKeyboardOpen (S Builder shell)", () => {
  it("is open while a text input or textarea has focus, and closed for buttons, pickers and no focus", () => {
    render(<Probe />);
    const state = () => screen.getByText(/^Keyboard:/).textContent;
    expect(state()).toBe("Keyboard: closed");

    act(() => screen.getByRole("textbox", { name: "Occasion" }).focus());
    expect(state()).toBe("Keyboard: open");
    act(() => screen.getByRole("textbox", { name: "Readings" }).focus());
    expect(state()).toBe("Keyboard: open");
    act(() => screen.getByLabelText("Service date").focus());
    expect(state()).toBe("Keyboard: closed");
    act(() => screen.getByRole("textbox", { name: "Occasion" }).focus());
    act(() => screen.getByRole("button", { name: "Next" }).focus());
    expect(state()).toBe("Keyboard: closed");
    act(() => screen.getByRole("textbox", { name: "Readings" }).focus());
    act(() => (document.activeElement as HTMLElement).blur());
    expect(state()).toBe("Keyboard: closed");
  });
});

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { PendingButton } from "./pending-button";

describe("PendingButton", () => {
  it("is disabled and says Saving… while pending", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    const { rerender } = render(
      <PendingButton pending onClick={onClick}>
        Save changes
      </PendingButton>,
    );

    const button = screen.getByRole("button", { name: "Saving…" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    expect(screen.queryByText("Save changes")).not.toBeInTheDocument();
    await user.click(button);
    expect(onClick).not.toHaveBeenCalled();

    rerender(
      <PendingButton pending pendingLabel="Creating church…">
        Create church
      </PendingButton>,
    );
    expect(screen.getByRole("button", { name: "Creating church…" })).toBeDisabled();
  });

  it("shows its label and passes Button props through when not pending", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(
      <PendingButton pending={false} type="submit" size="touch" onClick={onClick}>
        Save changes
      </PendingButton>,
    );

    const button = screen.getByRole("button", { name: "Save changes" });
    expect(button).toBeEnabled();
    expect(button).not.toHaveAttribute("aria-busy");
    expect(button).toHaveAttribute("type", "submit");
    expect(button).toHaveClass("h-11");
    await user.click(button);
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});

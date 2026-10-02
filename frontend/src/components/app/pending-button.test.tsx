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
    expect(button).toHaveAttribute("aria-disabled", "true");
    expect(button).toHaveClass("opacity-50");
    expect(button).toHaveAttribute("aria-busy", "true");
    expect(screen.queryByText("Save changes")).not.toBeInTheDocument();
    await user.click(button);
    expect(onClick).not.toHaveBeenCalled();

    rerender(
      <PendingButton pending pendingLabel="Creating church…">
        Create church
      </PendingButton>,
    );
    expect(screen.getByRole("button", { name: "Creating church…" })).toHaveAttribute("aria-disabled", "true");
  });

  it("keeps keyboard focus while pending and ignores Enter, Space and a form submit (build review fix 4)", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    const onSubmit = vi.fn((event: React.FormEvent) => event.preventDefault());
    function Form({ pending }: { pending: boolean }) {
      return (
        <form onSubmit={onSubmit}>
          <input aria-label="Name" />
          <PendingButton type="submit" pending={pending} onClick={onClick}>
            Save changes
          </PendingButton>
        </form>
      );
    }
    const { rerender } = render(<Form pending={false} />);
    const button = screen.getByRole("button", { name: "Save changes" });
    button.focus();
    expect(button).toHaveFocus();

    rerender(<Form pending />);
    const pendingButton = screen.getByRole("button", { name: "Saving…" });
    expect(pendingButton).toBe(button);
    expect(pendingButton).toHaveFocus();
    expect(pendingButton).not.toHaveAttribute("disabled");
    await user.keyboard("{Enter}");
    await user.keyboard(" ");
    await user.click(pendingButton);
    expect(onClick).not.toHaveBeenCalled();
    expect(onSubmit).not.toHaveBeenCalled();

    rerender(<Form pending={false} />);
    expect(button).toHaveFocus();
    expect(button).not.toHaveAttribute("aria-disabled");
  });

  it("is natively disabled when disabled without pending", () => {
    render(
      <PendingButton pending={false} disabled>
        Retry
      </PendingButton>,
    );
    expect(screen.getByRole("button", { name: "Retry" })).toBeDisabled();
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

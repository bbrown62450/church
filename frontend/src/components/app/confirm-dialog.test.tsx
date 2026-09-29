import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { ConfirmDialog } from "./confirm-dialog";

describe("ConfirmDialog", () => {
  it("names the action on the confirm button and calls onConfirm", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    const onOpenChange = vi.fn();
    const props = {
      open: true,
      onOpenChange,
      title: "Delete this service?",
      description: "Sunday, October 5. This can't be undone.",
      confirmLabel: "Delete service",
      onConfirm,
      destructive: true,
    };
    const { rerender } = render(<ConfirmDialog {...props} />);

    const dialog = await screen.findByRole("alertdialog", { name: "Delete this service?" });
    expect(dialog).toHaveAccessibleDescription("Sunday, October 5. This can't be undone.");
    await user.click(within(dialog).getByRole("button", { name: "Delete service" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onOpenChange).not.toHaveBeenCalled();
    expect(screen.getByRole("alertdialog")).toBeInTheDocument();

    rerender(<ConfirmDialog {...props} pending />);
    expect(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Saving…" })).toBeDisabled();
  });

  it("Cancel closes the dialog without confirming", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    const openChanges: boolean[] = [];
    function Harness() {
      const [open, setOpen] = useState(true);
      return (
        <ConfirmDialog
          open={open}
          onOpenChange={(next) => {
            openChanges.push(next);
            setOpen(next);
          }}
          title="Remove Ann from Grace Church?"
          confirmLabel="Remove member"
          onConfirm={onConfirm}
          destructive
        />
      );
    }
    render(<Harness />);

    const dialog = await screen.findByRole("alertdialog", { name: "Remove Ann from Grace Church?" });
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument());
    expect(openChanges).toEqual([false]);
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("names the cancel button when the screen's copy asks for it", async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    render(
      <ConfirmDialog
        open
        onOpenChange={onOpenChange}
        title="Replace your readings?"
        confirmLabel="Replace readings"
        cancelLabel="Keep mine"
        onConfirm={() => {}}
      />,
    );
    const dialog = await screen.findByRole("alertdialog", { name: "Replace your readings?" });
    expect(within(dialog).queryByRole("button", { name: "Cancel" })).toBeNull();
    await user.click(within(dialog).getByRole("button", { name: "Keep mine" }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useRef, useState } from "react";
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
    // 44 px tap targets on phones (F §4.9), the usual 32 px from md.
    for (const name of ["Cancel", "Delete service"]) {
      expect(within(dialog).getByRole("button", { name })).toHaveClass("h-11", "md:h-8");
    }
    await user.click(within(dialog).getByRole("button", { name: "Delete service" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onOpenChange).not.toHaveBeenCalled();
    expect(screen.getByRole("alertdialog")).toBeInTheDocument();

    rerender(<ConfirmDialog {...props} pending />);
    expect(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Saving…" })).toHaveAttribute("aria-disabled", "true");
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

  it("calls onCancel for the cancel button only, never for Escape, and focuses finalFocus when it closes", async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    function Harness() {
      const [open, setOpen] = useState(true);
      const after = useRef<HTMLDivElement>(null);
      return (
        <>
          <button type="button" onClick={() => setOpen(true)}>
            Ask again
          </button>
          <div ref={after} tabIndex={-1} data-testid="after" />
          <ConfirmDialog
            open={open}
            onOpenChange={setOpen}
            title="Replace your readings?"
            confirmLabel="Replace readings"
            cancelLabel="Keep mine"
            onCancel={onCancel}
            onConfirm={() => setOpen(false)}
            finalFocus={after}
          />
        </>
      );
    }
    render(<Harness />);
    await screen.findByRole("alertdialog", { name: "Replace your readings?" });
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(onCancel).not.toHaveBeenCalled();
    await waitFor(() => expect(screen.getByTestId("after")).toHaveFocus());

    await user.click(screen.getByRole("button", { name: "Ask again" }));
    let dialog = await screen.findByRole("alertdialog", { name: "Replace your readings?" });
    await user.click(within(dialog).getByRole("button", { name: "Keep mine" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(onCancel).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(screen.getByTestId("after")).toHaveFocus());

    await user.click(screen.getByRole("button", { name: "Ask again" }));
    dialog = await screen.findByRole("alertdialog", { name: "Replace your readings?" });
    await user.click(within(dialog).getByRole("button", { name: "Replace readings" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    await waitFor(() => expect(screen.getByTestId("after")).toHaveFocus());
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("shows more of the body under the description, above the buttons (slice 6b-2a)", async () => {
    render(
      <ConfirmDialog
        open
        onOpenChange={() => {}}
        title="Remove Ann Admin?"
        description="Ann Admin will lose access to Grace."
        confirmLabel="Remove member"
        onConfirm={() => {}}
        destructive
      >
        <label>
          <input type="checkbox" defaultChecked /> Also revoke the 1 reusable invite link
        </label>
      </ConfirmDialog>,
    );
    const dialog = await screen.findByRole("alertdialog", { name: "Remove Ann Admin?" });
    const box = within(dialog).getByRole("checkbox", { name: "Also revoke the 1 reusable invite link" });
    expect(box).toBeChecked();
    expect(box.compareDocumentPosition(within(dialog).getByRole("button", { name: "Remove member" })) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(dialog).toHaveAccessibleDescription("Ann Admin will lose access to Grace.");
  });

  it("names the pending action when asked (slice 6b-2a)", async () => {
    render(
      <ConfirmDialog open onOpenChange={() => {}} title="Revoke this invite?" confirmLabel="Revoke invite"
        onConfirm={() => {}} destructive pending pendingLabel="Revoking…" />,
    );
    const dialog = await screen.findByRole("alertdialog", { name: "Revoke this invite?" });
    expect(within(dialog).getByRole("button", { name: "Revoking…" })).toHaveAttribute("aria-disabled", "true");
  });
});

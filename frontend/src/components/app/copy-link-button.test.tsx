/** Copy link (slice 6b-2a; 6b spec UX 1a) and the initials avatar. */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { toast } from "sonner";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Toaster } from "@/components/ui/sonner";

import { COPY_FAILED, CopyLinkButton, LINK_COPIED } from "./copy-link-button";
import { InitialsAvatar } from "./initials-avatar";

const realExecCommand = document.execCommand;

afterEach(() => {
  toast.dismiss();
  document.execCommand = realExecCommand;
});

describe("CopyLinkButton (slice 6b-2a)", () => {
  it("copies the link, says Copied ✓ for two seconds and toasts Link copied", async () => {
    const user = userEvent.setup(); // installs a clipboard the test can read back
    const onCopyFailed = vi.fn();
    render(
      <>
        <CopyLinkButton text="http://localhost:3000/join?code=abc" onCopyFailed={onCopyFailed} size="touch" />
        <Toaster />
      </>,
    );
    await user.click(screen.getByRole("button", { name: "Copy link" }));
    expect(await screen.findByText(LINK_COPIED)).toBeInTheDocument();
    expect(LINK_COPIED).toBe("Link copied");
    expect(screen.getByRole("button", { name: "Copied ✓" })).toHaveClass("h-11");
    expect(await navigator.clipboard.readText()).toBe("http://localhost:3000/join?code=abc");
    expect(onCopyFailed).not.toHaveBeenCalled();
    await waitFor(() => expect(screen.getByRole("button", { name: "Copy link" })).toBeInTheDocument(), { timeout: 3000 });
  });

  it("selects the link through onCopyFailed and says so when copying is refused", async () => {
    const user = userEvent.setup();
    vi.spyOn(navigator.clipboard, "writeText").mockRejectedValue(new DOMException("Not allowed", "NotAllowedError"));
    document.execCommand = vi.fn(() => false);
    const onCopyFailed = vi.fn();
    render(
      <>
        <CopyLinkButton text="the link" onCopyFailed={onCopyFailed} label="Copy link for anyone with the link" />
        <Toaster />
      </>,
    );
    await user.click(screen.getByRole("button", { name: "Copy link for anyone with the link" }));
    expect(await screen.findByText(COPY_FAILED)).toBeInTheDocument();
    expect(COPY_FAILED).toBe("Couldn't copy. The link is selected; copy it from there.");
    expect(onCopyFailed).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Copy link for anyone with the link" })).toHaveTextContent("Copy link");
  });
});

describe("InitialsAvatar (slice 6b-2a)", () => {
  it("shows initials only, hidden from screen readers, and loads no picture", () => {
    const { container } = render(<InitialsAvatar name="Ann Admin" email="ann@example.com" />);
    const avatar = container.querySelector("[data-slot=avatar]");
    expect(avatar).toHaveTextContent("AA");
    expect(avatar).toHaveAttribute("aria-hidden", "true");
    expect(container.querySelector("img")).toBeNull();
    render(<InitialsAvatar name={null} email="sam@example.com" />);
    expect(screen.getByText("S", { exact: true })).toBeInTheDocument();
  });
});

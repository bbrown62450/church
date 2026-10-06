/**
 * The leave guard every settings form uses (slice 6a-1; the Bulletin settings
 * page's guard, shared): any in-app link to another page asks first while
 * there are unsaved edits; other links, and every link without edits, go on.
 */
import { act, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ChurchSwitcher } from "@/components/app/church-switcher";
import { testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import { DISCARD_TITLE, LeaveGuard } from "./leave-guard";

function Links({ dirty }: { dirty: boolean }) {
  return (
    <>
      <a href="/services?tab=saved">Services</a>
      <a href="/settings">Settings</a>
      <a href="#top">Top of this page</a>
      <a href="/services" target="_blank" rel="noreferrer">
        New tab
      </a>
      <a href="https://example.com/help">Help</a>
      <a href={`blob:${window.location.origin}/picture-1`}>Picture</a>
      <a
        href="/builder"
        onClick={(event) => {
          event.preventDefault(); // as Next's <Link replace> does
          testRouter.replace("/builder");
        }}
      >
        Builder
      </a>
      <LeaveGuard when={dirty} />
    </>
  );
}

/** Clicks `link`; true when the click went on as a link click (nothing prevented it). */
function followed(link: HTMLElement): boolean {
  const event = new MouseEvent("click", { bubbles: true, cancelable: true, button: 0 });
  act(() => {
    link.addEventListener("click", (e) => e.preventDefault(), { once: true }); // jsdom cannot navigate
    link.dispatchEvent(event);
  });
  return screen.queryByRole("alertdialog") === null;
}

describe("LeaveGuard (slice 6a-1)", () => {
  it("asks before an in-app link to another page while dirty, and only then", async () => {
    const { user, rerender } = renderWithProviders(<Links dirty={false} />, { path: "/settings/church" });
    expect(followed(screen.getByRole("link", { name: "Services" }))).toBe(true);

    rerender(<Links dirty />);
    for (const name of ["Top of this page", "New tab", "Help", "Picture"]) {
      expect(followed(screen.getByRole("link", { name }))).toBe(true);
    }
    await user.click(screen.getByRole("link", { name: "Services" }));
    const dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Discard changes" }));
    expect(testRouter.push).toHaveBeenCalledWith("/services?tab=saved");
  });

  it("after Discard changes, the link's own handler navigates, so a replace stays a replace", async () => {
    const { user } = renderWithProviders(<Links dirty />, { path: "/settings/church" });
    await user.click(screen.getByRole("link", { name: "Builder" }));
    expect(testRouter.replace).not.toHaveBeenCalled();
    const dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Discard changes" }));
    expect(testRouter.replace).toHaveBeenCalledWith("/builder");
    expect(testRouter.push).not.toHaveBeenCalled();
  });

  it("asks before the church menu's Join or create a church… while dirty, and not otherwise", async () => {
    const church = { id: "c-1", name: "Grace", role: "admin" } as const;
    const menu = (dirty: boolean) => (
      <>
        <ChurchSwitcher churches={[church]} activeId="c-1" onSelect={vi.fn()} />
        <LeaveGuard when={dirty} />
      </>
    );
    const { user, rerender } = renderWithProviders(menu(true), { path: "/settings/church" });
    const join = async () => {
      await user.click(screen.getByRole("button", { name: "Active church: Grace" }));
      await user.click(await screen.findByRole("menuitem", { name: "Join or create a church…" }));
    };

    await join();
    let dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Keep editing" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(testRouter.push).not.toHaveBeenCalled();
    // The menu item that asked has closed: focus goes back to the menu's trigger, not the page (review m6).
    await waitFor(() => expect(screen.getByRole("button", { name: "Active church: Grace" })).toHaveFocus());
    await join();
    dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Discard changes" }));
    expect(testRouter.push).toHaveBeenCalledWith("/welcome");

    testRouter.push.mockClear();
    rerender(menu(false));
    await join();
    expect(testRouter.push).toHaveBeenCalledWith("/welcome");
    expect(screen.queryByRole("alertdialog")).toBeNull();
  });

  it("takes down the browser's own warning once Discard changes is chosen (review m4)", async () => {
    const unload = () => {
      const event = new Event("beforeunload", { cancelable: true });
      window.dispatchEvent(event);
      return event.defaultPrevented;
    };
    const { user } = renderWithProviders(<Links dirty />, { path: "/settings/church" });
    expect(unload()).toBe(true);
    await user.click(screen.getByRole("link", { name: "Services" }));
    let dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Keep editing" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(unload()).toBe(true);
    await user.click(screen.getByRole("link", { name: "Services" }));
    dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    let warnedDuringLeave: boolean | null = null;
    testRouter.push.mockImplementationOnce(() => {
      warnedDuringLeave = unload(); // a navigation that falls back to a full page load fires beforeunload now
    });
    await user.click(within(dialog).getByRole("button", { name: "Discard changes" }));
    expect(testRouter.push).toHaveBeenCalledWith("/services?tab=saved");
    expect(warnedDuringLeave).toBe(false);
  });

  it("does nothing for a link to the Settings home from a page under /settings (review m5)", () => {
    const before = window.location.pathname;
    window.history.pushState(null, "", "/settings/church"); // the guard reads the address bar
    try {
      const { rerender } = renderWithProviders(<Links dirty />, { path: "/settings/church" });
      const settings = screen.getByRole("link", { name: "Settings" });
      const event = new MouseEvent("click", { bubbles: true, cancelable: true, button: 0 });
      act(() => {
        settings.dispatchEvent(event);
      });
      expect(event.defaultPrevented).toBe(true);
      expect(screen.queryByRole("alertdialog")).toBeNull();
      expect(testRouter.push).not.toHaveBeenCalled();
      // Without edits the link is not the guard's business.
      rerender(<Links dirty={false} />);
      expect(followed(settings)).toBe(true);
    } finally {
      window.history.pushState(null, "", before);
    }
  });
});

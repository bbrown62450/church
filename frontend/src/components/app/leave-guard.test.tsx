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
});

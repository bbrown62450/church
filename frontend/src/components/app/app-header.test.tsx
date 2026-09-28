import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AppHeader } from "@/components/app/app-header";
import type { Church, Me } from "@/lib/church";
import { testRouter } from "@/test/mocks";

const pat: Me["user"] = { id: "u-1", email: "pat@example.com", name: "Pat Doe", picture: null };
// Two churches with the same name: only the id (and the role shown) tells them apart.
const graceAdmin: Church = { id: "c-admin", name: "Grace", role: "admin" };
const graceMember: Church = { id: "c-member", name: "Grace", role: "member" };

describe("AppHeader", () => {
  it("lists same-name churches by id with their roles, and either one can be chosen", async () => {
    const onSelectChurch = vi.fn();
    const header = (active: Church) => (
      <AppHeader
        user={pat}
        churches={[graceAdmin, graceMember]}
        active={active}
        onSelectChurch={onSelectChurch}
        onSignOut={vi.fn()}
      />
    );
    const { rerender } = render(header(graceAdmin));
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Active church: Grace" }));
    const menu = await screen.findByRole("menu");
    expect(within(menu).getByRole("group", { name: "Your churches" })).toBeInTheDocument();
    expect(within(menu).getByRole("menuitemradio", { name: "Grace Admin" })).toHaveAttribute("aria-checked", "true");
    expect(within(menu).getByRole("menuitemradio", { name: "Grace Member" })).toHaveAttribute("aria-checked", "false");
    await user.click(within(menu).getByRole("menuitemradio", { name: "Grace Member" }));
    expect(onSelectChurch).toHaveBeenLastCalledWith("c-member");

    // The layout stores the new id and re-renders with it as the active church.
    rerender(header(graceMember));
    await user.click(screen.getByRole("button", { name: "Active church: Grace" }));
    expect(await screen.findByRole("menuitemradio", { name: "Grace Member" })).toHaveAttribute("aria-checked", "true");
    await user.click(screen.getByRole("menuitemradio", { name: "Grace Admin" }));
    expect(onSelectChurch).toHaveBeenLastCalledWith("c-admin");
    expect(onSelectChurch).toHaveBeenCalledTimes(2);
  });

  it("offers Join or create a church… below the list with one church, and it opens /welcome", async () => {
    const onSelectChurch = vi.fn();
    render(
      <AppHeader
        user={pat}
        churches={[graceAdmin]}
        active={graceAdmin}
        onSelectChurch={onSelectChurch}
        onSignOut={vi.fn()}
      />,
    );
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Active church: Grace" }));
    const menu = await screen.findByRole("menu");
    const list = within(menu).getByRole("group", { name: "Your churches" });
    expect(within(list).getAllByRole("menuitemradio")).toHaveLength(1);
    const separator = within(menu).getByRole("separator");
    const item = within(menu).getByRole("menuitem", { name: "Join or create a church…" });
    // S Flow C order: the church list, a separator, then the item.
    expect(list.compareDocumentPosition(separator) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(separator.compareDocumentPosition(item) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    await user.click(item);
    expect(testRouter.push).toHaveBeenCalledTimes(1);
    expect(testRouter.push).toHaveBeenCalledWith("/welcome");
    expect(testRouter.replace).not.toHaveBeenCalled();
    expect(onSelectChurch).not.toHaveBeenCalled();
    await waitFor(() => expect(screen.queryByRole("menu")).toBeNull());
  });

  it("shows the user's name, email and role label in the account menu", async () => {
    render(
      <AppHeader
        user={pat}
        churches={[graceAdmin]}
        active={graceAdmin}
        onSelectChurch={vi.fn()}
        onSignOut={vi.fn()}
      />,
    );
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Account menu" }));
    const menu = await screen.findByRole("menu");
    expect(within(menu).getByText("Pat Doe")).toBeInTheDocument();
    expect(within(menu).getByText("pat@example.com")).toBeInTheDocument();
    expect(within(menu).getByText("Role: Admin")).toBeInTheDocument();
  });

  it("calls onSignOut from Log out", async () => {
    const onSignOut = vi.fn();
    render(
      <AppHeader
        user={pat}
        churches={[graceAdmin]}
        active={graceAdmin}
        onSelectChurch={vi.fn()}
        onSignOut={onSignOut}
      />,
    );
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Account menu" }));
    await user.click(await screen.findByRole("menuitem", { name: "Log out" }));
    expect(onSignOut).toHaveBeenCalledTimes(1);
  });

  it("shows the app name and no switcher without churches, and still offers Log out", async () => {
    const onSignOut = vi.fn();
    render(<AppHeader user={pat} onSignOut={onSignOut} />);
    const user = userEvent.setup();

    expect(screen.getByText("Worship Service Builder")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /church/i })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Account menu" }));
    const menu = await screen.findByRole("menu");
    expect(within(menu).queryByText(/^Role:/)).toBeNull();
    await user.click(within(menu).getByRole("menuitem", { name: "Log out" }));
    expect(onSignOut).toHaveBeenCalledTimes(1);
  });
});

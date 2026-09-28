import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AppHeader } from "@/components/app/app-header";
import type { Church, Me } from "@/lib/church";

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

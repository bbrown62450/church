/** The Settings area's shell (slice 6a-1; 6a spec "Settings nav"): the heading, the section nav, `/settings`. */
import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
import SettingsHome from "@/app/(signed-in)/(church)/settings/page";
import type { Church } from "@/lib/api/types";
import { church, me } from "@/test/fixtures";
import { testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

function renderShell(role: Church["role"], path = "/settings/church") {
  const active = church({ role });
  return renderWithProviders(
    <SettingsLayout>
      <p>The section</p>
    </SettingsLayout>,
    { me: me({ churches: [active] }), church: active, path },
  );
}

describe("the Settings area (slice 6a-1)", () => {
  it("shows the heading, who you are in the church, and the sections with the current one marked", () => {
    const { unmount } = renderShell("admin");
    expect(screen.getByRole("heading", { level: 1, name: "Settings" })).toBeInTheDocument();
    expect(screen.getByText("You're an admin of Grace.")).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Settings sections" });
    const links = within(nav).getAllByRole("link");
    expect(links.map((link) => [link.textContent, link.getAttribute("href")])).toEqual([
      ["Church", "/settings/church"],
      ["Bulletin", "/bulletin-settings"],
      ["Contacts", "/settings/contacts"],
      ["Account", "/settings/account"],
    ]);
    expect(links[0]).toHaveAttribute("aria-current", "page");
    for (const link of links.slice(1)) expect(link).not.toHaveAttribute("aria-current");
    expect(links[0]).toHaveClass("h-11", "md:h-9");
    expect(screen.getByText("The section")).toBeInTheDocument();
    unmount();

    renderShell("owner");
    expect(screen.getByText("You're the owner of Grace.")).toBeInTheDocument();
  });

  it.each([
    ["/settings/contacts", "Contacts"],
    ["/settings/account", "Account"],
  ])("marks the section current on its page (slices 5b-1, 5b-2): %s", (path, label) => {
    renderShell("member", path);
    const links = within(screen.getByRole("navigation", { name: "Settings sections" })).getAllByRole("link");
    expect(links.filter((link) => link.getAttribute("aria-current") === "page").map((link) => link.textContent)).toEqual([
      label,
    ]);
  });

  it("shows a member the same sections, and /settings opens Church", () => {
    renderShell("member", "/settings");
    expect(screen.getByText("You're a member of Grace.")).toBeInTheDocument();
    expect(within(screen.getByRole("navigation", { name: "Settings sections" })).getAllByRole("link")).toHaveLength(4);
    renderWithProviders(<SettingsHome />, { path: "/settings" });
    expect(testRouter.replace).toHaveBeenCalledWith("/settings/church");
  });
});

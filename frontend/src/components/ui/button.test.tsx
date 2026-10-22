import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button } from "./button";

describe("Button", () => {
  it("has a 44 px touch size for primary actions on phones (F §4.8)", () => {
    render(<Button size="touch">Create church</Button>);
    const button = screen.getByRole("button", { name: "Create church" });
    expect(button).toHaveClass("h-11", "px-4");
    expect(button).not.toHaveClass("h-8");
  });

  it.each([
    ["default", "ring-ring"],
    ["outline", "ring-ring"],
    ["secondary", "ring-ring"],
    ["ghost", "ring-ring"],
    ["link", "ring-ring"],
    ["destructive", "ring-destructive"],
  ] as const)("draws a full-strength focus ring on the %s button (Theme PR 1)", (variant, ring) => {
    render(<Button variant={variant}>Go</Button>);
    const button = screen.getByRole("button", { name: "Go" });
    expect(button).toHaveClass("outline-none", "focus-visible:ring-3", `focus-visible:${ring}`);
    expect(button.className).not.toMatch(/focus-visible:ring-[\w-]+\/\d+/);
  });

  /** The variant's own text and fill colors (not sizes, not hover or dark states); tokens.test.ts checks each pair's contrast. */
  const colors = (className: string) =>
    className.split(/\s+/).filter((c) => /^(?:text|bg)-/.test(c) && !/^text-(?:xs|sm|base|lg|\[)|^bg-clip-/.test(c)).sort();

  it.each([
    ["default", ["bg-primary", "text-primary-foreground"]],
    ["outline", ["bg-transparent", "text-primary"]],
    ["secondary", ["bg-secondary", "text-secondary-foreground"]],
    ["ghost", []],
    ["destructive", ["bg-destructive/10", "text-destructive"]],
    ["link", ["text-primary"]],
  ] as const)("draws the %s button's text on its own fill (Theme PR 1)", (variant, pair) => {
    render(<Button variant={variant}>Go</Button>);
    expect(colors(screen.getByRole("button", { name: "Go" }).className)).toEqual(pair);
  });

  it("keeps the ghost button on its surface's text, and its hover and the destructive tint in dark on their tokens (Theme PR 1)", () => {
    const { unmount } = render(<Button variant="ghost">Go</Button>);
    expect(screen.getByRole("button", { name: "Go" })).toHaveClass("hover:bg-foreground/8", "hover:text-foreground");
    unmount();
    render(<Button variant="destructive">Go</Button>);
    expect(screen.getByRole("button", { name: "Go" })).toHaveClass("dark:bg-destructive/20");
  });
});

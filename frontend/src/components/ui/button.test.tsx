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
});

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
});

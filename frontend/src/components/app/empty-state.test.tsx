import { render, screen } from "@testing-library/react";
import { InboxIcon } from "lucide-react";
import { describe, expect, it } from "vitest";

import { Button } from "@/components/ui/button";

import { EmptyState } from "./empty-state";

describe("EmptyState", () => {
  it("shows the icon, a one-line title, one sentence and the primary action", () => {
    const { container } = render(
      <EmptyState
        icon={InboxIcon}
        title="No services yet"
        description="Plan your first service to see it here."
        action={<Button size="touch">Plan a service</Button>}
      />,
    );

    expect(screen.getByRole("heading", { level: 2, name: "No services yet" })).toBeInTheDocument();
    expect(screen.getByText("Plan your first service to see it here.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Plan a service" })).toBeInTheDocument();
    expect(container.querySelector("svg[aria-hidden='true']")).not.toBeNull();
  });
});

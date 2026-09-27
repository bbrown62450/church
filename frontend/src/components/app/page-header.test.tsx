import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button } from "@/components/ui/button";

import { PageHeader } from "./page-header";

describe("PageHeader", () => {
  it("renders the title as the page h1 with its description and actions", () => {
    const { rerender } = render(
      <PageHeader
        title="Services"
        description="Everything planned for Grace Church."
        actions={<Button>New service</Button>}
      />,
    );

    expect(screen.getByRole("heading", { level: 1, name: "Services" })).toBeInTheDocument();
    expect(screen.getByText("Everything planned for Grace Church.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "New service" })).toBeInTheDocument();

    rerender(<PageHeader title="Home" />);
    expect(screen.getByRole("heading", { level: 1, name: "Home" })).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});

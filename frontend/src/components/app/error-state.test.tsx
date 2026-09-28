import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";

import { ErrorState } from "./error-state";

describe("ErrorState", () => {
  it("shows the title and the server message, and Retry calls onRetry", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    render(
      <ErrorState
        title="Couldn't load the church"
        error={new ApiError(409, "conflict", "Someone else changed this.")}
        onRetry={onRetry}
      />,
    );

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Couldn't load the church");
    expect(alert).toHaveTextContent("Someone else changed this.");
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
    expect(onRetry).toHaveBeenCalledWith();
  });

  it("says Can't reach the server. for a network error", () => {
    render(
      <ErrorState
        error={new ApiError(0, "network_error", "Can't reach the server. Check your connection and try again.")}
        onRetry={() => {}}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(/^Can't reach the server\.$/);
    expect(screen.getByRole("button", { name: "Retry" })).toBeEnabled();
  });

  it("shows Something went wrong. with the first 8 characters of the request id for a 5xx", () => {
    render(
      <ErrorState
        error={new ApiError(502, "upstream_error", "Bad gateway", { requestId: "0123456789abcdef" })}
        onRetry={() => {}}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(/^Something went wrong\. \(Ref: 01234567\)$/);
  });
});

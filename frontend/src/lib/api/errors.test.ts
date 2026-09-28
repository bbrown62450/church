import { describe, expect, it } from "vitest";

import { ApiError, NETWORK_MESSAGE } from "./client";
import { describeError, errorToastMessage, isNoChurchAccess } from "./errors";

describe("isNoChurchAccess", () => {
  it("is true for a require_church 403", () => {
    const lost = new ApiError(403, "forbidden", "You don't have access to this church.", {
      details: { reason: "no_church_access" },
    });
    expect(isNoChurchAccess(lost)).toBe(true);
  });

  it("is false for a role 403, another code or a non-ApiError", () => {
    expect(isNoChurchAccess(new ApiError(403, "forbidden", "Only church admins can do this."))).toBe(false);
    expect(
      isNoChurchAccess(new ApiError(404, "not_found", "Not found.", { details: { reason: "no_church_access" } })),
    ).toBe(false);
    expect(isNoChurchAccess(new Error("forbidden"))).toBe(false);
    expect(isNoChurchAccess({ code: "forbidden", details: { reason: "no_church_access" } })).toBe(false);
  });
});

describe("describeError", () => {
  it("says the server can't be reached for a network error", () => {
    const e = new ApiError(0, "network_error", "Can't reach the server. Check your connection and try again.");
    expect(describeError(e)).toBe("Can't reach the server.");
  });

  it("uses the timeout's own message", () => {
    expect(describeError(new ApiError(0, "timeout", "This is taking too long. Try again."))).toBe(
      "This is taking too long. Try again.",
    );
  });

  it("hides a 5xx message behind a reference from the request id", () => {
    const withRef = new ApiError(500, "internal_error", "Something went wrong.", { requestId: "0123456789abcdef" });
    expect(describeError(withRef)).toBe("Something went wrong. (Ref: 01234567)");
    const noRef = new ApiError(503, "db_unavailable", "The database is not reachable.");
    expect(describeError(noRef)).toBe("Something went wrong.");
  });

  it("shows a 4xx server message, and a generic one for anything else", () => {
    expect(describeError(new ApiError(409, "conflict", "Someone else changed this."))).toBe("Someone else changed this.");
    expect(describeError(new TypeError("x is undefined"))).toBe("Something went wrong.");
    expect(describeError("boom")).toBe("Something went wrong.");
  });
});

describe("errorToastMessage", () => {
  it("uses the full sentence for a network error, a timeout or a cancel", () => {
    expect(errorToastMessage(new ApiError(0, "network_error", NETWORK_MESSAGE))).toBe(
      "Can't reach the server. Check your connection and try again.",
    );
    expect(errorToastMessage(new ApiError(0, "timeout", "This is taking too long. Try again."))).toBe(
      "This is taking too long. Try again.",
    );
    expect(errorToastMessage(new ApiError(0, "aborted", "The request was cancelled."))).toBe("The request was cancelled.");
  });

  it("falls back to describeError: a 5xx reference, a 4xx message, a generic line", () => {
    const withRef = new ApiError(500, "internal_error", "Something went wrong.", { requestId: "0123456789abcdef" });
    expect(errorToastMessage(withRef)).toBe("Something went wrong. (Ref: 01234567)");
    expect(errorToastMessage(new ApiError(503, "db_unavailable", "The database is not reachable."))).toBe(
      "Something went wrong.",
    );
    expect(errorToastMessage(new ApiError(400, "invite_rejected", "This invite has expired."))).toBe(
      "This invite has expired.",
    );
    expect(errorToastMessage(new TypeError("x is undefined"))).toBe("Something went wrong.");
  });
});

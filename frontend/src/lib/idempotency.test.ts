import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";

import { createKeyTracker, settleOutcome, stableStringify } from "./idempotency";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const BODY = { name: "New Life", timezone: "America/Chicago" };

describe("createKeyTracker", () => {
  it("gives the same body the same UUID key until it is settled (a double tap while in flight)", () => {
    const tracker = createKeyTracker();
    const first = tracker.keyFor(BODY);
    expect(first).toMatch(UUID);
    expect(tracker.keyFor({ ...BODY })).toBe(first);
    expect(tracker.keyFor(BODY)).toBe(first);
  });

  it("keeps the key after an uncertain outcome, so an identical retry can replay", () => {
    const tracker = createKeyTracker();
    const first = tracker.keyFor(BODY);
    tracker.settle("uncertain");
    expect(tracker.keyFor(BODY)).toBe(first);
    tracker.settle("uncertain");
    expect(tracker.keyFor(BODY)).toBe(first);
  });

  it("drops the key after a client error", () => {
    const tracker = createKeyTracker();
    const first = tracker.keyFor(BODY);
    tracker.settle("client_error");
    const second = tracker.keyFor(BODY);
    expect(second).toMatch(UUID);
    expect(second).not.toBe(first);
  });

  it("drops the key after a success", () => {
    const tracker = createKeyTracker();
    const first = tracker.keyFor(BODY);
    tracker.settle("success");
    const second = tracker.keyFor(BODY);
    expect(second).toMatch(UUID);
    expect(second).not.toBe(first);
  });

  it("gives a changed body a new key, even while the first one is pending", () => {
    const tracker = createKeyTracker();
    const first = tracker.keyFor(BODY);
    tracker.settle("uncertain");
    const edited = tracker.keyFor({ ...BODY, name: "New Life Church" });
    expect(edited).toMatch(UUID);
    expect(edited).not.toBe(first);
    expect(tracker.keyFor({ ...BODY, name: "New Life Church" })).toBe(edited);
  });
});

describe("stableStringify", () => {
  it("ignores object key order at every depth, so a reordered body keeps its key", () => {
    const a = { b: 1, a: { d: [2, { f: 1, e: 0 }], c: "x" } };
    const b = { a: { c: "x", d: [2, { e: 0, f: 1 }] }, b: 1 };
    expect(stableStringify(a)).toBe('{"a":{"c":"x","d":[2,{"e":0,"f":1}]},"b":1}');
    expect(stableStringify(b)).toBe(stableStringify(a));
    expect(stableStringify([3, "x", null])).toBe('[3,"x",null]');

    const tracker = createKeyTracker();
    const first = tracker.keyFor({ name: "Grace", timezone: "Europe/London" });
    expect(tracker.keyFor({ timezone: "Europe/London", name: "Grace" })).toBe(first);
  });
});

describe("settleOutcome", () => {
  it("maps a 4xx other than 429 to client_error and everything else to uncertain", () => {
    const cases: [unknown, "client_error" | "uncertain"][] = [
      [new ApiError(400, "invite_rejected", "Invalid invite code."), "client_error"],
      [new ApiError(422, "invalid_request", "Unknown timezone.", { fields: { timezone: "Unknown timezone." } }), "client_error"],
      [
        new ApiError(429, "rate_limited", "You've created 5 churches in the last 24 hours. Try again later.", {
          retryAfterSeconds: 60,
        }),
        "uncertain",
      ],
      [new ApiError(429, "rate_limited", "Too many requests. Try again in 20 seconds.", { retryAfterSeconds: 20 }), "uncertain"],
      [new ApiError(0, "network_error", "Can't reach the server. Check your connection and try again."), "uncertain"],
      [new ApiError(0, "timeout", "This is taking too long. Try again."), "uncertain"],
      [new ApiError(0, "aborted", "The request was cancelled."), "uncertain"],
      [new ApiError(500, "internal_error", "Something went wrong."), "uncertain"],
      [new ApiError(503, "db_unavailable", "The database is not reachable."), "uncertain"],
      [new Error("boom"), "uncertain"],
    ];
    for (const [error, outcome] of cases) {
      expect(settleOutcome(error), String(error)).toBe(outcome);
    }
  });
});

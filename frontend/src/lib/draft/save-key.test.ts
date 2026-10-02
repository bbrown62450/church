import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";
import { settleOutcome } from "@/lib/idempotency";
import { testDraft } from "@/test/fixtures";

import { keyForPost, settlePost } from "./save-key";

describe("the save key (slice 5a spec, Save key rule; F §1.6)", () => {
  it("keyForPost keeps the key for the first try and an identical retry, and replaces it when the body changed", () => {
    const d = testDraft();
    const first = keyForPost(d, "aaaa0001");
    expect(first).toMatchObject({ save_key: d.save_key, save_key_fingerprint: "aaaa0001" });
    expect(keyForPost(first, "aaaa0001")).toBe(first); // the same body after an unknown outcome: the same key
    const edited = keyForPost(first, "bbbb0002");
    expect(edited.save_key).not.toBe(d.save_key);
    expect(edited.save_key_fingerprint).toBe("bbbb0002");
  });

  it("settlePost replaces the key after any answer, and keeps it while the outcome is unknown", () => {
    const sent = keyForPost(testDraft(), "aaaa0001");
    const answered = (outcome: Parameters<typeof settlePost>[1]) => settlePost(sent, outcome);
    for (const outcome of ["success", "client_error"] as const) {
      expect(answered(outcome).save_key).not.toBe(sent.save_key);
      expect(answered(outcome).save_key_fingerprint).toBeNull();
    }
    expect(answered("uncertain")).toBe(sent);
    // What each failure counts as: every 4xx but a 429 is an answer; the rest are unknown.
    for (const [status, code] of [[400, "bad_request"], [404, "not_found"], [422, "invalid_request"], [422, "idempotency_mismatch"]] as const) {
      expect(settleOutcome(new ApiError(status, code, "x")), code).toBe("client_error");
    }
    for (const e of [new ApiError(0, "network_error", "x"), new ApiError(0, "timeout", "x"), new ApiError(0, "aborted", "x"),
      new ApiError(500, "internal_error", "x"), new ApiError(503, "db_unavailable", "x"), new ApiError(429, "rate_limited", "x")]) {
      expect(settleOutcome(e), e.code).toBe("uncertain");
    }
  });
});

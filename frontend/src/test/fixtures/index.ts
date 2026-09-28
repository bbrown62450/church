/**
 * Builders for API payloads in tests. Each call returns a fresh object;
 * `overrides` replace top-level fields (pass a whole `user` to change it).
 */
import type { Church, Me } from "@/lib/church";

/** Ids that read well in failure output (valid UUIDs, like the API's). */
export const CHURCH_IDS = {
  grace: "11111111-1111-4111-8111-111111111111",
  hope: "22222222-2222-4222-8222-222222222222",
  trinity: "33333333-3333-4333-8333-333333333333",
} as const;

export const USER_ID = "99999999-9999-4999-8999-999999999999";

/** Grace (admin) unless overridden. */
export function church(overrides: Partial<Church> = {}): Church {
  return { id: CHURCH_IDS.grace, name: "Grace", role: "admin", ...overrides };
}

/** Pat Pastor, a member of Grace only, unless overridden. */
export function me(overrides: Partial<Me> = {}): Me {
  return {
    user: { id: USER_ID, email: "pat@example.com", name: "Pat Pastor", picture: null },
    churches: [church()],
    ...overrides,
  };
}

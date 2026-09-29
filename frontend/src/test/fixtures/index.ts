/**
 * Builders for API payloads in tests. Each call returns a fresh object;
 * `overrides` replace top-level fields (pass a whole `user` to change it).
 */
import type { ChurchProfile, InviteAccepted, InvitePreview } from "@/lib/api/types";
import type { Church, Me } from "@/lib/church";
import { freshDraft, type DraftV1 } from "@/lib/draft/schema";

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

/**
 * `POST /invites/preview`'s body: a member invite to Grace, not bound to an
 * email, for someone not yet a member. It expires at midday UTC, so
 * "Invite expires October 5, 2026." reads the same in every zone from UTC-11 to UTC+11.
 */
export function invitePreview(overrides: Partial<InvitePreview> = {}): InvitePreview {
  return {
    church_name: "Grace",
    role: "member",
    expires_at: "2026-10-05T12:00:00Z",
    email_bound: false,
    already_member: false,
    ...overrides,
  };
}

/** `POST /invites/accept`'s body: Pat joined Grace as a member. */
export function inviteAccepted(overrides: Partial<InviteAccepted> = {}): InviteAccepted {
  return {
    church: church({ role: "member" }),
    already_member: false,
    message: "Joined Grace.",
    ...overrides,
  };
}

// --- slice 2b: the church profile, drafts and lectionary answers ------------------

/** `GET /church` for Grace (slice 2a's `ChurchProfileOut`): New York, WEB. */
export function churchProfile(overrides: Partial<ChurchProfile> = {}): ChurchProfile {
  return {
    ...church(),
    timezone: "America/New_York",
    timezone_valid: true,
    bible_translation: null,
    effective_translation: "web",
    effective_translation_label: "World English Bible (WEB)",
    ...overrides,
  };
}

/** Tuesday, September 29, 2026 at noon in New York: the next Sunday is October 4 (a first Sunday). */
export const DRAFT_NOW = new Date(Date.UTC(2026, 8, 29, 16, 0));

/** Pat's fresh draft for Grace at `DRAFT_NOW`, then `recipe` applied (the recipe may return a new object). */
export function testDraft(recipe: (d: DraftV1) => DraftV1 = (d) => d): DraftV1 {
  return recipe(freshDraft({ church: churchProfile(), user: { id: USER_ID }, now: DRAFT_NOW }));
}

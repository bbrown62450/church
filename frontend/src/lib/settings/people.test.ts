import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import type { Church, Member } from "@/lib/api/types";
import { invite, member, PEOPLE } from "@/test/fixtures";

import {
  displayName,
  formatDateTime,
  formatExpiry,
  initials,
  inviteSummary,
  invitesCreatedBy,
  memberActions,
  otherReusableInvites,
} from "./people";

type PolicyRow = {
  action: "change_role" | "remove" | "leave" | "transfer";
  actor_role: Church["role"];
  target?: "self" | Member["role"];
  new_role?: "member" | "admin";
  expected: string;
};

const POLICY: { rows: PolicyRow[] } = JSON.parse(
  readFileSync(new URL("../../../../backend/tests/fixtures/shared/role_policy.json", import.meta.url), "utf-8"),
);

/** The fixture's change_role and remove rows, grouped by (actor role, target): 11 pairs. */
function pairs(): Map<string, PolicyRow[]> {
  const grouped = new Map<string, PolicyRow[]>();
  for (const row of POLICY.rows.filter((r) => r.action === "change_role" || r.action === "remove")) {
    const key = `${row.actor_role}/${row.target}`;
    grouped.set(key, [...(grouped.get(key) ?? []), row]);
  }
  return grouped;
}

describe("memberActions mirrors the server's role policy (6b spec Testing → Frontend; slice 6b-2a)", () => {
  it("covers the 11 (actor, target) pairs of the shared fixture's change_role and remove rows", () => {
    expect([...pairs().keys()].sort()).toEqual([
      "admin/admin", "admin/member", "admin/owner", "admin/self",
      "member/admin", "member/member", "member/owner", "member/self",
      "owner/admin", "owner/member", "owner/self",
    ]);
  });

  it.each([...pairs().entries()])("offers what the server allows: %s", (_key, rows) => {
    const actorRole = rows[0].actor_role;
    const target = rows[0].target!;
    const actor = { id: "a", role: actorRole };
    const targetRow = member(target === "self" ? { user_id: "a", role: actorRole } : { user_id: "t", role: target });
    const changes = rows.filter((r) => r.action === "change_role");
    const removal = rows.filter((r) => r.action === "remove");
    expect(changes).toHaveLength(2);
    expect(removal).toHaveLength(1);

    const allowed = changes.filter((r) => r.expected === "allow");
    const got = memberActions(actor, targetRow);
    if (allowed.length === 1) {
      expect(changes.filter((r) => r.expected === "noop")).toHaveLength(1);
      expect(got.changeRoleTo).toBe(allowed[0].new_role);
    } else {
      expect(changes.map((r) => r.expected)).toEqual(["forbidden", "forbidden"]);
      expect(got.changeRoleTo).toBeNull();
    }
    expect(got.canRemove).toBe(removal[0].expected === "allow");
    expect(["allow", "forbidden"]).toContain(removal[0].expected);
  });
});

describe("the People page's names and sentences (slice 6b-2a)", () => {
  it("names a person by their name, trimmed, else their email", () => {
    expect(displayName(member())).toBe("Mo Member");
    expect(displayName(member({ name: "  Mo  " }))).toBe("Mo");
    expect(displayName(member({ name: null }))).toBe("mo@example.com");
    expect(displayName(member({ name: "   " }))).toBe("mo@example.com");
  });

  it("gives up to two initials: first and last word, else the email's first letter", () => {
    expect(initials(member())).toBe("MM");
    expect(initials(member({ name: "mary ann  jones " }))).toBe("MJ");
    expect(initials(member({ name: "Cher" }))).toBe("C");
    expect(initials(member({ name: null, email: "sam@example.com" }))).toBe("S");
    expect(initials(member({ name: "Émile Zola" }))).toBe("ÉZ");
  });

  it("says who can use a link, for what role and until when, in three ways", () => {
    const at = (iso: string) => `[${iso}]`;
    const expires_at = "2026-10-17T15:00:00Z";
    expect(inviteSummary({ email: null, role: "member", reusable: false, expires_at }, "Grace", at)).toBe(
      "Anyone who opens this link can join Grace as a member. It works once and expires [2026-10-17T15:00:00Z].",
    );
    expect(inviteSummary({ email: "b@example.com", role: "admin", reusable: false, expires_at }, "Grace", at)).toBe(
      "Only b@example.com can use this link to join Grace as an admin. It works once and expires [2026-10-17T15:00:00Z].",
    );
    expect(inviteSummary({ email: null, role: "admin", reusable: true, expires_at }, "Grace", at)).toBe(
      "Anyone with this link can join Grace as an admin until [2026-10-17T15:00:00Z]. Share it only with people you trust.",
    );
  });

  it("writes a date and time plainly, and nothing for an unreadable value", () => {
    expect(formatDateTime("2026-10-17T15:00:00Z", { timeZone: "America/New_York" })).toBe("Oct 17, 2026, 11:00 AM");
    expect(formatDateTime("not a time")).toBe("");
  });

  it("says when an invite expires in days, hours or less than an hour", () => {
    const now = new Date("2026-10-10T12:00:00Z");
    const zone = { timeZone: "UTC" };
    expect(formatExpiry("2026-10-17T11:59:00Z", now, zone)).toEqual({ relative: "in 7 days", full: "Oct 17, 2026, 11:59 AM" });
    expect(formatExpiry("2026-10-11T13:00:00Z", now, zone).relative).toBe("in 1 day");
    expect(formatExpiry("2026-10-10T17:10:00Z", now, zone).relative).toBe("in 5 hours");
    expect(formatExpiry("2026-10-10T13:00:00Z", now, zone).relative).toBe("in 1 hour");
    expect(formatExpiry("2026-10-10T12:59:00Z", now, zone).relative).toBe("in less than an hour");
    expect(formatExpiry("2026-10-10T11:00:00Z", now, zone).relative).toBe("in less than an hour");
  });

  it("chooses the unit after rounding, so 23.5 hours or more reads in 1 day", () => {
    const now = new Date("2026-10-10T12:00:00Z");
    expect(formatExpiry("2026-10-11T11:30:00Z", now).relative).toBe("in 1 day");
    expect(formatExpiry("2026-10-11T11:59:00Z", now).relative).toBe("in 1 day");
    expect(formatExpiry("2026-10-11T11:20:00Z", now).relative).toBe("in 23 hours");
  });

  it("counts the invites a person made, and the reusable links others made", () => {
    const mine = { user_id: PEOPLE.ann, name: "Ann Admin", email: "ann@example.com" };
    const invites = [
      invite({ id: "1", created_by: mine }),
      invite({ id: "2", created_by: mine, reusable: true }),
      invite({ id: "3", reusable: true }),
      invite({ id: "4", reusable: true, created_by: null }),
      invite({ id: "5" }),
    ];
    expect(invitesCreatedBy(invites, PEOPLE.ann)).toBe(2);
    expect(otherReusableInvites(invites, PEOPLE.ann)).toBe(2);
    expect(invitesCreatedBy([], PEOPLE.ann)).toBe(0);
  });
});

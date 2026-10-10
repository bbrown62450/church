/**
 * Settings → People's rules (slice 6b-2a; 6b spec "Pure helpers"): how a
 * person is named and shown, what an admin may do to a row (a mirror of the
 * server's role policy, tested against its shared fixture), and the invite
 * link's sentences. They decide only what the page shows; the server enforces.
 */
import type { Church, Invite, Member } from "@/lib/api/types";

/** A name or an email, as `MemberOut` and `InviteCreatorOut` carry them. */
type Person = Pick<Member, "name" | "email">;

/** The name, trimmed, else the email. */
export function displayName(person: Person): string {
  return person.name?.trim() || person.email;
}

/**
 * Up to two letters for the avatar: the first letters of the name's first and
 * last words, else the email's first letter, upper-cased.
 */
export function initials(person: Person): string {
  const words = (person.name ?? "").trim().split(/\s+/).filter(Boolean);
  const first = (word: string) => Array.from(word)[0] ?? "";
  if (words.length === 0) return first(person.email.trim()).toUpperCase();
  const letters = words.length === 1 ? first(words[0]) : first(words[0]) + first(words[words.length - 1]);
  return letters.toUpperCase();
}

export type MemberActions = {
  /** The role the menu offers ("Make admin" or "Make member"), or null: no role change. */
  changeRoleTo: "admin" | "member" | null;
  canRemove: boolean;
};

/**
 * What `actor` may do to `target`, mirroring the server's
 * `role_policy.check_role_change` and `check_remove` (`people.test.ts` runs
 * their shared fixture's change_role and remove rows): owners and admins make
 * a member an admin or an admin a member, and remove either; nobody acts on
 * their own row or on the owner's.
 */
export function memberActions(actor: { id: string; role: Church["role"] }, target: Member): MemberActions {
  const none: MemberActions = { changeRoleTo: null, canRemove: false };
  if (actor.role === "member") return none;
  if (target.user_id === actor.id || target.role === "owner") return none;
  return { changeRoleTo: target.role === "member" ? "admin" : "member", canRemove: true };
}

/** "a member" or "an admin". */
function asRole(role: Invite["role"]): string {
  return role === "admin" ? "an admin" : "a member";
}

/** The Invite link ready panel's sentence (UX 1a), with `formatDateTime` for the expiry. */
export function inviteSummary(
  invite: Pick<Invite, "email" | "role" | "reusable" | "expires_at">,
  churchName: string,
  formatDateTime: (iso: string) => string,
): string {
  const until = formatDateTime(invite.expires_at);
  if (invite.reusable) {
    return `Anyone with this link can join ${churchName} as ${asRole(invite.role)} until ${until}. Share it only with people you trust.`;
  }
  if (invite.email) {
    return `Only ${invite.email} can use this link to join ${churchName} as ${asRole(invite.role)}. It works once and expires ${until}.`;
  }
  return `Anyone who opens this link can join ${churchName} as ${asRole(invite.role)}. It works once and expires ${until}.`;
}

/** A timestamp as "Oct 17, 2026, 3:00 PM" (`timeZone` for tests; the device's zone otherwise). */
export function formatDateTime(iso: string, { timeZone }: { timeZone?: string } = {}): string {
  const at = Date.parse(iso);
  if (!Number.isFinite(at)) return "";
  const options: Intl.DateTimeFormatOptions = {
    month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit",
    ...(timeZone === undefined ? {} : { timeZone }),
  };
  // Newer ICU puts a narrow no-break space before AM/PM; a plain space reads the same everywhere.
  return new Intl.DateTimeFormat("en-US", options).format(at).replace(/\u202f/g, " ");
}

const HOUR = 60 * 60 * 1000;
const DAY = 24 * HOUR;

/**
 * When an invite expires, for its row: `relative` ("in 7 days", "in 5 hours",
 * "in less than an hour") and `full` (the date and time, for `title` and
 * `aria-label`). Days and hours are rounded to the nearest whole one.
 */
export function formatExpiry(
  expiresAtIso: string,
  now: Date = new Date(),
  { timeZone }: { timeZone?: string } = {},
): { relative: string; full: string } {
  const left = Date.parse(expiresAtIso) - now.getTime();
  const words = new Intl.RelativeTimeFormat("en-US", { numeric: "always" });
  let relative: string;
  const hours = Math.round(left / HOUR);
  // The unit is chosen after rounding, so 23.5 hours reads "in 1 day", never "in 24 hours".
  if (!(left >= HOUR)) relative = "in less than an hour";
  else if (hours < 24) relative = words.format(hours, "hour");
  else relative = words.format(Math.round(left / DAY), "day");
  return { relative, full: formatDateTime(expiresAtIso, { timeZone }) };
}

/** Invites `creatorId` made: the removal revokes them (the Remove dialog's count). */
export function invitesCreatedBy(invites: readonly Invite[], creatorId: string): number {
  return invites.filter((invite) => invite.created_by?.user_id === creatorId).length;
}

/** Live reusable links someone other than `creatorId` made: what "Also revoke …" would revoke too. */
export function otherReusableInvites(invites: readonly Invite[], creatorId: string): number {
  return invites.filter((invite) => invite.reusable && invite.created_by?.user_id !== creatorId).length;
}

// --- Slice 6b-2b: the Danger zone ---------------------------------------------------------------------------

/**
 * Why Leave church is off (6b spec UX 2a): the owner must transfer first
 * ("owner_with_others") or, alone, delete the church ("owner_alone"); null
 * for an admin or a member, who may leave (the server still refuses the last
 * admin of a church with no owner, and that answer is toasted).
 */
export function leaveBlock(role: Church["role"], memberCount: number): "owner_with_others" | "owner_alone" | null {
  if (role !== "owner") return null;
  return memberCount > 1 ? "owner_with_others" : "owner_alone";
}

/**
 * Delete church's typed name (6b spec UX 2c): equal to the church's name once
 * both are trimmed, exactly, capitals included, as the server compares them.
 */
export function deleteNameMatches(typed: string, name: string): boolean {
  return typed.trim() === name.trim();
}

/** Who can become the owner (6b spec UX 2b): everyone else in the church, admins first, each in the list's order. */
export function transferCandidates(members: readonly Member[]): Member[] {
  const others = members.filter((m) => !m.is_me && m.role !== "owner");
  return [...others.filter((m) => m.role === "admin"), ...others.filter((m) => m.role !== "admin")];
}

/** A person in the New owner list: "{name} ({email})", or the email alone when there is no name. */
export function transferChoiceLabel(member: Member): string {
  const name = displayName(member);
  return name === member.email ? member.email : `${name} (${member.email})`;
}

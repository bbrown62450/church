/**
 * Builders for API payloads in tests. Each call returns a fresh object;
 * `overrides` replace top-level fields (pass a whole `user` to change it).
 */
import type {
  ChurchProfile,
  Hymn,
  Hymnals,
  InviteAccepted,
  InvitePreview,
  Lectionary,
  SuggestedHymn,
  Translations,
} from "@/lib/api/types";
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

/** `GET /church` for Grace (`ChurchProfileOut`, slices 2a and 3a): New York, WEB, GG2013. */
export function churchProfile(overrides: Partial<ChurchProfile> = {}): ChurchProfile {
  return {
    ...church(),
    timezone: "America/New_York",
    timezone_valid: true,
    bible_translation: null,
    effective_translation: "web",
    effective_translation_label: "World English Bible (WEB)",
    default_hymnal: null,
    effective_hymnal: "GG2013",
    ...overrides,
  };
}

/** Tuesday, September 29, 2026 at noon in New York: the next Sunday is October 4 (a first Sunday). */
export const DRAFT_NOW = new Date(Date.UTC(2026, 8, 29, 16, 0));

/** Pat's fresh draft for Grace at `DRAFT_NOW`, then `recipe` applied (the recipe may return a new object). */
export function testDraft(recipe: (d: DraftV1) => DraftV1 = (d) => d): DraftV1 {
  return recipe(freshDraft({ church: churchProfile(), user: { id: USER_ID }, now: DRAFT_NOW }));
}

/** A `GET /lectionary/readings` answer for `date` (the Isaiah and Easter lines from S `scripture_refs.py`). */
export function lectionary(date: string, overrides: Partial<Lectionary> = {}): Lectionary {
  return {
    date,
    status: "ok",
    partial: false,
    reading_sets: [
      {
        name: "Nineteenth Sunday after Pentecost",
        source: "merged",
        scriptures: ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"],
      },
      {
        name: "Resurrection of the Lord",
        source: "vanderbilt",
        scriptures: ["Acts 10:34-43", "Psalm 118:1-2, 14-24", "Colossians 3:1-4", "John 20:1-18"],
      },
    ],
    default_index: 0,
    ...overrides,
  };
}

// --- slice 2c: reference data and lookups for the Date & readings step ---------

/** `GET /translations` with ESV configured (production has the key): WEB, KJV and ESV. */
export function translations(overrides: Partial<Translations> = {}): Translations {
  return {
    default: "web",
    esv_available: true,
    items: [
      { id: "web", label: "World English Bible (WEB)" },
      { id: "kjv", label: "King James Version (KJV)" },
      { id: "esv", label: "English Standard Version (ESV)" },
    ],
    ...overrides,
  };
}

/** `GET /lectionary/readings` for a date with no readings (an ordinary weekday). */
export function noReadings(date: string): Lectionary {
  return lectionary(date, { status: "no_readings", reading_sets: [], default_index: null });
}

/** A fake-API handler for `GET /lectionary/readings` that answers each date with `answer(date)`. */
export function lectionaryRoute(answer: (date: string) => Lectionary = noReadings) {
  return (req: { path: string }) => answer(new URL(req.path, "http://localhost").searchParams.get("date") ?? "");
}

// --- slice 3b: hymns and hymnals ------------------------------------------------

/** A readable, valid hymn id: `hymnId(403)` is "00000000-0000-4000-8000-000000000403". */
export function hymnId(n: number): string {
  return `00000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
}

/** One `HymnOut` (slice 3a): #403 "Come, Thou Almighty King" in GG2013 unless overridden; the id follows the number. */
export function hymn(overrides: Partial<Hymn> = {}): Hymn {
  const number = overrides.number === undefined ? 403 : overrides.number;
  return {
    id: hymnId(number ?? 0),
    hymnal: "GG2013",
    title: "Come, Thou Almighty King",
    number,
    link: `https://hymnary.org/hymn/GG2013/${number ?? ""}`,
    scripture_refs: null,
    themes: [],
    recent_use_on: null,
    text_year: null,
    hymnal_count: null,
    newer_than_preferred: false,
    ...overrides,
  };
}

/** One `SuggestedHymnOut`: `hymn(overrides)` with `source` "ai" unless overridden. */
export function suggested(overrides: Partial<SuggestedHymn> = {}): SuggestedHymn {
  return { source: "ai", ...hymn(overrides), ...overrides };
}

/** `GET /hymnals` for Grace: GG2013 only (production, slice 3a record), no stored default. */
export function hymnals(overrides: Partial<Hymnals> = {}): Hymnals {
  return {
    items: [{ code: "GG2013", hymn_count: 853, scripture_ref_count: 795 }],
    default_hymnal: null,
    effective_hymnal: "GG2013",
    ...overrides,
  };
}

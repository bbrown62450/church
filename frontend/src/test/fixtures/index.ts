/**
 * Builders for API payloads in tests. Each call returns a fresh object;
 * `overrides` replace top-level fields (pass a whole `user` to change it).
 */
import type {
  BulletinImage,
  BulletinSettings,
  ChurchProfile,
  Contact,
  ContactList,
  GmailConnection,
  GenerateLiturgyBody,
  Hymn,
  HymnalSource,
  HymnalSources,
  HymnDetail,
  HymnMatch,
  Hymnals,
  HymnPage,
  HymnSuggestions,
  InviteAccepted,
  InvitePreview,
  Lectionary,
  LiturgyConfig,
  LiturgySection,
  OutlineItem,
  PreviousBulletin,
  ReviewBody,
  ReviewNote,
  ReviewResult,
  ReviseBody,
  ScriptureMatches,
  SectionError,
  SectionResult,
  ServiceBulletin,
  ServiceOut,
  ServicePage,
  ServiceSummary,
  SuggestedHymn,
  Translations,
} from "@/lib/api/types";
import type { Church, Me } from "@/lib/church";
import { freshDraft, type DraftV1 } from "@/lib/draft/schema";
import { DEFAULT_BENEDICTION_FALLBACK } from "@/lib/liturgy/defaults";
import { SECTION_LABELS } from "@/lib/liturgy/sections";

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

/** `GET /church` for Grace (`ChurchProfileOut`, slices 2a, 3a and 4a): New York, WEB, GG2013, the full Halverson benediction. */
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
    default_benediction: DEFAULT_BENEDICTION_FALLBACK, // what the API resolves an unset or "Halverson" default to
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

/**
 * Grace's GG2013 list as `GET /hymns?hymnal=GG2013&limit=2000` returns it, in
 * hymnal order: #403 (`hymn()`), two hymns with the same title, one newer than
 * the church prefers (#710, written 1981), one with no number (last), one
 * with a link that is not https (#650), and one with a blank title (never listed).
 */
export function gg2013(): Hymn[] {
  return [
    hymn({ number: 1, title: "Holy, Holy, Holy! Lord God Almighty", scripture_refs: "Revelation 4:8-11", text_year: 1826 }),
    hymn({ number: 35, title: "Praise, My Soul, the King of Heaven", link: null, scripture_refs: "Psalm 103", text_year: 1834 }),
    hymn(),
    hymn({ number: 649, title: "Amazing Grace", scripture_refs: "Ephesians 2:8", text_year: 1779 }),
    hymn({ number: 650, title: "Amazing Grace", link: "http://hymnary.org/text/amazing_grace", text_year: 1779 }),
    hymn({ number: 700, title: "Great Is Thy Faithfulness", scripture_refs: "Lamentations 3:22-23", text_year: 1923 }),
    hymn({ number: 710, title: "Here I Am, Lord", scripture_refs: "Isaiah 6:8", text_year: 1981, newer_than_preferred: true }),
    hymn({ number: 800, title: " " }),
    hymn({ id: hymnId(9999), number: null, title: "Sent Forth by God's Blessing", link: null, text_year: 1964 }),
  ];
}

/** Grace's PH1990 list: no scripture references, as in production's PH1990. */
export function ph1990(): Hymn[] {
  return [
    hymn({ id: hymnId(10_001), hymnal: "PH1990", number: 1, title: "Come, Thou Long-Expected Jesus", link: null }),
    hymn({ id: hymnId(10_276), hymnal: "PH1990", number: 276, title: "Great Is Thy Faithfulness", link: null }),
  ];
}

/** `GET /hymnals` with GG2013 and PH1990 (605 hymns, none with scripture references). */
export function twoHymnals(): Hymnals {
  return hymnals({
    items: [
      { code: "GG2013", hymn_count: 853, scripture_ref_count: 795 },
      { code: "PH1990", hymn_count: 605, scripture_ref_count: 0 },
    ],
  });
}

/**
 * A fake-API handler for `GET /hymns`: each hymnal's list from `lists`, and,
 * when `recent_for_date` is sent, `recent_use_on` from `recent` (title → date).
 */
export function hymnListRoute(
  lists: Record<string, Hymn[]> = { GG2013: gg2013(), PH1990: ph1990() },
  recent: Record<string, string> = {},
) {
  return (req: { path: string }): HymnPage => {
    const query = new URL(req.path, "http://localhost").searchParams;
    const dated = query.get("recent_for_date") !== null;
    const items = (lists[query.get("hymnal") ?? ""] ?? []).map((h) => ({
      ...h,
      recent_use_on: dated ? (recent[h.title] ?? null) : null,
    }));
    return { items, total: items.length, limit: Number(query.get("limit") ?? 50), offset: 0 };
  };
}

/** A `HymnMatchOut`: a hymn with its strength and the query references it matched. */
export function hymnMatch(h: Hymn, strength: HymnMatch["strength"], matched: string[]): HymnMatch {
  return { ...h, strength, matched_refs: matched };
}

/** `POST /hymns/scripture-matches` for the readings of October 4, 2026, unless overridden. */
export function scriptureMatches(overrides: Partial<ScriptureMatches> = {}): ScriptureMatches {
  const [holy, , come, grace, , , here] = gg2013();
  const items = [
    hymnMatch(here, "passage", ["Isaiah 5:1-7"]),
    hymnMatch(come, "chapter", ["Isaiah 5:1-7"]),
    hymnMatch(holy, "chapter", ["Matthew 21:33-46"]),
    hymnMatch(grace, "chapter", ["Philippians 3:4b-14"]),
  ];
  return {
    hymnal: "GG2013",
    refs_used: ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"],
    unparsed_refs: [],
    total_matched: items.length,
    items,
    ...overrides,
  };
}

/** `POST /hymns/suggestions`: each slot's hymns in order, all `source: "ai"`, unless overridden. */
export function hymnSuggestions(
  slots: Record<"opening" | "response" | "closing", Hymn[]>,
  overrides: Partial<HymnSuggestions> = {},
): HymnSuggestions {
  const out = (list: Hymn[]): SuggestedHymn[] => list.map((h) => suggested(h));
  return {
    hymnal: "GG2013",
    nt_ref: "Philippians 3:4b-14",
    nt_text_used: false,
    excluded_recent_count: 0,
    slots: { opening: out(slots.opening), response: out(slots.response), closing: out(slots.closing) },
    ...overrides,
  };
}

// --- slice 4b: the liturgy config and the generation answers --------------------

/**
 * `GET /liturgy/config` as 4a serves it (slice 4a record: 8 sections, 17
 * places, 16 outline items, `ai_available` true), with the communion text
 * shortened to its first seven blocks. `liturgy.test.tsx` pins the sections,
 * places and outline to the shared fixtures.
 */
export function liturgyConfig(overrides: Partial<LiturgyConfig> = {}): LiturgyConfig {
  const section = (
    key: LiturgySection["key"],
    label: string,
    hint: string | null = null,
    extra: Partial<LiturgySection> = {},
  ): LiturgySection => ({ key, label, default_enabled: true, rows: 4, pastor_copy_only: false, hint, ...extra });
  const landmark = (
    key: string,
    label: string,
    value_source: OutlineItem["value_source"],
    anchors: string[] = [key],
    fixed_text: string | null = null,
  ): OutlineItem => ({ kind: "landmark", key, label, value_source, fixed_text, anchors_after: anchors });
  const card = (key: string, label: string, anchors: string[] = [key]): OutlineItem => ({
    kind: "section",
    key,
    label,
    value_source: "none",
    fixed_text: null,
    anchors_after: anchors,
  });
  return {
    sections: [
      section("call_to_worship", "Call to Worship", "Start lines with “Leader:” or “People:”. People lines print in bold."),
      section("opening_prayer", "Opening Prayer"),
      section("prayer_of_confession", "Prayer of Confession", "Printed in bold for everyone to read together."),
      section("assurance", "Assurance of Pardon", "Added automatically after your text."),
      section("prayer_for_illumination", "Prayer for Illumination"),
      section("prayers_of_the_people", "Prayers of the People", null, { default_enabled: false, rows: 8, pastor_copy_only: true }),
      section("offertory_prayer", "Offertory Prayer"),
      section("benediction", "Benediction", "Your church's default benediction. Admins can change it in Settings."),
    ],
    custom_placements: [
      ["call_to_worship", "After Call to Worship"],
      ["opening_prayer", "After Opening Prayer"],
      ["first_hymn", "After First Hymn"],
      ["prayer_of_confession", "After Prayer of Confession"],
      ["assurance", "After Assurance of Pardon"],
      ["prayer_for_illumination", "After Prayer for Illumination"],
      ["ot_reading", "After First Reading"],
      ["nt_reading", "After New Testament Reading"],
      ["sermon", "After Sermon"],
      ["affirmation_of_faith", "After Affirmation of Faith"],
      ["second_hymn", "After Second Hymn"],
      ["communion", "After Communion"],
      ["prayers_of_the_people", "After Prayers of the People"],
      ["offertory_prayer", "After Offertory Prayer"],
      ["third_hymn", "After Third Hymn"],
      ["benediction", "Before Benediction"],
      ["end", "At the end (after Benediction)"],
    ].map(([key, label]) => ({ key, label })),
    outline: [
      card("call_to_worship", "Call to Worship"),
      card("opening_prayer", "Opening Prayer"),
      landmark("first_hymn", "First Hymn", "hymn_opening"),
      card("prayer_of_confession", "Prayer of Confession"),
      card("assurance", "Assurance of Pardon"),
      card("prayer_for_illumination", "Prayer for Illumination"),
      landmark("ot_reading", "First Reading", "reading_ot"),
      landmark("nt_reading", "New Testament Reading", "reading_nt"),
      landmark("sermon", "Sermon Title", "sermon_title"),
      landmark("affirmation_of_faith", "Affirmation of Faith", "fixed", ["affirmation_of_faith"], "Apostles' Creed"),
      landmark("second_hymn", "Second Hymn", "hymn_response"),
      {
        kind: "communion",
        key: "communion",
        label: "The Sacrament of the Lord's Supper",
        value_source: "none",
        fixed_text: null,
        anchors_after: ["communion"],
      },
      card("prayers_of_the_people", "Prayers of the People"),
      card("offertory_prayer", "Offertory Prayer"),
      landmark("third_hymn", "Third Hymn", "hymn_closing", ["third_hymn", "benediction"]),
      card("benediction", "Benediction", ["end"]),
    ],
    assurance_response: "People: Thanks be to God! Amen.",
    default_benediction_fallback: DEFAULT_BENEDICTION_FALLBACK,
    communion: {
      title: "The Sacrament of the Lord's Supper",
      toggle_label: "Include communion liturgy (The Sacrament of the Lord's Supper)",
      default_rule: "first_sunday_of_month",
      blocks: [
        { style: "heading1", text: "The Sacrament of the Lord's Supper" },
        { style: "blank", text: "" },
        { style: "heading2", text: "Invitation to the Table" },
        { style: "text", text: "This is the table of our Lord Jesus Christ." },
        { style: "heading2", text: "Great Thanksgiving" },
        { style: "text", text: "The Lord be with you." },
        { style: "response", text: "And also with you." },
      ],
    },
    limits: {
      max_section_text: 20_000,
      max_sermon_title: 300,
      max_custom_elements: 30,
      max_custom_label: 200,
      max_custom_text: 10_000,
      max_sections_per_request: 4,
    },
    ai_available: true,
    ...overrides,
  };
}

/** A section written by the AI (`status: "generated"`). */
export function sectionResult(section: SectionResult["section"], text: string): SectionResult {
  return { section, status: "generated", text, error: null };
}

/** A section's failure inside the 200 (`status: "error"`), with the server's message. */
export function sectionFailure(section: SectionResult["section"], code: SectionError["code"], message: string): SectionResult {
  return { section, status: "error", text: null, error: { code, message } };
}

/**
 * A fake-API handler for `POST /liturgy/generate`: `answer(section, body)`
 * gives the section's result (wrapped in `{results: [...]}`) or a whole
 * response (`fakeError(...)`); by default "{Label} written by the AI.".
 */
export function generateRoute(
  answer: (
    section: SectionResult["section"],
    body: GenerateLiturgyBody,
  ) => SectionResult | { status: number } | Promise<SectionResult | { status: number }> = (section) =>
    sectionResult(section, `${SECTION_LABELS[section]} written by the AI.`),
) {
  return async (req: { body: unknown }) => {
    const body = req.body as GenerateLiturgyBody;
    const out = await answer(body.sections[0], body);
    return "section" in out ? { results: [out] } : out;
  };
}

// --- the service reviewer: review and revise answers -------------------------------

/** One note as `POST /liturgy/review` returns it (an AI note unless `source` says "code"). */
export function reviewNote(tag: ReviewNote["tag"], text: string, source: ReviewNote["source"] = "ai"): ReviewNote {
  return { tag, text, source };
}

/** A review answer: by default the AI ran and found nothing. */
export function reviewResult(overrides: Partial<ReviewResult> = {}): ReviewResult {
  return { cards: [], service_notes: [], ai_status: "ok", ...overrides };
}

/**
 * A fake-API handler for `POST /liturgy/review`: `answer(body)` gives the
 * answer or a whole response (`fakeError(...)`); by default every card sent
 * comes back with no notes ("Looks good.").
 */
export function reviewRoute(
  answer: (body: ReviewBody) => ReviewResult | { status: number } | Promise<ReviewResult | { status: number }> = (body) =>
    reviewResult({ cards: body.cards.map((c) => ({ section: c.section, notes: [] })) }),
) {
  return async (req: { body: unknown }) => answer(req.body as ReviewBody);
}

/** A fake-API handler for `POST /liturgy/revise`: by default "{Label} revised with the notes.". */
export function reviseRoute(
  answer: (body: ReviseBody) => { text: string } | { status: number } | Promise<{ text: string } | { status: number }> = (body) => ({
    text: `${SECTION_LABELS[body.section]} revised with the notes.`,
  }),
) {
  return async (req: { body: unknown }) => answer(req.body as ReviseBody);
}

// --- slice 5a-3: saved services ---------------------------------------------------

export const SERVICE_ID = "55555555-5555-4555-8555-555555555555";

/**
 * `GET /services/{id}` (`ServiceOut`, slice 5a-2): Grace's October 4, 2026
 * service as Pat saved it on October 1 at 14:42 UTC: the Isaiah readings with
 * the Gospel picked, GG2013 #1 as the Opening hymn, an empty Response slot, a
 * Closing hymn no longer in the hymnal, two sections, communion, a sermon
 * title and an Anthem after the sermon.
 */
export function savedService(overrides: Partial<ServiceOut> = {}): ServiceOut {
  return {
    id: SERVICE_ID,
    service_date_iso: "2026-10-04",
    service_date: "October 04, 2026",
    occasion: "World Communion Sunday",
    scriptures: ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"],
    hymns: {
      opening: { hymn_id: hymnId(1), title: "Holy, Holy, Holy! Lord God Almighty", number: 1, hymnal: "GG2013", in_hymnal: true },
      response: null,
      closing: { hymn_id: null, title: "Old Favorite", number: 12, hymnal: "PH1990", in_hymnal: false },
    },
    hymnal: "GG2013",
    liturgy: { call_to_worship: "Leader: Come. People: We come.", benediction: "Go in peace." },
    sermon_title: "Living Water",
    selected_ot_ref: "",
    selected_nt_ref: "Matthew 21:33-46",
    include_communion: true,
    custom_elements: [{ label: "Anthem", text: "Choir", insert_after: "sermon" }],
    bulletin: serviceBulletin(),
    created_by: { id: USER_ID, name: "Pat Pastor" },
    saved_at: "2026-10-01T14:42:00.123456+00:00",
    ...overrides,
  };
}

/** A service's bulletin fields (printed bulletin PR 2b) with nothing filled in (no picture, as the API answers since PR 3a), unless overridden. */
export function serviceBulletin(overrides: Partial<ServiceBulletin> = {}): ServiceBulletin {
  return {
    prelude: { title: "", composer: "" },
    postlude: { title: "", composer: "" },
    people: { worship_leader: null, liturgist: null, organist: null },
    leaders: {},
    announcements: { ushers: "", deacon: "", coffee_hour: "", activities: "", prayer_concerns: "", collection: "", other: "" },
    reading_text: { ot: "", nt: "" },
    unchecked: [],
    cover_image_id: null,
    ...overrides,
  };
}

/** `GET /services/previous-bulletin` (printed bulletin PR 2b): no service before the date, unless overridden. */
export function previousBulletin(overrides: Partial<PreviousBulletin> = {}): PreviousBulletin {
  return { service_id: null, service_date_iso: null, bulletin: serviceBulletin(), ...overrides };
}

/** An uploaded cover picture (`POST /bulletin-images`, printed bulletin PR 3a), unless overridden. */
export function bulletinImage(overrides: Partial<BulletinImage> = {}): BulletinImage {
  return { id: "0b4c2b0e-1111-4222-8333-444455556666", width: 1600, height: 1200, ...overrides };
}

/** One row of `GET /services` (`ServiceSummary`): `savedService()`'s, unless overridden. */
export function serviceSummary(overrides: Partial<ServiceSummary> = {}): ServiceSummary {
  const s = savedService();
  return {
    id: s.id,
    service_date_iso: s.service_date_iso,
    service_date: s.service_date,
    occasion: s.occasion,
    sermon_title: s.sermon_title,
    saved_at: s.saved_at,
    created_by: s.created_by,
    ...overrides,
  };
}

/** A page of `GET /services`. */
export function servicePage(items: ServiceSummary[], overrides: Partial<ServicePage> = {}): ServicePage {
  return { items, total: items.length, limit: 20, offset: 0, ...overrides };
}

/** The Gloria Patri's traditional words (`bulletin_settings.GLORIA_PATRI`). */
export const GLORIA_PATRI =
  "Glory be to the Father, and to the Son, and to the Holy Ghost; as it was in the beginning, is now, and ever shall be, world without end. Amen, amen.";

/**
 * `GET /church/bulletin-settings` (printed bulletin PR 2a) for a church that
 * never saved them: the server's defaults, unless overridden.
 */
export function bulletinSettings(overrides: Partial<BulletinSettings> = {}): BulletinSettings {
  return {
    address_lines: [],
    phone: "",
    email: "",
    website: "",
    facebook: "",
    service_time: "",
    worship_leader: "",
    liturgist: "",
    organist: "",
    stand_note: "Congregation stands if able",
    gloria_patri_words: GLORIA_PATRI,
    starred: ["first_hymn", "gloria_patri", "affirmation_of_faith", "second_hymn", "doxology", "third_hymn", "benediction"],
    leaders: {
      prelude: "organist",
      welcome: "liturgist",
      call_to_worship: "liturgist",
      opening_prayer: "liturgist",
      prayer_of_confession: "liturgist",
      assurance: "liturgist",
      prayer_for_illumination: "liturgist",
      ot_reading: "liturgist",
      nt_reading: "worship_leader",
      sermon: "worship_leader",
      prayers_of_the_people: "worship_leader",
      offertory_prayer: "worship_leader",
      postlude: "organist",
    },
    ...overrides,
  };
}

/** Every standing field filled in (invented details). */
export function filledBulletinSettings(overrides: Partial<BulletinSettings> = {}): BulletinSettings {
  return bulletinSettings({
    address_lines: ["100 Example Street", "Springfield, ST 00000"],
    phone: "(555) 010-0100",
    email: "office@example.com",
    website: "example.com",
    facebook: "Example Church",
    service_time: "10:30 a.m.",
    worship_leader: "Rev. Alex Example",
    liturgist: "Sam Sample",
    organist: "Jordan Doe",
    ...overrides,
  });
}

// --- slice 5b-1: contacts -------------------------------------------------------------------------

/** One of Grace's contacts (`ContactOut`): Mary Jones at an example address, which passes the check. */
export function contact(overrides: Partial<Contact> = {}): Contact {
  return {
    id: "6c0b5e1a-1d2b-4c3d-8e4f-5a6b7c8d9e01",
    name: "Mary Jones",
    email: "mary@example.org",
    email_valid: true,
    ...overrides,
  };
}

/** `GET /contacts`: Mary Jones, then the church office, which has no name. */
export function contactList(items: Contact[] = [
  contact(),
  contact({ id: "6c0b5e1a-1d2b-4c3d-8e4f-5a6b7c8d9e02", name: null, email: "office@example.org" }),
]): ContactList {
  return { items };
}

// --- slice 5b-2: the Gmail connection --------------------------------------------------------------

/** `GET /gmail-connection`: set up here and connected as Pat, unless overridden. */
export function gmailConnection(overrides: Partial<GmailConnection> = {}): GmailConnection {
  return { configured: true, connected: true, google_email: "pat@example.com", ...overrides };
}

/** Not connected yet (set up here). */
export function gmailDisconnected(): GmailConnection {
  return gmailConnection({ connected: false, google_email: null });
}

// --- slice 6a-2: Settings → Hymns ------------------------------------------------------------------

/** One hymn as `POST`/`PATCH /hymns` answer it (`HymnDetailOut`): `hymn(overrides)` with its stored theme text. */
export function hymnDetail(overrides: Partial<HymnDetail> = {}): HymnDetail {
  const h = hymn();
  return {
    id: h.id,
    hymnal: h.hymnal,
    title: h.title,
    number: h.number,
    scripture_refs: h.scripture_refs,
    theme: null,
    link: h.link,
    text_year: null,
    hymnal_count: null,
    ...overrides,
  };
}

/** One bundled hymnal (`HymnalSourceOut`): PH1990, not yet added, unless overridden. */
export function hymnalSource(overrides: Partial<HymnalSource> = {}): HymnalSource {
  return {
    code: "PH1990",
    label: "The Presbyterian Hymnal (1990)",
    hymn_count: 605,
    has_scripture_refs: false,
    present: false,
    ...overrides,
  };
}

/** `GET /hymnal-sources` for Grace: GG2013 (which Grace has) and PH1990 (which it has not). */
export function hymnalSources(items: HymnalSource[] = [
  hymnalSource({ code: "GG2013", label: "Glory to God (2013)", hymn_count: 853, has_scripture_refs: true, present: true }),
  hymnalSource(),
]): HymnalSources {
  return { items };
}

/**
 * App-facing names for the generated API types (F §1.11). schema.d.ts is
 * generated from openapi.json by `npm run gen:api`; never edit it by hand.
 */
import type { components } from "./schema";

export type Church = components["schemas"]["ChurchOut"];
export type Me = components["schemas"]["MeOut"];
export type ErrorBody = components["schemas"]["ErrorBody"];

/** `POST /invites/preview` (1b): what the invite offers. No church id: that comes with the accept. */
export type InvitePreview = components["schemas"]["InvitePreviewOut"];
/** `POST /invites/accept` (1b): the church (with the caller's role), and the toast text. */
export type InviteAccepted = components["schemas"]["InviteAcceptOut"];
/**
 * `POST /churches`'s body (1b). The schema gives both fields a "" default (a
 * missing field is the same 422 as a blank one); the app always sends both, so
 * the idempotency fingerprint of a body never depends on a left-out field.
 */
export type CreateChurchBody = Required<components["schemas"]["CreateChurchIn"]>;

/** `GET /church` (slice 2a): `ChurchOut` plus the profile fields. `/me`'s church items stay `Church`. */
export type ChurchProfile = components["schemas"]["ChurchProfileOut"];
/** `GET /lectionary/readings?date=` (slice 2a): the reading sets for exactly that date. */
export type Lectionary = components["schemas"]["LectionaryOut"];
export type ReadingSet = components["schemas"]["ReadingSetOut"];
/** `GET /translations` (slice 2a). */
export type Translations = components["schemas"]["TranslationsOut"];
/** `POST /scripture/passages` (slice 2a): one passage per ref sent, each with a section per " or " alternative. */
export type Passages = components["schemas"]["PassagesOut"];
export type Passage = components["schemas"]["PassageOut"];
export type PassageSection = components["schemas"]["PassageSectionOut"];

/** `GET /hymnals` (slice 3a): the church's hymnals with counts, the stored default and the effective one. */
export type Hymnals = components["schemas"]["HymnalListOut"];
export type HymnalSummary = components["schemas"]["HymnalOut"];
/** One hymn as every hymn route returns it (`HymnOut`, slice 3a). */
export type Hymn = components["schemas"]["HymnOut"];
/** `GET /hymns` (slice 3a): one page of hymns. */
export type HymnPage = components["schemas"]["Page_HymnOut_"];
/** `POST /hymns/scripture-matches` (slice 3a): the request body and the answer. */
export type ScriptureMatchBody = components["schemas"]["ScriptureMatchIn"];
export type ScriptureMatches = components["schemas"]["ScriptureMatchesOut"];
export type HymnMatch = components["schemas"]["HymnMatchOut"];
/** `POST /hymns/suggestions` (slice 3a): the request body and the answer. */
export type HymnSuggestionBody = components["schemas"]["HymnSuggestionIn"];
export type HymnSuggestions = components["schemas"]["HymnSuggestionsOut"];
export type SuggestedHymn = components["schemas"]["SuggestedHymnOut"];

/** `GET /liturgy/config` (slice 4a): the sections, custom places, order of worship, communion text, limits and `ai_available`. */
export type LiturgyConfig = components["schemas"]["LiturgyConfigOut"];
export type LiturgySection = components["schemas"]["SectionSpecOut"];
export type OutlineItem = components["schemas"]["OutlineItemOut"];
export type CommunionBlock = components["schemas"]["CommunionBlockOut"];
/** `POST /liturgy/generate` (slice 4a): the body the step sends (one section, no overrides) and the answer. */
export type GenerateLiturgyBody = components["schemas"]["GenerateLiturgyIn"];
export type GenerateLiturgyResult = components["schemas"]["GenerateLiturgyOut"];
export type SectionResult = components["schemas"]["SectionResult"];
/** A section's failure inside the 200 (the declared deviation from F §1.5). */
export type SectionError = components["schemas"]["SectionError"];
/** The effective NT reading and its text, never ESV (shared with the reviewer's routes). */
export type SermonText = components["schemas"]["SermonText"];
export type HymnRef = components["schemas"]["HymnRef"];

/**
 * `/services` (slice 5a-2): a saved service as the builder opens it (`GET`,
 * `POST`, `PUT`), one saved slot's hymn, one row of the list, a page of rows,
 * and the answer to a delete.
 */
export type ServiceOut = components["schemas"]["ServiceOut"];
export type ArchivedHymn = components["schemas"]["ArchivedHymn"];
export type ServiceSummary = components["schemas"]["ServiceSummary"];
export type ServicePage = components["schemas"]["Page_ServiceSummary_"];
export type DeletedOut = components["schemas"]["DeletedOut"];
/**
 * A service's printed-bulletin fields (printed bulletin PR 2b): the music, this
 * week's people and part leaders, the announcements and the pasted reading
 * text; and `GET /services/previous-bulletin`, what a new week carries forward.
 */
export type ServiceBulletin = components["schemas"]["ServiceBulletin"];
export type PreviousBulletin = components["schemas"]["PreviousBulletinOut"];
/** `POST /bulletin-images` (printed bulletin PR 3a): an uploaded cover picture as stored; its id goes in `cover_image_id`. */
export type BulletinImage = components["schemas"]["BulletinImageOut"];

/** `POST /liturgy/review` (the service reviewer): every switched-on card with text, and the notes back. */
export type ReviewBody = components["schemas"]["ReviewIn"];
export type ReviewCardBody = components["schemas"]["ReviewCardIn"];
export type ReviewResult = components["schemas"]["ReviewOut"];
export type ReviewNote = components["schemas"]["NoteOut"];
/** Why the AI part of a review is missing ("ok" when it ran): a field, not an error code (F §1.5). */
export type AiStatus = ReviewResult["ai_status"];
/** `POST /liturgy/revise` (the service reviewer): one AI card's text and its remaining notes; the revised text. */
export type ReviseBody = components["schemas"]["ReviseIn"];
export type ReviseResult = components["schemas"]["ReviseOut"];

/** `GET`/`PUT /church/bulletin-settings` (printed bulletin PR 2a): the church's standing bulletin settings. */
export type BulletinSettings = components["schemas"]["BulletinSettings"];

/** `GET /voices` (Voices of the Church V1): the Catena Aurea's sections on a Gospel passage, as printed. */
export type Voices = components["schemas"]["VoicesOut"];
export type VoiceSection = components["schemas"]["VoiceSectionOut"];
export type VoiceComment = components["schemas"]["VoiceCommentOut"];

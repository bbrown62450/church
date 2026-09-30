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

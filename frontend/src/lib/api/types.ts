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

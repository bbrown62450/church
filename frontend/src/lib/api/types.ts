/**
 * App-facing names for the generated API types (F §1.11). schema.d.ts is
 * generated from openapi.json by `npm run gen:api`; never edit it by hand.
 */
import type { components } from "./schema";

export type Church = components["schemas"]["ChurchOut"];
export type Me = components["schemas"]["MeOut"];
export type ErrorBody = components["schemas"]["ErrorBody"];

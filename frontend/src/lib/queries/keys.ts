/**
 * The query key factory (F §4.4). Every church-scoped key starts with
 * ["church", churchId], so a church switch can cancel and remove all of one
 * church's queries with the prefix `keys.church(oldId)`, and `handleAuthErrors`
 * reads the church id from the key's second element. Later slices only add entries.
 */
export const keys = {
  me: () => ["me"] as const,
  translations: () => ["ref", "translations"] as const,
  liturgyConfig: () => ["ref", "liturgy-config"] as const,
  lectionary: (dateIso: string) => ["lectionary", dateIso] as const,
  passage: (translation: string, ref: string) => ["passage", translation, ref] as const,
  gmailConnection: () => ["gmail-connection"] as const,

  /** Prefix of every key below: cancel or remove a whole church with it. */
  church: (id: string) => ["church", id] as const,
  churchProfile: (id: string) => ["church", id, "profile"] as const,
  hymns: (id: string, params: object) => ["church", id, "hymns", params] as const,
  /** Under the hymns prefix, so a hymn change (6a) refreshes the matches too (slice 3 S Queries). */
  hymnMatches: (id: string, params: object) => ["church", id, "hymns", "matches", params] as const,
  hymnals: (id: string) => ["church", id, "hymnals"] as const,
  hymnalSources: (id: string) => ["church", id, "hymnal-sources"] as const,
  services: (id: string, params: object) => ["church", id, "services", params] as const,
  service: (id: string, serviceId: string) => ["church", id, "service", serviceId] as const,
  /** Under the services prefix, so a save or a delete (which refresh it) changes what carries forward (PR 2b). */
  previousBulletin: (id: string, dateIso: string) => ["church", id, "services", "previous-bulletin", dateIso] as const,
  contacts: (id: string) => ["church", id, "contacts"] as const,
  members: (id: string) => ["church", id, "members"] as const,
  invites: (id: string) => ["church", id, "invites"] as const,
  liturgyPrompts: (id: string) => ["church", id, "liturgy-prompts"] as const,
  rubric: (id: string) => ["church", id, "rubric"] as const,
  prayerLibrary: (id: string) => ["church", id, "prayer-library"] as const,
  bulletinSettings: (id: string) => ["church", id, "bulletin-settings"] as const,
};

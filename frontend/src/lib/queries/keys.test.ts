import { describe, expect, it } from "vitest";

import { keys } from "./keys";

describe("keys", () => {
  it("builds the user-level and reference keys of F §4.4", () => {
    expect(keys.me()).toEqual(["me"]);
    expect(keys.translations()).toEqual(["ref", "translations"]);
    expect(keys.liturgyConfig()).toEqual(["ref", "liturgy-config"]);
    expect(keys.lectionary("2026-10-04")).toEqual(["lectionary", "2026-10-04"]);
    expect(keys.passage("NRSVUE", "John 3:16")).toEqual(["passage", "NRSVUE", "John 3:16"]);
    expect(keys.gmailConnection()).toEqual(["gmail-connection"]);
  });

  it("starts every church-scoped key with ['church', id]", () => {
    const id = "c-1";
    const churchKeys: ReadonlyArray<readonly unknown[]> = [
      keys.church(id),
      keys.churchProfile(id),
      keys.hymns(id, { q: "grace" }),
      keys.hymnMatches(id, { refs: ["Mark 1"] }),
      keys.hymnals(id),
      keys.hymnalSources(id),
      keys.services(id, { page: 1 }),
      keys.service(id, "s-9"),
      keys.contacts(id),
      keys.members(id),
      keys.invites(id),
      keys.liturgyPrompts(id),
      keys.rubric(id),
      keys.prayerLibrary(id),
      keys.bulletinSettings(id),
      keys.previousBulletin(id, "2026-10-11"),
    ];
    expect(churchKeys.map((key) => key.slice(0, 2))).toEqual(churchKeys.map(() => ["church", id]));
    expect(churchKeys.map((key) => key.slice(2))).toEqual([
      [],
      ["profile"],
      ["hymns", { q: "grace" }],
      ["hymns", "matches", { refs: ["Mark 1"] }],
      ["hymnals"],
      ["hymnal-sources"],
      ["services", { page: 1 }],
      ["service", "s-9"],
      ["contacts"],
      ["members"],
      ["invites"],
      ["liturgy-prompts"],
      ["rubric"],
      ["prayer-library"],
      ["bulletin-settings"],
      ["services", "previous-bulletin", "2026-10-11"], // under the services prefix: a save refreshes it (PR 2b)
    ]);
  });
});

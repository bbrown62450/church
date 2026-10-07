/**
 * The Settings area's pages, in the nav's order (6a spec "Settings nav"; slice
 * 6a-1). `/settings` opens the first. 6a-2 adds Hymns; 6a-3 Liturgy prompts,
 * Prayers and Rubric, and moves Bulletin settings in (its entry then points
 * under /settings); 5b-1 adds Contacts (the final order puts it after every
 * page about the church's services) and 5b-2 Account after it (6b's People
 * will go between them).
 */
export const SETTINGS_SECTIONS = [
  { href: "/settings/church", label: "Church" },
  { href: "/bulletin-settings", label: "Bulletin" },
  { href: "/settings/contacts", label: "Contacts" },
  { href: "/settings/account", label: "Account" },
] as const;

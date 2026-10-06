/**
 * The Settings area's pages, in the nav's order (6a spec "Settings nav"; slice
 * 6a-1). `/settings` opens the first. 6a-2 adds Hymns; 6a-3 Liturgy prompts,
 * Prayers and Rubric, and moves Bulletin settings in (its entry then points
 * under /settings); 5b adds Account and Contacts.
 */
export const SETTINGS_SECTIONS = [
  { href: "/settings/church", label: "Church" },
  { href: "/bulletin-settings", label: "Bulletin" },
] as const;

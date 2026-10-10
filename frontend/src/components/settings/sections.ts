/**
 * The Settings area's pages, in the nav's order (6a spec "Settings nav"; slice
 * 6a-1). `/settings` opens the first. 6a-2 added Hymns after Church; 6a-3a
 * added Liturgy (the prompts) and Rubric and moved Bulletin settings in under
 * /settings; 6a-3b puts Prayers between Liturgy and Rubric, the order the
 * owner's 6a-3 answers of 2026-10-07 set for once 6a is done (Church, Hymns,
 * Liturgy, Prayers, Rubric, Bulletin, Contacts, Account); 5b-1 added Contacts
 * and 5b-2 Account after it; 6b-2a puts People between them (the owner's 6b
 * answers of 2026-10-09: Church, Hymns, Liturgy, Prayers, Rubric, Bulletin,
 * Contacts, People, Account, then 6b-2b's Danger zone); 6b-2b adds Danger
 * zone last, so the nav is in its final order.
 */
export const SETTINGS_SECTIONS = [
  { href: "/settings/church", label: "Church" },
  { href: "/settings/hymns", label: "Hymns" },
  { href: "/settings/liturgy", label: "Liturgy" },
  { href: "/settings/prayers", label: "Prayers" },
  { href: "/settings/rubric", label: "Rubric" },
  { href: "/settings/bulletin", label: "Bulletin" },
  { href: "/settings/contacts", label: "Contacts" },
  { href: "/settings/people", label: "People" },
  { href: "/settings/account", label: "Account" },
  { href: "/settings/danger", label: "Danger zone" },
] as const;

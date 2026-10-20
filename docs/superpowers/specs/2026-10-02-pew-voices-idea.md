# Hear it from the pews: owner idea (pre-spec)

Status: idea only, not a spec. Owner, 2026-10-02.

A second kind of review beside "Review service": a few personas from the
pews react to the whole service, so the pastor hears how the prayers land
for different people. The owner's examples: someone very conservative but
sharply intelligent, a teenager, a man who rarely comes to church, parents of
busy young kids, someone deeply worried about their health. The aim is a
well-rounded approach to prayer writing.

## Owner answers so far (2026-10-02)

1. A separate button, not part of Review service.
2. The personas are editable by the church's members (in Settings).
3. A persona's reaction can be used with Revise.
4. Placement: after 6a (owner, 2026-10-02). Order: 5a-3, the printed bulletin, (Voices of the Church, dropped 2026-10-05), 6a (which adds a place in Settings to edit the personas), then this.

## Notes for the planning round

- One AI request for all personas, like Review service; each gives one or two
  short reactions to the whole service, each able to point at a prayer.
- Its own panel, not mixed with the reviewer's notes.
- Guard against caricature and against flattery (only what did not land, or
  what helped).

## Owner's planning answers (2026-10-20, "all recommended"; binding)

1. One PR: persona storage, Settings editing, the AI request, the builder button and panel. No migration (personas live in `churches.settings`, like the prayer library). Split only if the plan comes out unusually large.
2. Settings: a "From the pews" section on the existing Prayers page, under the voice profile. No new nav item.
3. Admins (and the owner) edit the personas; every member reads them (supersedes "editable by the church's members" above).
4. Every church starts with the owner's five, as short descriptions with no invented first names: "Sharp, very conservative, reads every word"; "A teenager"; "A man who rarely comes to church"; "Parents of busy young kids"; "Someone deeply worried about their health". Admins can edit, turn off or add; at most 6 turned on; each description about 300 characters at most.
5. One AI request for all turned-on personas, like Review service. Each persona gives one or two short reactions to the whole service; a reaction may point at one prayer; only what did not land or what helped; no flattery, no caricature; the personas are not real people; the health persona reacts as a worshipper and never gives medical advice. Shown in a "From the pews" panel at the top of the liturgy step, separate from the reviewer's notes; client memory only; a reaction clears when its prayer's text changes.
6. A reaction that points at a prayer has "Revise with this", under today's Revise rules (Undo kept; asks before replacing the member's own text).
7. Same AI model (OPENAI_MODEL) and the same `ai` rate-limit bucket as Review service; one request per tap; "Still working" and Cancel as on Review. Measure the real cost in the plan. Keep the process lean: one plan agent, one plan review, one code review.

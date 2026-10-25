# Upstream test fixtures

Recorded or hand-built answers from the four upstreams the lectionary and
passage code calls. Tests replay them with respx or `httpx.MockTransport`
(`backend/tests/upstream_fixtures.py`); no test touches the network.

Each fixture is a body file plus `<name>.meta.json`:
`{"status", "content_type", "url", "recorded_at", "synthetic"}`.
The Vanderbilt year files are trimmed to the fixture dates (preamble, header
and file order kept; each kept row verbatim).

`shared/` holds the hand-written Python/TypeScript cases (not recorded).

This file is rewritten by the recorder. To refresh the fixtures (network;
owner's permission; never in CI), from the repo root:

    .venv/bin/python backend/scripts/record_fixtures.py

and for any fixture it reports as FAIL, the hand-built version:

    .venv/bin/python backend/scripts/record_fixtures.py --synthetic <kind/name>

| Fixture | Status | Content-Type | Made |
|---|---|---|---|
| `bible_api/isaiah_50_4-9` | 200 | `application/json; charset=utf-8` | synthetic |
| `bible_api/isaiah_50_4-9a` | 404 | `application/json; charset=utf-8` | synthetic |
| `bible_api/luke_2_1-14_15-20` | 200 | `application/json; charset=utf-8` | synthetic |
| `esv/empty` | 200 | `application/json; charset=utf-8` | synthetic |
| `esv/success` | 200 | `application/json; charset=utf-8` | synthetic |
| `lectio/2025-12-24` | 200 | `application/json; charset=utf-8` | synthetic |
| `lectio/2025-12-25` | 200 | `application/json; charset=utf-8` | synthetic |
| `lectio/2026-01-01` | 404 | `application/json; charset=utf-8` | synthetic |
| `lectio/2026-02-18` | 200 | `application/json; charset=utf-8` | synthetic |
| `lectio/2026-03-29` | 200 | `application/json; charset=utf-8` | synthetic |
| `lectio/2026-04-03` | 404 | `application/json; charset=utf-8` | synthetic |
| `lectio/2026-04-05` | 200 | `application/json; charset=utf-8` | synthetic |
| `lectio/2026-05-14` | 200 | `application/json; charset=utf-8` | synthetic |
| `lectio/2026-05-31` | 200 | `application/json; charset=utf-8` | synthetic |
| `lectio/2026-09-29` | 404 | `application/json; charset=utf-8` | synthetic |
| `lectio/2026-10-04` | 200 | `application/json; charset=utf-8` | synthetic |
| `lectio/2026-11-01` | 200 | `application/json; charset=utf-8` | synthetic |
| `lectio/2026-11-26` | 404 | `application/json; charset=utf-8` | synthetic |
| `lectio/error_500` | 500 | `application/json; charset=utf-8` | synthetic |
| `lectio/html_200` | 200 | `text/html; charset=utf-8` | synthetic |
| `vanderbilt/2025-26` | 200 | `text/csv; charset=utf-8` | synthetic |
| `vanderbilt/2026-27` | 200 | `text/csv; charset=utf-8` | synthetic |
| `vanderbilt/2027-28` | 200 | `text/csv; charset=utf-8` | synthetic |
| `vanderbilt/404` | 404 | `text/html; charset=utf-8` | synthetic |
| `vanderbilt/html_200` | 200 | `text/html; charset=utf-8` | synthetic |

## shared/

- `shared/scripture_refs.json` is hand-written, not recorded, so it has no `.meta.json` sidecar. It is the authority for `backend/scripture_refs.py` and for 2b's `frontend/src/lib/scripture-refs.ts`: change a case here first, then both ports. `backend/tests/test_scripture_refs.py` runs it in pytest; 2b's `lib/scripture-refs.test.ts` reads it with `fs` from `../backend/tests/fixtures/shared/`. The top-level `"_about"` key documents each section's encoding. Slice 5a adds its `doc_readings` cases to the `resolve_readings` section.
- `shared/formatting.json` is hand-written too (formatting spec, 2026-10-25): each case is a box's text and the lines the printed bulletin prints for it. It is the authority for `backend/formatting.py` with `backend/printed_bulletin.py` and for `frontend/src/lib/formatting.ts` (the Review step's preview): change a case here first, then both. `backend/tests/test_formatting.py` and `frontend/src/lib/formatting.test.ts` run every case.
- `shared/formatting_fuzz.json` is generated, not hand-written: 300 seeded random texts (marks, spaces of every kind, labels and word characters) and the lines the printed bulletin prints for each, in `formatting.json`'s form. `backend/tests/test_formatting.py` regenerates it from the seed and fails if the file differs (rewrite it with `cd backend && ../.venv/bin/python -c "import tests.test_formatting as t; t.write_fuzz_fixture()"` after a deliberate change, and read the diff); `frontend/src/lib/formatting.test.ts` checks every case, so the preview cannot drift from print on text no one wrote a case for.

# Service Rubric: Design

Date: 2026-09-25
Status: approved; implemented on branch claude/liturgy-writing-improvements-22ed17

## Why

Beau's cohort suggested three improvements to how the app builds a service:

1. **A rubric**: a written definition of a good service (hymn roles, and what
   makes each prayer good).
2. **A prayer library**: Beau's own prayers, so the writer learns Beau's voice.
3. **An adversarial reviewer**: a second AI that critiques each draft against
   the rubric and the library, followed by a revision.

They build on each other, so they ship in that order, each with its own
spec → plan → build cycle. **This spec covers only the rubric.**

## Scope

The rubric is built **behind the scenes now**: storage, defaults, API, hymn
data, and the code that feeds it to the AI. The screens that use it arrive
with the migration slices that own those screens (see
`2026-09-25-react-fastapi-migration-design.md`):

- slice 3 (hymns): show the year label on suggested hymns
- slice 4 (liturgy): nothing new; the writer already uses the rubric
- slice 6 (settings): the rubric editor

The Streamlit app gets no new screens. Because it calls the same backend code,
its hymn picks and liturgy start following the rubric too; Beau approved this.

Out of scope: the prayer library, the reviewer, per-hymn manual editing of
year and familiarity (a slice 6 hymn-settings concern), and changing the AI
model.

## The rubric

A rubric has four parts:

| Part | Type | Default |
|---|---|---|
| `hymns` | a checklist per hymn slot: `opening`, `response`, `closing` | below |
| `prayers` | a checklist per liturgy section (the 8 keys in `liturgy_prompts.SECTION_ORDER`) | below |
| `prefer_before_year` | integer | `1970` |
| `prefer_familiar` | boolean | `true` |

A checklist is a list of short strings. The checklists describe quality. The
existing per-section prompts keep describing format (Leader/People lines,
length, "End with Amen"). The two stay separate so the future reviewer can
grade a draft item by item.

`prefer_before_year` and `prefer_familiar` are preferences, not filters. Older
and familiar hymns rank first, but a newer hymn may still be suggested when it
fits clearly better.

### Default checklists (approved one by one)

**Opening (Gathering) Hymn.** A good opening hymn:
- gathers and welcomes people into worship
- turns attention toward God in praise, not toward the sermon topic
- is strong and confident, not quiet or reflective
- fits the season when possible (for example, an Advent hymn in Advent)

**Response Hymn (after the sermon).** A good response hymn:
- reinforces the central message of the sermon, which is usually the New Testament reading
- gives the congregation a way to respond, such as commitment, trust or prayer
- may be more reflective than the opening or closing hymn
- connects to the reading's main theme, not just a single word that appears in it

**Closing (Sending) Hymn.** A good closing hymn:
- is joyful and upbeat
- sends people out to serve others and share God's love
- looks outward to the world, not inward
- ends the service on a note of hope

**Call to Worship.** A good Call to Worship:
- calls the people together to worship God
- keeps the People's lines short and easy to say together
- builds toward praise, ending with a strong People response
- hints at the day's themes without citing scripture

**Opening Prayer.** A good opening prayer:
- follows the classic collect shape
- addresses God
- names something God has done or is ("who…")
- asks for one thing that fits the day
- says why ("so that…")
- closes through Christ, then "Amen"

**Prayer of Confession.** A good confession:
- names real, specific failings that are common to all people, not vague "we have fallen short"
- connects to the themes of the New Testament reading (the sermon text), without citing it
- includes sins of omission (what we failed to do) as well as commission
- stays in "we," as one congregation confessing together
- is honest without piling on shame
- turns toward God's mercy at the end

**Assurance of Pardon.** A good assurance:
- declares forgiveness as a sure fact ("In Jesus Christ, we are forgiven"), not a wish ("may God forgive us")
- is grounded in God's grace in Christ
- answers the confession by echoing its theme
- is brief and joyful

**Prayer for Illumination.** A good prayer for illumination:
- asks the Holy Spirit to open hearts and minds to the Word
- asks that we both hear and respond, not just understand
- makes room for the preacher's words to be God's word for today
- is no more than 3 sentences, and quiets the room before the reading

**Prayers of the People.** A good Prayers of the People:
- moves outward to inward: world, church, community, then ourselves
- names concrete needs (refugees, the grieving, people without work), not just "all who suffer"
- makes room for the congregation's joys and concerns, and a time of silence
- is unhurried but not wordy, with each petition saying one thing
- leads naturally into the Lord's Prayer

**Offertory Prayer.** A good offertory prayer:
- thanks God as the giver of everything we have
- dedicates both our gifts and ourselves to God's work
- names, even briefly, what the gifts will do in the world
- is no more than 3 sentences

**Benediction.** A good benediction:
- speaks a blessing to the people ("May God go with you…"), rather than praying to God
- sends them out to serve and share God's love
- may name the Trinity
- is 1 to 3 sentences, confident and easy to remember

### Default prompt changes

Two default section prompts in `liturgy_prompts.py` change so that they agree
with their checklists:

- `prayer_for_illumination`: "Write 3-5 sentences" → "Write no more than 3 sentences"
- `offertory_prayer`: "Three to five sentences" → "No more than three sentences"

## Storage

A new module, `backend/service_rubric.py`, holds `DEFAULT_RUBRIC` and the merge
logic, following `liturgy_prompts.py`:

- `default_rubric() -> dict`: a deep copy of the defaults.
- `merge_rubric(overrides) -> dict`: the defaults with any valid overrides
  applied, ignoring unknown keys and invalid values.
- `validate_patch(patch) -> dict`: rejects unknown keys and bad values, and
  raises `ValueError` with a readable message.

Each church stores **only its overrides** in `churches.settings["rubric"]`,
with the same shape as the rubric but sparse. For example:
`{"hymns": {"closing": [...]}, "prefer_before_year": 1960}`. A church that never
edits anything gets future improvements to the defaults automatically.

Repo functions in `repos/churches.py`, alongside `get_church_prompts`:

- `get_church_rubric_overrides(church_id) -> dict`
- `get_church_rubric(church_id) -> dict` (merged)
- `update_church_rubric(church_id, patch) -> dict`: applies a validated patch,
  where `null` for a checklist or setting removes that override (reset to
  default). Returns the merged rubric.

Reset granularity is one checklist or one setting.

Validation limits: at most 12 items per checklist; each item is a non-empty
string of at most 300 characters after trimming. Whitespace runs inside an item,
line breaks included, collapse to single spaces, so each item stays one
`- item` line in the prompt; an item with any other control character is
invalid. `prefer_before_year` must be
between 1500 and the current year. `prefer_familiar` must be a boolean. An
empty list is invalid; to reset, use `null`.

## API

A new router, `backend/api/routes/rubric.py`, registered in `api/main.py`:

- `GET /rubric`, for any church member (`require_church`). Returns
  `{"rubric": <merged>, "customized": ["hymns.closing", "prefer_before_year", ...]}`.
  `customized` lets the slice 6 screen show which items differ from the
  default.
- `PATCH /rubric`, for admins and owners (`require_admin`). The body is a
  sparse patch as described above. Returns the same shape as `GET`. Invalid
  input returns 422 with the validation message.

The response model (`RubricOut`) goes in `api/schemas.py`. The `PATCH` body is a plain JSON object checked by `service_rubric.validate_patch`, so its error messages stay readable.

## Hymn year and familiarity

### New data

Two nullable integer columns go on both `hymn_catalog` and `hymns`:

- `text_year`: the year the words were written (the words, not the tune; new
  words set to an old tune count as new).
- `hymnal_count`: how many hymnals include the text. This is the familiarity
  signal.

`_hymn_to_dict` exposes them as `"Text Year"` and `"Hymnal Count"`, and
`seed_church_from_catalog` copies them.

Existing databases get the columns from a new idempotent script,
`backend/migrate_add_hymn_facts.py`, modeled on `migrate_add_hymnal.py`. It
checks the existing columns with SQLAlchemy's inspector and adds only the
missing ones. This works on both Postgres and SQLite, which lacks
`ADD COLUMN IF NOT EXISTS`, so it can be tested locally. **Deploy order matters:** run it against Supabase
**before** merging. Both the Streamlit app and the Railway API select every
mapped column, so they would fail against a database that lacks the new
columns.

### Source: Hymnary.org's public API

Hymnary.org's website sits behind a bot challenge, so the backfill does not
scrape it. The public scripture API (`https://hymnary.org/api/scripture?reference=…`)
answers plain requests. It returns a JSON object keyed by each text's first
line. Each value holds `title` (a short name, sometimes null),
`number of hymnals`, a `text link`, often `date`, and people fields with life
dates such as `author: "Perronet, Edward, 1721-1792"`. A response holds at most
100 texts and cannot be paged.

A new one-off script, `backend/backfill_hymn_facts.py`:

1. For each row in `hymn_catalog` and `hymns` that is missing either value,
   queries the API once for each of the row's `scripture_refs`. Responses are
   cached per reference, and requests are spaced about 1 second apart.
2. Matches results to the row by normalized title (lowercase, punctuation and
   leading articles stripped). It compares the row's title with each text's
   `title` and with its first line, since some catalogs list hymns by first
   line. A text matching both ways counts once. When any text matches by
   title, texts that only match by first line are set aside.
3. When several texts match, takes the one in the most hymnals. It leaves the
   row unknown instead when a response hit the 100-text cap, because the cap
   may have dropped a more-published text of the same name.
4. Sets `hymnal_count` from `number of hymnals`.
5. Sets `text_year` from the first 4-digit year in `date`. If `date` is absent,
   it estimates from the main writers first: author, translator, paraphraser
   and versifier, including qualified keys such as `author (attributed to)`
   and `translator (dutch)`. It takes the latest death year among them. Only
   when none of them gives a year does it use the adapter and alterer fields
   the same way, since those people may have reworked the words long after
   they were written ("Prepare the Way, O Zion": author Franzen, 1772-1847,
   adapted by Price, 1920-1999, is 1847). Life dates may use a hyphen, en dash
   or em dash, or `d. YYYY` and `b. YYYY`. A person with only a birth year
   counts as birth year + 35, capped at the current year so the estimate is
   never a future year.
6. Only fills blanks and never overwrites a value, so manual corrections
   survive re-runs. The script is idempotent and supports `--dry-run`.
7. Leaves a row unknown for this run when one of its requests fails, rather
   than guessing from partial results. A later run retries it.
8. Prints the database it uses first (password hidden), then coverage: rows
   matched, rows left unknown, failed requests, references that hit the
   100-text cap, and references Hymnary could not parse (these are skipped).

Rows with no scripture references or no match stay `NULL` (unknown). Hymns
added later, by a hymnal import or Settings' Add hymn, also start unknown until
the script runs again.

## How the hymn picker uses the rubric

`suggest_hymns_for_service` gains `rubric: dict | None = None`, where `None`
means the defaults.

- **Ranking.** Each slot's candidate list is sorted, then cut to 60.
  - First key: era. Hymns with `text_year < prefer_before_year` come first,
    then unknown years, then newer hymns.
  - Second key (only when `prefer_familiar` is on): `hymnal_count`, highest
    first. An unknown count ranks as the median of the known counts in that
    list, so it is neither pushed up nor down.
  - The sort is stable, so the existing order breaks ties.
  - The cut keeps places for newer hymns. A list of 60 or fewer is not cut.
    For a longer list, up to 12 of the 60 places go to the best-ranked
    unknown-year and newer hymns, taken from each group in turn, so older
    hymns cannot crowd them out. Places they do not need go back to older
    hymns. The list stays in ranked order. (Added during Task 7 review so the
    age preference does not act as a filter.)
  - When a slot has no theme-matched candidates, the fallback becomes the full
    ranked hymn list, cut the same way. Today it is the first 80 hymns in
    storage order.
- **Checklists.** The hard-coded `ROLE REQUIREMENTS` block is replaced by the
  three slot checklists from the rubric.
- **More detail for the AI.** Each candidate line gains `(written 1826, in
  1,322 hymnals)` when those facts are known. The instructions add: "Prefer
  hymns written before {year} and hymns found in many hymnals; choose a newer
  hymn only when it fits clearly better."
- **Output.** `hymn_display_info` adds `year`, `hymnal_count` and
  `newer_than_preferred` (a boolean) so slice 3 can label newer hymns with
  their year.

**Known limit.** The opening and closing candidate lists are still narrowed by
fixed theme keywords in `worship_service.py` (`_OPENING_THEMES`,
`_CLOSING_THEMES`) before ranking. The keywords match the default checklists;
if a church rewrites a slot checklist, they may not match it. Revisit when the
slice 6 rubric editor makes checklists editable.

## How the liturgy writer uses the rubric

`generate_liturgy` gains two optional parameters:

- `rubric: dict | None = None` (`None` means the defaults)
- `sermon_text: tuple[str, str] | None = None`: the New Testament reference
  and its text

For each section it generates, after rendering the section prompt, it appends:

1. The section's checklist, headed `A good {Section Label}:` with one `- item`
   per line.
2. When `sermon_text` is given: `Sermon text ({ref}), for themes only; do not
   quote, cite, or name it:` followed by the text, truncated to 2,000
   characters. Passages that failed to load (`"[Could not load text]"`) are
   skipped.

These blocks are appended in code, not added as template placeholders, so a
church that has edited its prompts still gets them.

## Streamlit call sites (no new screens)

In `app.py`:

- `suggest_hymns_for_service(...)` also passes `rubric=get_church_rubric(church_id)`.
- `generate_liturgy(...)` also passes `rubric=get_church_rubric(church_id)` and
  `sermon_text`: the selected New Testament reference with its text from the
  loaded passages (`scripture_full_texts`). When that text is missing it is
  fetched and kept in `scripture_full_texts` for the session. `sermon_text` is
  `None` when no reference is selected or the fetch fails.

## Testing

All AI calls are faked. Tests cover:

- **Merge.** Defaults load for a church with no overrides. Overrides replace
  only their own checklist or setting. Unknown keys and invalid values are
  ignored on read.
- **Validation.** Unknown keys, empty lists, over-long items, bad years and
  non-boolean flags are rejected. `null` resets.
- **Isolation.** One church's rubric edits never appear in another church.
- **API.** A member can `GET`. A plain member gets 403 on `PATCH`; an admin
  can `PATCH`. `customized` is accurate. Bad input returns 422.
- **Ranking.** Older-then-unknown-then-newer order holds. Familiarity orders
  within each era. The median rule applies to unknown counts. Turning off
  `prefer_familiar` keeps the original order within each era.
- **Prompts.** The checklists and the sermon text reach the messages sent to
  the fake model, including for a church with edited prompts. The hymn prompt
  contains the slot checklists and the year/familiarity details.
- **Backfill.** Year parsing covers `date`, death years, the birth-year-only
  estimate, and no data. Title matching is covered. Blanks are filled and
  existing values are not overwritten. Dry run writes nothing. The API is
  faked with no network.
- **Migration.** `migrate_add_hymn_facts.py` is idempotent on SQLite. Seeding
  copies the new columns.
- **Defaults.** The two changed default prompts say "no more than 3/three
  sentences."

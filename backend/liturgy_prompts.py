#!/usr/bin/env python3
"""Editable liturgy prompts.

The AI liturgy is driven by one "voice" (system) prompt plus one prompt per
section. These defaults live here as templates with named placeholders so they
can be shown in the UI and overridden per church (Settings -> Liturgy prompts).

Placeholders a section template may use (all optional; unknown ones render as
empty, so an edited prompt never crashes):
  {occasion}      e.g. "Sixteenth Sunday in Ordinary Time"
  {scriptures}    the day's readings as a bulleted list (for theme inspiration)
  {opening_hymn}  the selected opening hymn title (or "N/A")
  {hymns}         all selected hymns as a bulleted list
"""
import string
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import prayer_library
import service_rubric

# The one home of the section order and labels is liturgy_config (slice 4); the
# names stay here for frozen Streamlit's Settings page and the tests.
from liturgy_config import SECTION_LABELS, SECTION_ORDER  # noqa: F401 (re-exported)

PLACEHOLDER_HELP = (
    "Placeholders you can use: {occasion}, {scriptures}, {opening_hymn}, {hymns}. "
    "Unknown placeholders are ignored (they render as blank)."
)

# The season rule (service reviewer decision 6, 2026-09-26): seasonal themes are
# welcome and the season or festival may be named; canned or repetitive seasonal
# language is not. The reviewer's prompt quotes the same sentence.
SEASON_GUIDANCE = (
    "Let the season's themes come through when the time calls for it, and name the season or festival "
    "where it is natural; saying 'Easter' or 'Christmas' more than once is fine. Avoid canned or repetitive "
    "seasonal language: no stock phrases like 'in this season of…,' 'as we journey through…,' or "
    "'on this Nth Sunday…,' and never name Ordinary Time."
)

DEFAULT_SYSTEM_PROMPT = (
    "You are a thoughtful worship writer for Christian liturgy from a moderate Reformed perspective, "
    "in line with PC(USA) theology. Write in clear, inclusive language. "
    "Avoid exclusively male references to God: use 'God' by name, or varied language (e.g. 'God who is Father, Son, and Holy Spirit' when trinitarian language fits); "
    "do not use only 'he/him/his' or 'Lord' alone for God; you may use 'Lord' as one among other titles. "
    "Do not directly cite or name scripture passages in the liturgy (e.g. avoid 'as we hear in 1 Samuel,' 'in our gospel reading,' or 'the psalm tells us'). "
    "Instead, draw on the themes and spirit of the day in general, evocative language. "
    + SEASON_GUIDANCE + " "
    "Vary how you address God—avoid repeating similar openings (e.g. 'God of X and Y') across prayers. "
    "Use diverse forms: 'Gracious God,' 'Eternal One,' 'Lord of mercy,' 'O God,' 'God of all creation,' etc. "
    "Keep each piece concise and usable in worship. Output only the liturgy text, no meta-commentary or labels."
)

DEFAULT_SECTION_PROMPTS: Dict[str, str] = {
    "call_to_worship": (
        "Write a Call to Worship for: {occasion}. "
        "Themes from today's readings (use for inspiration only; do not cite): {scriptures}. Opening hymn: {opening_hymn}. "
        "Use exactly this format with four parts: 'Leader: ' (2-3 lines), then 'People: ' (one short response), "
        "then 'Leader: ' again (2-3 lines), then 'People: ' again (one short response). "
        "Do not mention specific books, chapters, or verses."
    ),
    "opening_prayer": (
        "Write an Opening Prayer (collect) for: {occasion}. "
        "Themes from today's readings (use for inspiration only; do not cite): {scriptures}. "
        "Around 100 words. Address God, thank or praise, and ask for one thing fitting the day. End with 'Amen.' "
        "Do not name or quote specific passages."
    ),
    "prayer_of_confession": (
        "Write a Prayer of Confession for: {occasion}. "
        "Themes from today's readings (use for inspiration only; do not cite): {scriptures}. "
        "One short paragraph. First person plural (we). "
        "Do not end with an invitation (e.g. avoid 'let us now take a moment to confess' or 'in a moment of silence...'). "
        "End with 'in the name of Jesus. Amen.' Do not mention specific scripture passages."
    ),
    "assurance": (
        "Write only the Leader line for Assurance of Pardon for: {occasion}, "
        "grounded in God's grace in Christ. One sentence. Do not include "
        "'People:' or 'Thanks be to God'—that will be added separately. "
        "Start your response with 'Leader: ' followed by the sentence."
    ),
    "prayer_for_illumination": (
        "Write a Prayer for Illumination for: {occasion}. "
        "Themes from today's readings (use for inspiration only; do not cite): {scriptures}. "
        "Write no more than 3 sentences asking God to open hearts and minds to the Word, that we may hear and respond. End with 'Amen.' "
        "Do not name specific books or passages; speak generally of God's Word."
    ),
    "prayers_of_the_people": (
        "Write Prayers of the People for: {occasion}. "
        "Themes from today's readings (use for inspiration only; do not cite): {scriptures}. Hymns: {hymns}. "
        "Write a substantial, full prayer (at least 10–15 paragraphs) in 'out to in' order: "
        "First, prayers for the world (nations, creation, peace, the suffering). "
        "Second, prayers for the Church universal and our denomination and congregation. "
        "Third, prayers for our country and our local community and leaders. "
        "Fourth, prayers for ourselves and our families. "
        "Then include an explicit invitation for the congregation to share joys and concerns aloud "
        "(e.g. 'Let us now lift up the joys and concerns of this congregation' or 'You are invited to name aloud...'). "
        "Then include a clear bid for a moment of silence—to lift up individuals or situations, or simply to sit in silence before God. "
        "Use 'we pray,' 'let us pray,' or similar. End with a closing that leads into the Lord's Prayer or a final amen. "
        "Write in full sentences and paragraphs; this should feel like a complete, unhurried pastoral prayer. "
        "Do not cite or name specific scripture passages."
    ),
    "offertory_prayer": (
        "Write an Offertory Prayer for: {occasion}. "
        "No more than three sentences: thank God for provision, dedicate our gifts and ourselves to God's service, "
        "and ask that our offerings be used for the work of the kingdom. End with 'Amen.'"
    ),
    "benediction": (
        "Write a Benediction (1–3 sentences) for: {occasion}. "
        "Themes from today's readings (use for inspiration only; do not cite): {scriptures}. "
        "Send the people out to serve and share God's love. You may invoke the Trinity. End with 'Amen.' "
        "Do not mention specific books or passages."
    ),
}

# Keys allowed in a stored prompt-override dict: "system" + each section.
PROMPT_KEYS: List[str] = ["system"] + SECTION_ORDER


class _SafeDict(dict):
    """format_map helper: an unknown placeholder renders as '' instead of raising,
    so an admin-edited prompt with a stray or misspelled {placeholder} never crashes
    liturgy generation."""

    def __missing__(self, key):  # noqa: D401
        return ""


def default_prompts() -> Dict[str, str]:
    """The full default prompt set: {'system', 'call_to_worship', ...}."""
    out = {"system": DEFAULT_SYSTEM_PROMPT}
    out.update(DEFAULT_SECTION_PROMPTS)
    return out


def merge_prompts(overrides: Dict[str, str] | None) -> Dict[str, str]:
    """Defaults with any non-blank per-key overrides applied. Ignores unknown keys,
    and values that are not strings (settings is JSON anyone could have written)."""
    prompts = default_prompts()
    for key in PROMPT_KEYS:
        value = (overrides or {}).get(key)
        if isinstance(value, str) and value.strip():
            prompts[key] = value
    return prompts


def render(template: str, *, occasion: str = "", scriptures: str = "",
           opening_hymn: str = "", hymns: str = "") -> str:
    """Fill a section template's placeholders. Safe against unknown placeholders."""
    ctx = _SafeDict(
        occasion=occasion,
        scriptures=scriptures,
        opening_hymn=opening_hymn,
        hymns=hymns,
    )
    return template.format_map(ctx)


# --- slice 4a: the template validator (slice 4 spec, Backend 2; reused by 6a) ---

KNOWN_PLACEHOLDERS = ("occasion", "scriptures", "opening_hymn", "hymns")
# Counted on the text as given, so a CRLF line ending counts as two characters:
# callers (6a's PUT) run clean_prompt_overrides first, then check_template on
# what it keeps, so a browser's CRLF textarea is measured as it will be stored.
MAX_TEMPLATE_CHARS = 8000
MAX_PROMPT_CHARS = 24_000         # system + user, the cost guard (F §2.8)

TOO_LONG_TEMPLATE = "This prompt is too long (max 8,000 characters)."
UNPAIRED_BRACE = "It has a { or } without a partner. Use {{ or }} to print a brace."
NO_NAME = "Placeholders need a name, such as {occasion}."
NOT_PLAIN_NAME = "Placeholders must be a plain name such as {occasion}, with no dots or brackets."
NOT_ONE_WORD = ("Placeholders must be a single word such as {occasion}. "
                "To print a { or } as text, write {{ or }}.")
HAS_SPEC = "Placeholders can't include ! or :. Write just {occasion}."
CANT_FILL = "It can't be filled in. Check the { } placeholders."


@dataclass(frozen=True)
class TemplateCheck:
    ok: bool
    message: Optional[str]                      # user-facing reason when not ok
    unknown_placeholders: tuple[str, ...]       # render as blank; 6a may show them as warnings


def _failed(message: str) -> TemplateCheck:
    return TemplateCheck(False, message, ())


def check_template(key: str, template: str) -> TemplateCheck:
    """The first failing check, in the spec's order, or ok with the unknown
    placeholders. The system prompt is sent as written, never formatted, so
    only its length is checked. Never raises. The length is of the text as
    given (CRLF counts two): run clean_prompt_overrides first."""
    if not isinstance(template, str):
        return _failed(CANT_FILL)
    if len(template) > MAX_TEMPLATE_CHARS:
        return _failed(TOO_LONG_TEMPLATE)
    if key == "system":
        return TemplateCheck(True, None, ())
    try:
        parsed = list(string.Formatter().parse(template))
    except ValueError:
        return _failed(UNPAIRED_BRACE)
    fields = [(name, spec, conversion) for _text, name, spec, conversion in parsed if name is not None]
    checks = (
        (lambda name, spec, conv: name == "" or name.isdigit(), NO_NAME),
        (lambda name, spec, conv: "." in name or "[" in name, NOT_PLAIN_NAME),
        (lambda name, spec, conv: not name.isidentifier(), NOT_ONE_WORD),
        (lambda name, spec, conv: conv is not None or bool(spec), HAS_SPEC),
    )
    for fails, message in checks:
        if any(fails(*field) for field in fields):
            return _failed(message)
    try:
        template.format_map(_SafeDict({name: "sample" for name in KNOWN_PLACEHOLDERS}))
    except Exception:                                    # inv §0 item 4: never crash here
        return _failed(CANT_FILL)
    unknown = tuple(dict.fromkeys(name for name, _spec, _conv in fields if name not in KNOWN_PLACEHOLDERS))
    return TemplateCheck(True, None, unknown)


def template_error(template: str) -> Optional[str]:
    """The section-template check 6a calls: the reason, or None. Any section key
    gives the same result; only "system" is special. Never raises."""
    return check_template("call_to_worship", template).message


def validate_prompts(prompts: Mapping[str, Any]) -> dict[str, str]:
    """key -> reason for each stored override merge_prompts would use (a
    non-blank string under a PROMPT_KEYS key) that fails check_template.
    Other keys and values are skipped: merge_prompts ignores them."""
    if not isinstance(prompts, Mapping):
        return {}
    failures = {}
    for key in PROMPT_KEYS:
        value = prompts.get(key)
        if isinstance(value, str) and value.strip():
            message = check_template(key, value).message
            if message is not None:
                failures[key] = message
    return failures


def _normalized(value: Any) -> str:
    return value.replace("\r\n", "\n").strip() if isinstance(value, str) else ""


def clean_prompt_overrides(prompts: Mapping[str, Any],
                           defaults: Optional[Mapping[str, Any]] = None) -> dict[str, str]:
    """The overrides worth storing (streamlit_views/settings.py submit_prompts,
    plus one rule): each value and default has its CRLF line endings read as LF
    (browser textareas submit CRLF) and is stripped; a PROMPT_KEYS value that is
    then non-blank and differs from its default is kept, stored normalized.
    defaults=None means default_prompts(). The one rule for "equal to the
    default": 6a's PUT imports it and has no second copy."""
    if not isinstance(prompts, Mapping):
        return {}                         # a list, string or None stores nothing (as validate_prompts)
    defaults = default_prompts() if defaults is None else defaults
    cleaned = {}
    for key, value in prompts.items():
        if key not in PROMPT_KEYS:
            continue
        text = _normalized(value)
        if text and text != _normalized(defaults.get(key)):
            cleaned[key] = text
    return cleaned


# --- slice 4a: building a section's messages (slice 4 spec, Backend 2, with the
# 2026-09-26 amendments: PR #4's rubric checklist and sermon text, PR #7's voice) ---

SERMON_TEXT_LIMIT = 2000                      # moved from worship_service (PR #4)
SERMON_TEXT_FAILED = "[Could not load text]"  # Streamlit's sentinel for a passage that failed
TOO_LONG_WITH_ADDITIONS = "It is too long once the readings, hymns and rubric checklist are added."
HYMN_SLOTS = ("opening", "response", "closing")
VOICE_PROFILE_INTRO = "Write in the voice of this church's pastor, described here:\n"
VOICE_EXAMPLE_INTRO = "For voice only, here is a {label} this pastor wrote. Do not reuse its lines or phrases:\n"


def _one_line(text: Optional[str], limit: int) -> str:
    """Client text for the prompt: whitespace (newlines included) collapsed to one
    space, stripped and cut, so a field cannot add lines of its own (as
    hymn_suggest._clip does)."""
    return " ".join((text or "").split())[:limit]


def sermon_text_block(ref: Optional[str], text: Optional[str]) -> str:
    """The sermon-text context for a prompt (PR #4, moved from worship_service),
    or "" when the reference or text is blank or the passage failed to load."""
    text = (text or "").strip()
    ref = _one_line(ref, 200)
    if not ref or not text or SERMON_TEXT_FAILED in text:
        return ""
    return (f"Sermon text ({ref}), for themes only; do not quote, cite, or name it:\n"
            f"{text[:SERMON_TEXT_LIMIT]}")


@dataclass(frozen=True)
class ResolvedHymn:
    """A slot's hymn as the prompt shows it: the database's title and number
    for a hymn_id, or an archived snapshot's own."""
    title: str
    number: Optional[int]


@dataclass(frozen=True)
class PromptContext:
    occasion: str
    scriptures: str
    opening_hymn: str
    hymns: str
    checklists: Mapping[str, tuple[str, ...]] = field(default_factory=dict)   # the merged rubric's "prayers"
    sermon: str = ""                                                          # sermon_text_block(...) or ""


def build_context(*, occasion: str, scriptures: Sequence[str],
                  hymns_by_slot: Mapping[str, Optional[ResolvedHymn]],
                  rubric: Optional[Mapping[str, Any]] = None,
                  sermon_ref: Optional[str] = None, sermon_text: Optional[str] = None) -> PromptContext:
    """The placeholders' values and the blocks appended after render().

    - scriptures: "- {ref}" lines (blank ones dropped), or "None specified.".
    - hymns: the filled slots in slot order, "- {title} (#{number})", or
      "- {title}" without a number; "None chosen." when none is filled. A slot
      with a blank title counts as empty.
    - opening_hymn: the opening slot's title, else "N/A" (never another slot's).
    - checklists: service_rubric.merge_rubric(rubric)["prayers"], so None, a
      church's sparse overrides or a full rubric all work (PR #4).
    """
    lines = [line for line in (_one_line(s, 200) for s in scriptures) if line]
    filled = [(slot, hymn, _one_line(hymn.title, 300)) for slot in HYMN_SLOTS
              if (hymn := hymns_by_slot.get(slot)) is not None and _one_line(hymn.title, 300)]
    hymn_lines = [f"- {title} (#{hymn.number})" if hymn.number is not None else f"- {title}"
                  for _slot, hymn, title in filled]
    opening = next((title for slot, _hymn, title in filled if slot == "opening"), "N/A")
    prayers = service_rubric.merge_rubric(dict(rubric) if rubric is not None else None)["prayers"]
    return PromptContext(
        occasion=_one_line(occasion, 300),
        scriptures="\n".join(f"- {line}" for line in lines) or "None specified.",
        opening_hymn=opening,
        hymns="\n".join(hymn_lines) or "None chosen.",
        checklists={key: tuple(points) for key, points in prayers.items()},
        sermon=sermon_text_block(sermon_ref, sermon_text),
    )


@dataclass(frozen=True)
class VoiceContext:
    """The prayer library's voice for one section (PR #7): the church's voice
    profile and one same-type example, or None."""
    profile: str
    example: Optional[str]


class PromptInvalid(Exception):
    """The church's own prompt text cannot be used for this section."""

    def __init__(self, section: str, reason: str):
        super().__init__(reason)
        self.section = section
        self.reason = reason


@dataclass(frozen=True)
class BuiltPrompt:
    messages: list[dict[str, str]]
    dropped: tuple[str, ...]          # "example", "profile", "sermon": what the budget left out


def build_prompt(section: str, prompts: Mapping[str, str], ctx: PromptContext, *,
                 voice: Optional[VoiceContext] = None) -> BuiltPrompt:
    """The section's [system, user] messages and what the budget dropped.

    1. The section's template must pass check_template, else PromptInvalid.
    2. system = prompts["system"]; user = render(template, ctx).
    3. The section's non-empty checklist is appended to user.
    4. Over MAX_PROMPT_CHARS now: PromptInvalid (the church's own text).
    5. After render(), so braces in them are never placeholders: the sermon
       block (user), the voice profile, stripped and cut to 2 000 (system),
       and the example, cut to 3 000 (user). While over MAX_PROMPT_CHARS, the
       example is dropped first, then the profile, then the sermon block;
       they never raise.
    With voice None, or an empty profile and no example, the result is the
    same as without the voice blocks, byte for byte.
    """
    template = prompts[section]
    check = check_template(section, template)
    if not check.ok:
        raise PromptInvalid(section, check.message or CANT_FILL)
    system = prompts["system"]
    user = render(template, occasion=ctx.occasion, scriptures=ctx.scriptures,
                  opening_hymn=ctx.opening_hymn, hymns=ctx.hymns)
    checklist = ctx.checklists.get(section)
    if checklist:
        user += "\n\n" + service_rubric.format_checklist(SECTION_LABELS[section], list(checklist))
    if len(system) + len(user) > MAX_PROMPT_CHARS:
        raise PromptInvalid(section, TOO_LONG_WITH_ADDITIONS)
    blocks = {
        "sermon": ctx.sermon,
        "profile": (voice.profile if voice else "").strip()[:prayer_library.MAX_PROFILE_CHARS],
        "example": ((voice.example or "") if voice else "")[:prayer_library.MAX_EXAMPLE_CHARS],
    }
    blocks = {name: text for name, text in blocks.items() if text.strip()}
    dropped: list[str] = []
    while True:
        full_system = system + ("\n\n" + VOICE_PROFILE_INTRO + blocks["profile"] if "profile" in blocks else "")
        full_user = user
        if "sermon" in blocks:
            full_user += "\n\n" + blocks["sermon"]
        if "example" in blocks:
            full_user += ("\n\n" + VOICE_EXAMPLE_INTRO.format(label=SECTION_LABELS[section])
                          + blocks["example"])
        if len(full_system) + len(full_user) <= MAX_PROMPT_CHARS:
            break
        name = next(n for n in ("example", "profile", "sermon") if n in blocks)
        del blocks[name]
        dropped.append(name)
    return BuiltPrompt(messages=[{"role": "system", "content": full_system},
                                 {"role": "user", "content": full_user}],
                       dropped=tuple(dropped))


def build_messages(section: str, prompts: Mapping[str, str], ctx: PromptContext, *,
                   voice: Optional[VoiceContext] = None) -> list[dict[str, str]]:
    """build_prompt's messages (the interface the spec names; 6a and the reviewer use it)."""
    return build_prompt(section, prompts, ctx, voice=voice).messages

"""liturgy_config: the liturgy step's fixed data (slice 4 spec, Backend 1;
Testing `test_liturgy_config.py`; AC1, AC2). The shared fixtures under
tests/fixtures/shared/ are the authority 4b's TypeScript reads too."""
import ast
import json
from datetime import date
from pathlib import Path

import pytest

import liturgy_config as lc

SHARED = Path(__file__).resolve().parent / "fixtures" / "shared"
APP_PY = Path(__file__).resolve().parents[2] / "app.py"
OUTLINE_FIXTURE = SHARED / "liturgy_outline.json"
REGENERATE = "PYTHONPATH=backend .venv/bin/python backend/tests/test_liturgy_config.py"


def _shared(name: str) -> dict:
    return json.loads((SHARED / name).read_text(encoding="utf-8"))


def write_outline_fixture() -> None:
    """Rewrite shared/liturgy_outline.json from OUTLINE (one item per line)."""
    about = _shared("liturgy_outline.json")["_about"]
    lines = ",\n".join("    " + json.dumps(item, ensure_ascii=False) for item in lc.outline_as_json())
    OUTLINE_FIXTURE.write_text('{\n  "_about": ' + json.dumps(about) + ',\n  "outline": [\n'
                               + lines + "\n  ]\n}\n", encoding="utf-8")


def test_sections_match_the_shared_fixture():
    expected = _shared("liturgy_sections.json")["sections"]
    assert [{"key": s.key, "label": s.label, "default_enabled": s.default_enabled}
            for s in lc.SECTIONS] == expected
    assert lc.SECTION_ORDER == [s["key"] for s in expected]
    assert lc.SECTION_LABELS == {s["key"]: s["label"] for s in expected}
    assert lc.SECTIONS_BY_KEY["benediction"].label == "Benediction"


def test_rows_budgets_pastor_copy_and_hints():
    for spec in lc.SECTIONS:
        pastor = spec.key == "prayers_of_the_people"
        assert (spec.rows, spec.max_completion_tokens, spec.pastor_copy_only) == (
            (8, 4000, True) if pastor else (4, 1500, False)), spec.key
        assert spec.timeout_seconds == (60.0 if pastor else None), spec.key
    hints = {s.key: s.hint for s in lc.SECTIONS if s.hint is not None}
    assert hints == {
        "call_to_worship": "Start lines with “Leader:” or “People:”. People lines print in bold.",
        "prayer_of_confession": "Printed in bold for everyone to read together.",
        "assurance": "Added automatically after your text.",
        "benediction": "Your church's default benediction. Admins can change it in Settings.",
    }


def _app_py_placements() -> list[tuple[str, str]]:
    """The CUSTOM_PLACEMENTS list literal in the frozen app.py (read, never imported)."""
    tree = ast.parse(APP_PY.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "CUSTOM_PLACEMENTS" for t in node.targets):
            return [tuple(pair) for pair in ast.literal_eval(node.value)]
    raise AssertionError("CUSTOM_PLACEMENTS not found in app.py")


@pytest.mark.skipif(not APP_PY.exists(), reason="app.py is gone (slice 7 deletes the Streamlit app): "
                    "liturgy_config.CUSTOM_PLACEMENTS is then the only copy of the 17 placements")
def test_custom_placements_are_app_py_s_17_with_the_first_reading_label():
    frozen = _app_py_placements()
    assert len(frozen) == len(lc.CUSTOM_PLACEMENTS) == 17
    # Owner decision B: "First Reading" wherever the app shows that heading.
    renamed = [("ot_reading", "After First Reading") if key == "ot_reading" else (key, label)
               for key, label in frozen]
    assert list(lc.CUSTOM_PLACEMENTS) == renamed
    assert lc.PLACEMENT_KEYS == {key for key, _ in frozen}


def _app_py_communion_checkbox_label() -> str:
    """The first argument of the st.checkbox keyed "include_communion" in app.py."""
    tree = ast.parse(APP_PY.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "checkbox"
                and any(k.arg == "key" and isinstance(k.value, ast.Constant) and k.value.value == "include_communion"
                        for k in node.keywords)):
            return ast.literal_eval(node.args[0])
    raise AssertionError('st.checkbox(..., key="include_communion") not found in app.py')


@pytest.mark.skipif(not APP_PY.exists(), reason="app.py is gone (slice 7 deletes the Streamlit app): "
                    "liturgy_config.COMMUNION_TOGGLE_LABEL is then the only copy")
def test_communion_toggle_label_is_app_py_s():
    assert lc.COMMUNION_TOGGLE_LABEL == _app_py_communion_checkbox_label()


def test_every_placement_is_anchored_exactly_once():
    anchors = [anchor for item in lc.OUTLINE for anchor in item.anchors_after]
    assert sorted(anchors) == sorted(lc.PLACEMENT_KEYS)
    assert len(anchors) == len(set(anchors)) == 17
    assert [item.key for item in lc.OUTLINE if item.kind == "section"] == lc.SECTION_ORDER
    assert len(lc.OUTLINE) == 16
    third_hymn = next(item for item in lc.OUTLINE if item.key == "third_hymn")
    assert third_hymn.anchors_after == ("third_hymn", "benediction")      # "Before Benediction"


def test_outline_fixture_equals_outline():
    stored = _shared("liturgy_outline.json")["outline"]
    assert stored == lc.outline_as_json(), f"shared/liturgy_outline.json is stale. Regenerate: {REGENERATE}"


def test_first_sunday_cases():
    for case in _shared("first_sunday.json")["cases"]:
        assert lc.is_first_sunday_of_month(date.fromisoformat(case["date"])) is case["expected"], case


def test_resolve_default_benediction():
    cases = [
        (None, "Halverson"),
        ({}, "Halverson"),
        ({"default_benediction": 5}, "Halverson"),
        ({"default_benediction": None}, "Halverson"),
        ({"default_benediction": ""}, ""),
        ({"default_benediction": "May the Lord bless you…"}, "May the Lord bless you…"),
        ("not a mapping", "Halverson"),
    ]
    for settings, expected in cases:
        assert lc.resolve_default_benediction(settings) == expected, settings


def test_normalize_placement_limits_and_fixed_text():
    assert lc.normalize_placement("bogus") == "end"
    assert lc.normalize_placement(None) == "end"
    assert lc.normalize_placement("communion") == "communion"
    assert lc.LIMITS == lc.Limits(max_section_text=20_000, max_sermon_title=300, max_custom_elements=30,
                                  max_custom_label=200, max_custom_text=10_000, max_sections_per_request=4)
    assert lc.ASSURANCE_RESPONSE == "People: Thanks be to God! Amen."
    assert lc.DEFAULT_BENEDICTION_FALLBACK == "Halverson"
    assert lc.COMMUNION_TOGGLE_LABEL == "Include communion liturgy (The Sacrament of the Lord's Supper)"
    assert lc.COMMUNION_BLOCKS[0] == lc.CommunionBlock("heading1", lc.COMMUNION_TITLE)
    assert [b.text for b in lc.COMMUNION_BLOCKS if b.style == "heading2"] == [
        "Invitation to the Table", "Great Thanksgiving", "Words of Institution", "The Lord's Prayer",
        "Breaking of the Bread and Communion", "Prayer After Communion"]


# The docx still prints "Old Testament Reading" until 5a renames it to OUTLINE's
# "First Reading" (owner decision B; slice 4a plan, clarification 4). 5a deletes
# this map when it changes build_docx.
DOCX_HEADINGS_UNTIL_5A = {"ot_reading": "Old Testament Reading"}


def test_the_outline_is_build_docx_s_heading_order():
    from docx import Document

    import worship_service

    buf = worship_service.build_docx(
        occasion="World Communion Sunday", date="October 4, 2026",
        scriptures=["Isaiah 5:1-7", "Matthew 21:33-46"],
        hymns=[{"title": f"Hymn {n}", "number": n} for n in (1, 2, 3)],
        liturgy={key: f"Text of {key}." for key in lc.SECTION_ORDER},
        sermon_title="Living Water", selected_ot_ref="Isaiah 5:1-7", selected_nt_ref="Matthew 21:33-46",
        include_sermon=True, include_prayers_of_the_people=True, include_communion=True,
        custom_elements=[{"label": f"CE:{key}", "text": "", "insert_after": key}
                         for key, _label in lc.CUSTOM_PLACEMENTS])
    communion_inside = {b.text for b in lc.COMMUNION_BLOCKS if b.style == "heading2"}
    printed = [p.text for p in Document(buf).paragraphs
               if p.style.name in ("Heading 1", "Heading 2") and p.text not in communion_inside]
    expected = []
    for item in lc.OUTLINE:
        expected.append(DOCX_HEADINGS_UNTIL_5A.get(item.key, item.label))
        expected.extend(f"CE:{anchor}" for anchor in item.anchors_after)
    assert printed == expected, (
        "OUTLINE and build_docx disagree: change both in one PR and regenerate "
        f"shared/liturgy_outline.json ({REGENERATE})")


if __name__ == "__main__":
    write_outline_fixture()
    print(f"wrote {OUTLINE_FIXTURE}")

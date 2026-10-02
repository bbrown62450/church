"""service_output: the Word files' date line, names, headers and helpers
(slice 5a spec, Testing `test_service_output.py`; F §1.9)."""
import json
from datetime import date
from pathlib import Path

import service_output as so

SHARED = Path(__file__).resolve().parent / "fixtures" / "shared"


def test_dates_and_filenames_follow_the_shared_fixture():
    cases = json.loads((SHARED / "docx_filenames.json").read_text(encoding="utf-8"))["cases"]
    assert len(cases) == 8
    for case in cases:
        d = date.fromisoformat(case["date"])
        assert so.service_date_display(d) == case["display"], case
        assert so.docx_filename(case["variant"], d) == case["filename"], case
    assert so.safe_date("October 04, 2026") == "October_04_2026"


def test_the_date_line_never_reads_the_locale():
    class NoStrftime(date):
        def strftime(self, fmt):            # '%B' follows LC_TIME; the file must not
            raise AssertionError("service_date_display read the locale")

    assert so.service_date_display(NoStrftime(2026, 10, 4)) == "October 04, 2026"
    assert so.MONTHS[0] == "January" and so.MONTHS[11] == "December" and len(so.MONTHS) == 12


def test_headers_and_variants():
    assert so.DOCX_MIME == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert so.content_disposition("worship_October_04_2026.docx") == (
        "attachment; filename=\"worship_October_04_2026.docx\"; "
        "filename*=UTF-8''worship_October_04_2026.docx")
    assert so.VARIANTS == {
        "bulletin": {"include_sermon": True, "include_prayers_of_the_people": False},
        "pastor": {"include_sermon": True, "include_prayers_of_the_people": True},
    }


def test_hymn_lines_never_print_none():
    assert so.hymn_line("Holy, Holy, Holy", 138) == "Holy, Holy, Holy — #138"
    assert so.hymn_line("Old Favorite", None) == "Old Favorite"
    assert so.hymn_line("Hymn Zero", 0) == "Hymn Zero — #0"


def test_doc_readings_are_resolve_readings():
    rcl = ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"]
    assert so.resolve_doc_readings(rcl) == ("Isaiah 5:1-7", "Philippians 3:4b-14")
    # A pick no longer among the lines is ignored: the automatic reading prints.
    assert so.resolve_doc_readings(rcl, "", "Matthew 21:33-40") == ("Isaiah 5:1-7", "Philippians 3:4b-14")
    assert so.resolve_doc_readings(rcl, "", "Matthew 21:33-46") == ("Isaiah 5:1-7", "Matthew 21:33-46")
    assert so.resolve_doc_readings(["Isaiah 5:1-7", "Psalm 80:7-15"]) == ("Isaiah 5:1-7", None)
    assert so.resolve_doc_readings([]) == (None, None)
    cases = json.loads((SHARED / "scripture_refs.json").read_text(encoding="utf-8"))["resolve_readings"]
    assert cases
    for case in cases:
        expected = (case["expected"]["ot"], case["expected"]["nt"])
        assert so.resolve_doc_readings(case["scriptures"], case["ot_pick"], case["nt_pick"]) == expected, case["name"]


def test_legacy_error_placeholders():
    for text in ("[Error generating call_to_worship: timeout]",
                 "  [Configure OPENAI_API_KEY to generate opening_prayer.]  ",
                 "[Your OPENAI_API_KEY contains invalid characters.]"):
        assert so.is_legacy_error_placeholder(text), text
    for text in ("[Sermon title]", "Error generating", "[Error generating call_to_worship", ""):
        assert not so.is_legacy_error_placeholder(text), text


# --- slice 5a-2: stored dates and hymns (5a spec, "Normalizing stored data") ---

def test_normalize_date_iso_keeps_a_real_date_and_recovers_a_time_part():
    assert so.normalize_date_iso("2026-10-04") == "2026-10-04"
    assert so.normalize_date_iso("2026-10-04T00:00:00.000Z") == "2026-10-04"     # Notion-era
    for raw in ("", None, "October 4", "2026-02-30", "2026-13-01", "26-10-04", "２０２６-10-04", 20261004, " 2026-10-04"):
        assert so.normalize_date_iso(raw) is None, raw


def test_coerce_number():
    assert [so.coerce_number(v) for v in (138, "138", " 12 ", 7.0, 0)] == [138, 138, 12, 7, 0]
    assert [so.coerce_number(v) for v in (None, True, "12a", "", 7.5, "²", [1])] == [None] * 7


def test_stored_hymn_entries_never_raise_and_keep_every_entry():
    assert so.stored_hymn_entries("Holy") == [] and so.stored_hymn_entries({"title": "x"}) == []
    assert so.stored_hymn_entries(None) == []
    entries = so.stored_hymn_entries([
        None, 42, {"title": 7}, {"title": "  "},
        {"title": " Holy, Holy, Holy ", "number": "138", "slot": "closing", "hymn_id": "abc", "hymnal": "GG2013"},
        {"title": "Fourth", "number": None, "slot": "bogus", "hymn_id": 5, "hymnal": " "},
    ])
    assert entries[:4] == [None, None, None, None]
    assert entries[4] == so.StoredHymn("closing", "Holy, Holy, Holy", 138, "abc", "GG2013")
    assert entries[5] == so.StoredHymn(None, "Fourth", None, None, None)


def test_slot_map_by_slot_or_by_position():
    react = so.stored_hymns({"opening": None, "response": so.ResolvedHymn("B", 2), "closing": so.ResolvedHymn("C", None)})
    by_slot = so.slot_map(react)
    assert by_slot["opening"] is None
    assert (by_slot["response"].title, by_slot["closing"].title) == ("B", "C")
    # Streamlit's compacted list: by position, a 4th entry ignored.
    legacy = so.slot_map([{"title": "A", "number": 1}, {"title": "B"}, {"title": "C"}, {"title": "D"}])
    assert [legacy[s].title for s in so.SLOTS] == ["A", "B", "C"]
    # One entry without a slot makes the whole list positional.
    mixed = so.slot_map([{"slot": "closing", "title": "C"}, {"title": "A"}])
    assert (mixed["opening"].title, mixed["response"].title, mixed["closing"]) == ("C", "A", None)
    assert so.slot_map([]) == so.slot_map("x") == {"opening": None, "response": None, "closing": None}


def test_stored_hymns_writes_three_slot_entries_never_null_titles():
    import uuid

    hymn_id = "3f0c1b9e-0000-4000-8000-000000000001"
    assert so.stored_hymns({"opening": so.ResolvedHymn("Holy, Holy, Holy", 138, uuid.UUID(hymn_id), "GG2013"),
                            "closing": so.ResolvedHymn("Old Favorite", 12, None, "PH1990")}) == [
        {"slot": "opening", "title": "Holy, Holy, Holy", "number": 138, "hymn_id": hymn_id, "hymnal": "GG2013"},
        {"slot": "response", "title": "", "number": None, "hymn_id": None, "hymnal": None},
        {"slot": "closing", "title": "Old Favorite", "number": 12, "hymn_id": None, "hymnal": "PH1990"},
    ]

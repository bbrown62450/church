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

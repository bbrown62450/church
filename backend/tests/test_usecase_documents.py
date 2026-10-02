"""usecases.documents.build_document and the parts of usecases.archive it uses
(slice 5a spec, Backend "usecases/documents.py", "usecases/archive.py"; Testing
`test_archive_usecase.py`'s input and hymn cases, and "build_document writes no
usage")."""
import logging
import uuid
from datetime import date
from io import BytesIO

import pytest
from docx import Document
from sqlalchemy import func, select

from db import session_scope
from db.models import Hymn, HymnUsage, Service
from domain_errors import InvalidInput, NotFound
from service_output import CustomElement, ResolvedHymn
from usecases import archive, documents
from usecases.liturgy import HymnRefData

HYMN_GONE = "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step."


@pytest.fixture
def church(make_user, make_church):
    return make_church(name="Grace", owner_user_id=make_user(email="pastor@example.com"))


def add_hymn(church_id, title="Holy, Holy, Holy", number=138, hymnal="GG2013"):
    with session_scope() as s:
        row = Hymn(church_id=church_id, hymnal=hymnal, title=title, number=number)
        s.add(row)
        s.flush()
        return row.id


def service(**kw):
    base = dict(service_date=date(2026, 10, 4), occasion="  World Communion Sunday ",
                scriptures=(" Isaiah 5:1-7", "", "Psalm 80:7-15", "Philippians 3:4b-14 ", "Matthew 21:33-46"),
                liturgy={"call_to_worship": " Leader: Come. People: We come. ", "opening_prayer": "   ",
                         "prayers_of_the_people": "We pray for the world.",
                         "offertory_prayer": "[Error generating offertory_prayer: timeout]"},
                sermon_title=" Living Water ")
    return archive.ServiceInput(**{**base, **kw})


def texts(content: bytes) -> list[str]:
    return [p.text for p in Document(BytesIO(content)).paragraphs]


def test_clean_input_trims_and_drops_blanks_and_streamlit_errors():
    clean = archive.clean_input(service(
        hymns={"opening": HymnRefData(None, "  Old Favorite ", 12, " PH1990 "), "response": None},
        hymnal="  ", selected_nt_ref=" Matthew 21:33-46 ",
        custom_elements=(CustomElement(" Anthem ", " Choir ", "sermon"),)))
    assert clean.occasion == "World Communion Sunday" and clean.sermon_title == "Living Water"
    assert clean.scriptures == ("Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46")
    assert clean.liturgy == {"call_to_worship": "Leader: Come. People: We come.",
                             "prayers_of_the_people": "We pray for the world."}
    assert clean.hymns == {"opening": HymnRefData(None, "Old Favorite", 12, "PH1990"), "response": None,
                           "closing": None}
    assert clean.hymnal is None and clean.selected_nt_ref == "Matthew 21:33-46"
    assert clean.custom_elements == (CustomElement("Anthem", "Choir", "sermon"),)


def test_clean_input_makes_windows_and_old_mac_line_endings_one_break():
    """Build review fix 1: "\\r\\n" and "\\r" become "\\n" before anything else,
    so a pasted Windows text prints one line break, not two."""
    clean = archive.clean_input(service(
        liturgy={"opening_prayer": "One\r\nTwo\rThree\r\n\r\nFour"}, sermon_title="Living\r\nWater",
        custom_elements=(CustomElement("An\r\nthem", "Choir\r\nsings", "sermon"),)))
    assert clean.liturgy == {"opening_prayer": "One\nTwo\nThree\n\nFour"}
    assert clean.sermon_title == "Living\nWater"
    assert clean.custom_elements == (CustomElement("An\nthem", "Choir\nsings", "sermon"),)
    assert "\r" not in archive._xml_safe("a\r\nb\rc\x0bd")


def test_a_blank_custom_label_is_a_422_on_its_field():
    with pytest.raises(InvalidInput) as caught:
        archive.clean_input(service(custom_elements=(CustomElement("Anthem", "", "sermon"),
                                                     CustomElement("  ", "Words", "end"))))
    assert (caught.value.message, caught.value.field) == ("Give each custom element a label.",
                                                          "custom_elements.1.label")


def test_hymn_ids_resolve_in_the_church_and_snapshots_are_kept(church, make_user, make_church):
    hymn = add_hymn(church)
    with session_scope() as s:
        resolved = archive.resolve_hymn_refs(s, church, {
            "opening": HymnRefData(hymn, "What the client says", 999, "XX"),
            "response": HymnRefData(None, "Old Favorite", None, "PH1990"),
            "closing": HymnRefData(None, "   ", 5, None)})
    assert resolved == {"opening": ResolvedHymn("Holy, Holy, Holy", 138, hymn, "GG2013"),
                        "response": ResolvedHymn("Old Favorite", None, None, "PH1990"), "closing": None}
    other = make_church(name="Other", owner_user_id=make_user(email="other@example.com"))
    for gone in (add_hymn(other), uuid.uuid4()):
        with session_scope() as s, pytest.raises(NotFound) as caught:
            archive.resolve_hymn_refs(s, church, {"opening": HymnRefData(hymn, "", None),
                                                  "response": HymnRefData(gone, "Their hymn", 1)})
        assert (caught.value.message, caught.value.details) == (HYMN_GONE, {"field": "hymns.response.hymn_id"})


def test_build_document_prints_the_cleaned_service_with_its_hymns(church, caplog):
    hymn = add_hymn(church)
    data = service(hymns={"opening": HymnRefData(hymn, "Stale title", 1), "response": None,
                          "closing": HymnRefData(None, "Old Favorite", None)})
    with caplog.at_level(logging.INFO, logger="usecases.documents"):
        bulletin = documents.build_document(church, data, "bulletin")
    pastor = documents.build_document(church, data, "pastor")
    assert bulletin.filename == "worship_October_04_2026.docx"
    assert pastor.filename == "worship_pastor_October_04_2026.docx"
    assert bulletin.content[:2] == b"PK"
    lines = texts(bulletin.content)
    assert lines[:2] == ["Worship Service\nWorld Communion Sunday", "October 04, 2026"]
    assert lines[lines.index("First Hymn") + 1] == "Holy, Holy, Holy — #138"
    assert "Second Hymn" not in lines and lines[lines.index("Third Hymn") + 1] == "Old Favorite"
    assert lines[lines.index("First Reading") + 1] == "Isaiah 5:1-7"
    assert lines[lines.index("New Testament Reading") + 1] == "Philippians 3:4b-14"
    assert lines[lines.index("Sermon Title") + 1] == "Living Water"
    assert "Opening Prayer" not in lines and "Offertory Prayer" not in lines
    assert "Prayers of the People" not in lines and "Prayers of the People" in texts(pastor.content)
    [record] = [r for r in caplog.records if r.name == "usecases.documents"]
    assert record.getMessage().startswith(f"documents.build church={church} variant=bulletin bytes=")
    assert "Living Water" not in record.getMessage() and "Communion" not in record.getMessage()


def test_build_document_writes_nothing(church):
    documents.build_document(church, service(hymns={"opening": HymnRefData(add_hymn(church), "", None)}), "pastor")
    with session_scope() as s:
        assert s.scalar(select(func.count()).select_from(HymnUsage)) == 0
        assert s.scalar(select(func.count()).select_from(Service)) == 0

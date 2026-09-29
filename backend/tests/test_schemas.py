"""The shared hymn and liturgy models, frozen in F §1.3 and created by slice 3
(S "API Models", Testing "Contract and guards"). Slices 4 and 5a import them
unchanged and keep their own tests; these pin the frozen shape."""
import uuid

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from api.main import create_app
from api.schemas import HymnalCode, HymnRef, SectionKey, SlotHymns


def test_extra_fields_rejected_on_hymn_ref_and_slot_hymns():
    with pytest.raises(ValidationError):
        HymnRef(title="Holy, Holy, Holy", audio_url="https://example.org/a.mp3")
    with pytest.raises(ValidationError):
        SlotHymns(opening=None, offertory={"title": "Doxology"})
    with pytest.raises(ValidationError):        # extra inside a nested HymnRef too
        SlotHymns(opening={"title": "Doxology", "slot": "opening"})


def test_title_300_accepted_301_rejected():
    assert len(HymnRef(title="t" * 300).title) == 300
    with pytest.raises(ValidationError):
        HymnRef(title="t" * 301)


def test_number_bounds():
    assert HymnRef(number=0).number == 0
    assert HymnRef(number=100_000).number == 100_000
    for bad in (-1, 100_001):
        with pytest.raises(ValidationError):
            HymnRef(number=bad)


def test_hymnal_length_capped_but_no_pattern():
    with pytest.raises(ValidationError):
        HymnRef(hymnal="H" * 21)
    # Codes that break HymnalCode's pattern are accepted (F §1.3: no pattern on HymnRef).
    for code in ("PH 1990", "X", "gg.2013"):
        assert HymnRef(hymnal=code).hymnal == code


def test_null_hymn_id_and_defaults_accepted():
    ref = HymnRef(hymn_id=None, title="Archived Hymn", number=None, hymnal=None)
    assert ref.hymn_id is None
    assert HymnRef().model_dump() == {"hymn_id": None, "title": "", "number": None, "hymnal": None}
    hymn_id = uuid.uuid4()
    slots = SlotHymns(opening={"hymn_id": str(hymn_id), "title": "x", "number": 1, "hymnal": "GG2013"})
    assert slots.opening.hymn_id == hymn_id
    assert (slots.response, slots.closing) == (None, None)


def test_section_key_rejects_an_unknown_section():
    class Section(BaseModel):
        key: SectionKey

    assert Section(key="prayers_of_the_people").key == "prayers_of_the_people"
    with pytest.raises(ValidationError):
        Section(key="offering")


def test_hymnal_code_pattern_and_models_absent_from_openapi():
    code = TypeAdapter(HymnalCode)
    assert code.validate_python("GG2013") == "GG2013"
    for bad in ("PH 1990", "X", "G" * 21):
        with pytest.raises(ValidationError):
            code.validate_python(bad)
    # No slice-3 route uses them, so the committed snapshot does not change for them.
    schemas = create_app().openapi()["components"]["schemas"]
    assert not {"HymnRef", "SlotHymns"} & set(schemas)

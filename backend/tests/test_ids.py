"""db.ids.as_uuid: malformed ids are a 404, never a 500 (F §2.2 item 5)."""
import uuid

import pytest

from db.ids import as_uuid
from domain_errors import NotFound

ID = uuid.UUID("6f1c2a52-3a8e-4c3e-9d57-2f0b1f6f1a11")


@pytest.mark.parametrize("value", [ID, str(ID)], ids=["uuid", "string"])
def test_as_uuid_accepts_uuid_and_string(value):
    assert as_uuid(value) == ID


@pytest.mark.parametrize("value", [None, "nope", 123, ""], ids=["none", "malformed", "int", "empty"])
def test_as_uuid_raises_not_found_for_bad_input(value):
    with pytest.raises(NotFound) as caught:
        as_uuid(value)
    assert (caught.value.status, caught.value.code, caught.value.message) == (404, "not_found", "Not found.")

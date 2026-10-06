"""email_addresses.normalize_address, the one address rule (slice 5b spec;
slice 5b-1), driven by the shared fixture every caller is tested against."""
import json
from email.message import EmailMessage
from pathlib import Path

import pytest

from email_addresses import InvalidAddress, normalize_address

CASES = json.loads((Path(__file__).parent / "fixtures" / "shared" / "email_addresses.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES["valid"], ids=lambda case: case["raw"].strip()[:40])
def test_a_valid_address_is_trimmed_with_its_domain_lower_cased(case):
    assert normalize_address(case["raw"]) == case["normalized"]
    assert normalize_address(case["normalized"]) == case["normalized"]     # saving it again changes nothing


@pytest.mark.parametrize("raw", CASES["invalid"], ids=lambda raw: raw[:40])
def test_an_invalid_address_is_refused(raw):
    with pytest.raises(InvalidAddress):
        normalize_address(raw)


@pytest.mark.parametrize("raw", ["", "   ", "\t\n"])
def test_a_blank_address_is_refused(raw):
    with pytest.raises(InvalidAddress):
        normalize_address(raw)


def test_every_valid_address_is_exactly_one_recipient_in_a_bcc_header():
    for case in CASES["valid"]:
        message = EmailMessage()
        message["Bcc"] = case["normalized"]
        header = message["Bcc"]
        assert [a.addr_spec for a in header.addresses] == [case["normalized"]], case["raw"]
        assert [g.display_name for g in header.groups] == [None], case["raw"]       # no group syntax
        assert header.defects == (), case["raw"]

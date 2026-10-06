"""email_addresses.normalize_address, the one address rule (slice 5b spec;
slice 5b-1), driven by the shared fixture every caller is tested against."""
import json
from email import message_from_bytes
from email.message import EmailMessage
from email.policy import default
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


# Addresses built to slip a second recipient, a header or a group into a Bcc
# header. Each must be refused, or be exactly one recipient once sent: set as a
# Bcc header, serialized and parsed back, it is itself and nothing else.
ADVERSARIAL = [
    # RFC 2047 encoded-words ("a@b.com, c@d.com" and "x\r\nBcc: evil@x.org" in base64; q-encoding)
    "=?utf-8?b?YUBiLmNvbSwgY0BkLmNvbQ==?=@example.org",
    "=?utf-8?b?eA0KQmNjOiBldmlsQHgub3Jn?=@example.org",
    "=?utf-8?b?YUBiLmNvbSwgY0BkLmNvbQ==?=.x@example.org",
    "x.=?utf-8?q?a=40b.com=2C_c=40d.com?=@example.org",
    "=?utf-8?q?a?=@example.org",
    "a?=b@example.org",
    "a=b?c@example.org",
    # quotes, comments, escapes
    '"a@b.com, c"@example.org',
    '"mary"@example.org',
    "mary(comment)@example.org",
    "mary@example.org(comment)",
    "(c@d.com)mary@example.org",
    "ma\\,ry@example.org",
    "ma\\\"ry@example.org",
    # separators, routes and groups
    "a@b.com, c@d.com",
    "a@b.com,c@d.com",
    "a@b.com; c@d.com",
    "a@b.com;c@d.com",
    "undisclosed:a@b.com;",
    "group: a@b.com, c@d.com;",
    "@route:mary@example.org",
    "mary:jones@example.org",
    "<a@b.com>",
    "Mary <mary@example.org>",
    "mary@example.org>, <c@d.com",
    "mary@[127.0.0.1]",
    # CR, LF, tabs and other whitespace or controls
    "a@b.com\r\nBcc: x@y.com",
    "a@b.com\nBcc: x@y.com",
    "a@b.com\rBcc: x@y.com",
    "mary\t@example.org",
    "mary@exa\tmple.org",
    "ma\x00ry@example.org",
    "ma\x7fry@example.org",
    "mary @example.org",
    "mary@example.org c@d.com",
    # unicode and IDN
    "josé@example.org",
    "anna@bücher.de",
    "mary@exаmple.org",
    "anna@xn--bcher-kva.de",
    "ｍary@example.org",
    # dots
    ".mary@example.org",
    "mary.@example.org",
    "ma..ry@example.org",
    "mary@.example.org",
    "mary@example.org.",
    "mary@example..org",
    # very long
    "a" * 64 + "@" + ".".join(["b" * 63] * 3) + ".org",
    "a" * 65 + "@example.org",
    "a" * 64 + "@" + ".".join(["b" * 63] * 4) + ".org",
    "a@" + "b" * 64 + ".org",
    # plain ones that must keep working
    "mary@example.org",
    "o'brien+bulletin@example.org",
    "a!#$%&'*+/=?^_`{|}~-z@example.org",
]


@pytest.mark.parametrize("raw", ADVERSARIAL + [case["raw"] for case in CASES["valid"]], ids=lambda raw: ascii(raw)[:40])
def test_an_address_is_refused_or_is_exactly_one_recipient_once_sent(raw):
    try:
        address = normalize_address(raw)
    except InvalidAddress:
        return
    message = EmailMessage()
    message["Subject"] = "Bulletin"
    message["Bcc"] = address
    message.set_content("Hello")
    parsed = message_from_bytes(message.as_bytes(), policy=default)
    assert len(parsed.get_all("Bcc")) == 1
    header = parsed["Bcc"]
    assert [a.addr_spec for a in header.addresses] == [address]
    assert [g.display_name for g in header.groups] == [None]
    assert header.defects == ()
    assert parsed.defects == []

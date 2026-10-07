"""bulletin_email (slice 5b spec, "service_output.py additions" and Testing
"test_service_output_email.py"; slice 5b-2): the subject, the default message,
who goes in To and Bcc, and the composed message read back as a mail client
would. The subject and message cases are the shared fixture the frontend's
email.test.ts reads too."""
import datetime
import json
from email import message_from_bytes, policy
from pathlib import Path

import pytest

import bulletin_email
from bulletin_email import Attachment
from printed_bulletin import PDF_MIME
from service_output import DOCX_MIME

CASES = json.loads((Path(__file__).parent / "fixtures" / "shared" / "bulletin_email.json").read_text(encoding="utf-8"))
SENDER = "pastor@example.org"
SUNDAY = datetime.date(2026, 10, 4)
DOCX = Attachment(b"PK\x03\x04docx", "worship_October_04_2026.docx", DOCX_MIME)
PDF = Attachment(b"%PDF-1.7 printed", "printed_bulletin_October_04_2026.pdf", PDF_MIME)


@pytest.mark.parametrize("case", CASES["cases"], ids=lambda case: case["date_iso"])
def test_subject_and_default_message_match_the_shared_fixture(case):
    d = datetime.date.fromisoformat(case["date_iso"])
    assert bulletin_email.bulletin_email_subject(d) == case["subject"]
    assert bulletin_email.default_bulletin_message(d) == case["default_message"]


@pytest.mark.parametrize("recipients, to, bcc", [
    (["mary@example.org"], ("mary@example.org",), ()),
    (["mary@example.org", "office@example.org", "organist@example.org"],
     (SENDER,), ("mary@example.org", "office@example.org", "organist@example.org")),
    (["mary@example.org", "Pastor@Example.org"], (SENDER,), ("mary@example.org",)),
    ([SENDER], (SENDER,), ()),
])
def test_one_recipient_is_in_to_and_several_are_in_bcc_with_the_sender_in_to(recipients, to, bcc):
    assert bulletin_email.plan_bulletin_addressing(SENDER, recipients) == bulletin_email.Addressing(to, bcc)


def _compose(recipients, message=None, attachments=(DOCX,)):
    composed = bulletin_email.compose_bulletin_email(sender=SENDER, recipients=recipients, service_date=SUNDAY,
                                                     message=message, attachments=attachments)
    return message_from_bytes(composed.as_bytes(), policy=policy.default)


def test_the_message_reads_back_with_its_headers_body_and_attachments():
    parsed = _compose(["mary@example.org", "office@example.org"], "  Here it is.\nSee you Sunday.  ", (DOCX, PDF))
    assert (parsed["From"], parsed["To"], parsed["Bcc"]) == (SENDER, SENDER, "mary@example.org, office@example.org")
    assert parsed["Subject"] == "Worship service for October 4, 2026"
    assert parsed.get_body(preferencelist=("plain",)).get_content() == "Here it is.\nSee you Sunday.\n"
    files = [(part.get_filename(), part.get_content_type(), part.get_content()) for part in parsed.iter_attachments()]
    assert files == [("worship_October_04_2026.docx", DOCX_MIME, b"PK\x03\x04docx"),
                     ("printed_bulletin_October_04_2026.pdf", PDF_MIME, b"%PDF-1.7 printed")]
    assert parsed.defects == []


def test_one_recipient_has_no_bcc_and_a_blank_message_gets_the_default():
    for blank in (None, "", "   \n "):
        parsed = _compose(["mary@example.org"], blank, (PDF,))
        assert (parsed["To"], parsed["Bcc"]) == ("mary@example.org", None)
        assert parsed.get_body(preferencelist=("plain",)).get_content() == (
            "Hi! Here's the worship bulletin for this Sunday.\n")
        assert [part.get_filename() for part in parsed.iter_attachments()] == ["printed_bulletin_October_04_2026.pdf"]

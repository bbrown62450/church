"""The one email address rule (slice 5b spec, `email_addresses.normalize_address`).

Every address the app keeps or sends goes through normalize_address: a saved
contact (slice 5b-1, POST and PATCH /contacts) and, from 5b-2, every
recipient of a bulletin email. So an address Settings accepts can always be
emailed, and the shared fixture tests/fixtures/shared/email_addresses.json
pins the rule for both. No dependency (email-validator is not installed);
no FastAPI, Starlette or Streamlit here.
"""
import re

# Characters that never belong in one plain address: they separate lists (", ;"),
# start a group (":", which in a Bcc header would send to the address after it),
# wrap display names or quoted parts ("< > \" ( ) [ ]") or escape ("\\").
_FORBIDDEN = frozenset(',;:<>"()[]\\')
# The local part: dot-separated runs of the characters an unquoted address may use (RFC 5322 dot-atom),
# so no leading, trailing or doubled dot; every address the rule accepts is one plain Bcc recipient.
_LOCAL = re.compile(r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*")
# One domain label: 1-63 ASCII letters, digits or hyphens, not starting or ending with a hyphen.
_LABEL = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?")


class InvalidAddress(ValueError):
    """`raw` is not one plain email address the app can send to."""


def normalize_address(raw: str) -> str:
    """`raw` trimmed, with its domain lower-cased (domains ignore case; the
    local part keeps the case typed), or InvalidAddress unless all hold:
    at most 254 characters, ASCII only (an internationalized domain is refused;
    its punycode form is accepted), no whitespace, control character or any of
    , ; : < > " ( ) [ ] \\, exactly one @, a local part of 1-64 characters made
    of dot-separated runs of letters, digits and ! # $ % & ' * + / = ? ^ _ ` { | } ~ -
    (no leading, trailing or doubled dot), and a domain of at least two labels
    (each 1-63 letters, digits or hyphens, not starting or ending with a hyphen)
    whose last label is at least two letters. So an accepted address is always
    exactly one recipient in a Bcc header.
    """
    address = raw.strip()
    if not address or len(address) > 254 or not address.isascii():
        raise InvalidAddress(raw)
    if any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 or ch in _FORBIDDEN for ch in address):
        raise InvalidAddress(raw)
    if address.count("@") != 1:
        raise InvalidAddress(raw)
    local, _, domain = address.partition("@")
    if not 1 <= len(local) <= 64 or not _LOCAL.fullmatch(local):
        raise InvalidAddress(raw)
    labels = domain.split(".")
    if len(labels) < 2 or not all(_LABEL.fullmatch(label) for label in labels):
        raise InvalidAddress(raw)
    if len(labels[-1]) < 2 or not labels[-1].isalpha():
        raise InvalidAddress(raw)
    return f"{local}@{domain.lower()}"

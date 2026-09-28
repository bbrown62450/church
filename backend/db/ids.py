"""One way to turn an untrusted id into a uuid.UUID (F §2.2 item 5; slice 1).

Every repo and usecase function that slice 1 creates or changes coerces its ids
with as_uuid(), so a malformed id is a 404 `not_found`, never a ValueError or
a SQLAlchemy StatementError (a 500).
"""
import uuid

from domain_errors import NotFound


def as_uuid(value: object) -> uuid.UUID:
    """`value` as a UUID; NotFound("Not found.") for None, malformed text or any other type."""
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str):
        try:
            return uuid.UUID(value)
        except ValueError:
            pass
    raise NotFound("Not found.")

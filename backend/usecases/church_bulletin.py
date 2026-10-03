"""The church's bulletin settings (printed bulletin spec, PR 2a): GET and PUT
/church/bulletin-settings.

get_bulletin_settings reads churches.settings["bulletin"] tolerantly
(read_settings: bulletin_settings.read of the stored texts made Word-safe,
which build_printed uses too, so a value written by any other path never
breaks the Word version). save_bulletin_settings stores the validated body
whole as settings["bulletin"] in one locked read-modify-write
(repos.churches.set_bulletin_settings), so the church's other settings are
never touched; two admins saving at once both succeed and the later save is
what stays (plan clarification 6). It stores the body as read_settings
cleans it and answers what is stored. Every text goes through
archive._xml_safe first (as the service's texts do), so the Word version can
always hold it. A church missing or soft-deleted is require_church's 403. No FastAPI, Starlette or Streamlit here (usecases/__init__.py).
"""
import uuid
from collections.abc import Mapping

import bulletin_settings
from domain_errors import Forbidden
from repos import churches
from usecases import archive

NO_ACCESS_MESSAGE = "You don't have access to this church."      # usecases.church_profile's


def _safe(value: object) -> object:
    if isinstance(value, str):
        return archive._xml_safe(value)
    if isinstance(value, list):
        return [_safe(item) for item in value]
    return value


def read_settings(settings: object) -> bulletin_settings.BulletinSettings:
    """A church's stored settings JSON as the bulletin settings, every text Word-safe."""
    stored = settings.get("bulletin") if isinstance(settings, Mapping) else None
    if not isinstance(stored, Mapping):
        return bulletin_settings.read(None)
    return bulletin_settings.read({"bulletin": {name: _safe(value) for name, value in stored.items()}})


def get_bulletin_settings(church_id: uuid.UUID) -> bulletin_settings.BulletinSettings:
    church = churches.get_church(church_id)
    if church is None:
        raise Forbidden(NO_ACCESS_MESSAGE, details={"reason": "no_church_access"})
    return read_settings(church["settings"])


def save_bulletin_settings(church_id: uuid.UUID, body: Mapping) -> bulletin_settings.BulletinSettings:
    """`body` is PUT's validated body (every field, within its limits)."""
    churches.set_bulletin_settings(church_id, read_settings({"bulletin": body}).to_json())
    return get_bulletin_settings(church_id)

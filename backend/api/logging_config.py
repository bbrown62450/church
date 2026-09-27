"""API logging: every line carries request_id= (F §2.5; ops slice).

configure_logging(level) does three things:
1. maps the level name (DEBUG, INFO, WARNING, ERROR, CRITICAL; any case); an
   unknown name falls back to INFO with a WARNING;
2. installs, once, a log-record factory that sets record.request_id to the id
   of the request being handled, or "-" outside a request. A factory rather
   than a handler filter, so every handler (pytest's caplog too) sees it;
3. if nothing has configured the root logger yet (as under uvicorn), gives it
   one stream handler with LOG_FORMAT at that level.

Never log request bodies, tokens, invite codes, OAuth codes or state, email
bodies, or AI prompts and outputs (F §2.5).
"""
import logging

from api.middleware import current_request_id

LOG_FORMAT = "%(name)s %(levelname)s request_id=%(request_id)s %(message)s"

_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

logger = logging.getLogger(__name__)


def configure_logging(level: str) -> int:
    """Set up API logging at `level` (a name such as "INFO"); returns the level used."""
    resolved = _LEVELS.get((level or "").strip().upper())
    _install_request_id_factory()
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        # `defaults` covers records built without the factory (logging.makeLogRecord).
        handler.setFormatter(logging.Formatter(LOG_FORMAT, defaults={"request_id": "-"}))
        logging.basicConfig(level=resolved or logging.INFO, handlers=[handler])
    if resolved is None:
        logger.warning("LOG_LEVEL='%s' is not a valid level; using INFO.", level)
        return logging.INFO
    return resolved


def _install_request_id_factory() -> None:
    """Wrap the current log-record factory once; calling again is a no-op."""
    previous = logging.getLogRecordFactory()
    if getattr(previous, "adds_request_id", False):
        return

    def factory(*args, **kwargs):
        record = previous(*args, **kwargs)
        record.request_id = current_request_id() or "-"
        return record

    factory.adds_request_id = True
    logging.setLogRecordFactory(factory)

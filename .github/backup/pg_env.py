#!/usr/bin/env python3
"""Turn a Postgres URL into libpq PG* variables without ever echoing it.

backup.yml runs, in this order (the URL goes in on stdin, never in argv):

    python3 .github/backup/pg_env.py --mask <<<"$BACKUP_DATABASE_URL"
    pg_env=$(python3 .github/backup/pg_env.py --exports <<<"$BACKUP_DATABASE_URL")
    eval "$pg_env"

--mask     prints one `::add-mask::` workflow command for each secret part: the
           decoded password, the password as written in the URL, the user name,
           the host and the whole URL. GitHub masks a secret only as a whole
           string, so this hides the parts too. Values are escaped the way the
           runner unescapes them (% -> %25, CR -> %0D, LF -> %0A).
--exports  prints `export PGHOST=... PGPORT=... PGUSER=... PGPASSWORD=...
           PGDATABASE=...`, one per line, each value quoted with shlex.quote,
           for `eval` in bash.

Why: libpq quotes pieces of a malformed URL in its errors (for example
`invalid percent-encoded token: "<part of the password>"`), and GitHub would not
mask such a piece. With PG* variables, psql and pg_dump have no URL to parse.

The URL is read the way SQLAlchemy's make_url reads it, so every URL the app
accepts works here: the same pattern (urllib.parse.urlsplit would cut a raw
`/`, `?` or `#` in the password), and urllib.parse.unquote for the user name,
password and database name. Schemes: postgresql+<driver>, postgresql, postgres.
The port defaults to 5432. Query parameters are ignored: backup.yml sets
PGSSLMODE=require itself.

On any error this prints one generic line to stderr, never any of the input,
and exits non-zero. Standard library only, Python 3.8+: it runs on the
runner's system python3 and on macOS's.
"""
import re
import shlex
import sys
from urllib.parse import unquote

USAGE = "usage: pg_env.py --mask|--exports  (the database URL on stdin)"
ERROR = ("pg_env.py: the database URL could not be parsed "
         "(details withheld because they could include the password)")

# The pattern of sqlalchemy.engine.url._parse_url (SQLAlchemy 2.x), used as it does
# (pattern.match), so this script and the app split a URL in the same places.
_URL = re.compile(
    r"""
        (?P<name>[\w\+]+)://
        (?:
            (?P<username>[^:/]*)
            (?::(?P<password>[^@]*))?
        @)?
        (?:
            (?:
                \[(?P<ipv6host>[^/\?]+)\] |
                (?P<ipv4host>[^/:\?]+)
            )?
            (?::(?P<port>[^/\?]*))?
        )?
        (?:/(?P<database>[^\?]*))?
        (?:\?(?P<query>.*))?
    """,
    re.X,
)
_SCHEME = re.compile(r"postgresql(\+[A-Za-z0-9_]+)?|postgres")
_PORT = re.compile(r"[0-9]{1,5}")
_EXPORTS = (("PGHOST", "host"), ("PGPORT", "port"), ("PGUSER", "user"),
            ("PGPASSWORD", "password"), ("PGDATABASE", "dbname"))


class UrlError(ValueError):
    """The URL cannot be used. The message never contains any part of it."""


def _match(url):
    match = _URL.match(url)
    if match is None or not _SCHEME.fullmatch(match.group("name")):
        raise UrlError("not a postgres URL")
    return match


def parse(url):
    """Return {"host", "port", "user", "password", "dbname"} for a Postgres URL."""
    match = _match(url.strip())
    user, password, dbname = (match.group(g) for g in ("username", "password", "database"))
    host = match.group("ipv4host") or match.group("ipv6host")
    port = match.group("port") or "5432"
    if not (user and password and host and dbname):
        raise UrlError("a part is missing")
    if not _PORT.fullmatch(port) or not 0 < int(port) < 65536:
        raise UrlError("bad port")
    parts = {"host": host, "port": str(int(port)), "user": unquote(user),
             "password": unquote(password), "dbname": unquote(dbname)}
    if any("\x00" in value for value in parts.values()):
        raise UrlError("NUL byte")   # libpq cannot take one, and bash drops it
    return parts


def escape_command_value(value):
    """Escape a workflow-command value as @actions/core does; the runner undoes it."""
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def mask_lines(url):
    url = url.strip()
    parts = parse(url)
    values = [parts["password"], _match(url).group("password"), parts["user"], parts["host"], url]
    unique = [value for i, value in enumerate(values) if value not in values[:i]]
    return ["::add-mask::" + escape_command_value(value) for value in unique]


def export_lines(url):
    parts = parse(url)
    return ["export %s=%s" % (name, shlex.quote(parts[key])) for name, key in _EXPORTS]


def main(argv):
    if argv not in (["--mask"], ["--exports"]):
        sys.stderr.write(USAGE + "\n")
        return 2
    try:
        url = sys.stdin.buffer.read().decode("utf-8")
        lines = mask_lines(url) if argv == ["--mask"] else export_lines(url)
    except Exception:   # no traceback: it could quote the input
        sys.stderr.write(ERROR + "\n")
        return 1
    sys.stdout.buffer.write("".join(line + "\n" for line in lines).encode("utf-8"))
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

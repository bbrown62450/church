"""Write the API's OpenAPI schema to frontend/src/lib/api/openapi.json (F §1.11).

Run from the repo root after any change to a route, a request or response
model, or an error declaration:

    .venv/bin/python backend/scripts/export_openapi.py

then run `npm run gen:api` in frontend/ and commit both files. The output is
create_app().openapi() as JSON with sorted keys, two-space indents and a
trailing newline, so the committed file changes only when the API does.
backend/tests/test_openapi_contract.py fails while the committed file differs
from the live schema. `--out PATH` writes somewhere else (the tests use it).
"""
import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))   # run as a file, sys.path[0] is backend/scripts

from api.main import create_app  # noqa: E402

DEFAULT_OUT = BACKEND.parent / "frontend" / "src" / "lib" / "api" / "openapi.json"


def render_openapi() -> str:
    """The live schema as the committed file's text."""
    return json.dumps(create_app().openapi(), sort_keys=True, indent=2) + "\n"


def write_openapi(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_openapi(), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help="where to write the schema (default: %(default)s)")
    args = parser.parse_args(argv)
    write_openapi(args.out)
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

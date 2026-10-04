import re
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi import APIRouter, Body
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from api import settings as settings_mod
from api.deps import get_verifier
from api.errors import validation_fields
from api.main import create_app
from api.schemas import ChurchOut, ItemList, Page
from api.security import TokenVerifier
from api.settings import _split_origins
from domain_errors import ERROR_CODES
from repos.memberships import add_membership
from tests.jwt_helpers import ISSUER, SIGNING_KEY, make_token

BACKEND = Path(__file__).resolve().parents[1]


def test_health_ok():
    r = TestClient(create_app()).get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_unknown_route_uses_error_shape():
    r = TestClient(create_app()).get("/nope")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_validation_error_uses_error_shape():
    app = create_app()
    router = APIRouter()

    @router.get("/needs-int")
    def needs_int(n: int):
        return {"n": n}

    app.include_router(router)
    r = TestClient(app).get("/needs-int?n=abc")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_request"


def test_unhandled_exception_is_a_generic_500():
    app = create_app()
    router = APIRouter()

    @router.get("/boom")
    def boom():
        raise RuntimeError("secret detail")

    app.include_router(router)
    r = TestClient(app, raise_server_exceptions=False).get("/boom")
    assert r.status_code == 500
    error = r.json()["error"]
    assert set(error) == {"code", "message", "request_id"}
    assert (error["code"], error["message"]) == ("internal_error", "Something went wrong.")
    assert re.fullmatch(r"[0-9a-f]{32}", error["request_id"])
    assert error["request_id"] == r.headers["x-request-id"]
    assert "secret detail" not in r.text


def test_cors_allows_only_configured_origins(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://church.example.app")
    settings_mod.get_settings.cache_clear()
    try:
        client = TestClient(create_app())
        preflight = {"Access-Control-Request-Method": "GET"}
        ok = client.options("/health", headers={"Origin": "https://church.example.app", **preflight})
        assert ok.headers.get("access-control-allow-origin") == "https://church.example.app"
        bad = client.options("/health", headers={"Origin": "https://evil.example", **preflight})
        assert "access-control-allow-origin" not in bad.headers
    finally:
        settings_mod.get_settings.cache_clear()


def test_split_origins_trims_slashes_and_blanks():
    assert _split_origins(" https://a.app/ , ,http://localhost:3000") == (
        "https://a.app",
        "http://localhost:3000",
    )


def test_settings_derive_supabase_urls(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co/")
    settings_mod.get_settings.cache_clear()
    try:
        s = settings_mod.get_settings()
        assert s.jwks_url == "https://abc.supabase.co/auth/v1/.well-known/jwks.json"
        assert s.token_issuer == "https://abc.supabase.co/auth/v1"
    finally:
        settings_mod.get_settings.cache_clear()


def test_lifespan_warns_when_supabase_url_unset(monkeypatch, tmp_db, caplog):
    monkeypatch.setenv("SUPABASE_URL", "")
    settings_mod.get_settings.cache_clear()
    try:
        with caplog.at_level("WARNING"):
            with TestClient(create_app()):
                pass
        assert any(
            "SUPABASE_URL is not set; every authenticated request will return 503."
            in record.message
            for record in caplog.records
        )
    finally:
        settings_mod.get_settings.cache_clear()


def test_api_does_not_import_streamlit():
    code = "import sys, api.main; sys.exit(1 if 'streamlit' in sys.modules else 0)"
    result = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr or "streamlit was imported"


# --- slice 1a: 422 fields, 403 reasons, framework codes, OpenAPI error bodies (F §1.5; S) ---

class _Named(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(max_length=5)


def _app_with_validation_routes():
    """create_app() plus a model body, a free-form object body and a UUID path id."""
    app = create_app()
    router = APIRouter()

    @router.post("/named")
    def named(payload: _Named):
        return {"name": payload.name}

    @router.post("/object")
    def any_object(payload: dict[str, Any] = Body(...)):
        return payload

    @router.get("/items/{item_id}")
    def item(item_id: uuid.UUID):
        return {"id": str(item_id)}

    app.include_router(router)
    return app


@pytest.mark.parametrize("body, fields", [
    ({}, {"name": "Required."}),
    ({"name": "abcdef"}, {"name": "Too long (max 5 characters)."}),
    ({"name": "Grace", "colour": "red"}, {"colour": "Not a valid value."}),
], ids=["missing", "too-long", "extra"])
def test_validation_422_maps_fields(body, fields):
    r = TestClient(_app_with_validation_routes()).post("/named", json=body)
    assert r.status_code == 422
    assert r.json() == {"error": {
        "code": "invalid_request",
        "message": "The request was not valid.",
        "request_id": r.headers["x-request-id"],
        "fields": fields,
    }}


def test_a_whole_body_422_has_no_fields():
    client = TestClient(_app_with_validation_routes())
    not_an_object = client.post("/object", json=["x"])             # location ("body",)
    not_json = client.post("/object", content=b"{", headers={"Content-Type": "application/json"})
    for r in (not_an_object, not_json):
        assert r.status_code == 422
        error = r.json()["error"]
        assert (error["code"], error["message"]) == ("invalid_request", "The request was not valid.")
        assert "fields" not in error


def test_a_path_param_422_strips_path():
    r = TestClient(_app_with_validation_routes()).get("/items/nope")
    assert r.status_code == 422
    assert r.json()["error"]["fields"] == {"item_id": "Not a valid value."}
    # Every source prefix goes; the rest of the location is dotted (F §1.5).
    assert validation_fields([
        {"type": "missing", "loc": ("body", "hymns", "opening", "title")},
        {"type": "string_too_long", "loc": ("query", "q"), "ctx": {"max_length": 3}},
        {"type": "int_parsing", "loc": ("header", "x-count")},
        {"type": "int_parsing", "loc": ("body", "items", 0, "n")},
    ]) == {
        "hymns.opening.title": "Required.",
        "q": "Too long (max 3 characters).",
        "x-count": "Not a valid value.",
        "items.0.n": "Not a valid value.",
    }


@pytest.fixture
def auth_client(tmp_db):
    app = create_app()
    app.dependency_overrides[get_verifier] = lambda: TokenVerifier(
        lambda _token: SIGNING_KEY.public_key(), issuer=ISSUER
    )
    return TestClient(app)


def _auth(email):
    return {"Authorization": f"Bearer {make_token(email=email)}"}


def test_require_church_403_says_no_church_access(auth_client, make_user, make_church):
    make_church(name="Grace", owner_user_id=make_user(email="a@example.com"))
    other = make_church(name="Hope")
    r = auth_client.get("/church", headers={**_auth("a@example.com"), "X-Church-Id": str(other)})
    assert r.status_code == 403
    assert r.json() == {"error": {
        "code": "forbidden",
        "message": "You don't have access to this church.",
        "request_id": r.headers["x-request-id"],
        "details": {"reason": "no_church_access"},
    }}


def test_require_church_without_a_church_header_says_no_church_access(auth_client, make_user, make_church):
    make_church(name="Grace", owner_user_id=make_user(email="a@example.com"))
    missing = auth_client.get("/church", headers=_auth("a@example.com"))
    malformed = auth_client.get("/church", headers={**_auth("a@example.com"), "X-Church-Id": "not-a-uuid"})
    for r in (missing, malformed):
        assert r.status_code == 403
        assert r.json()["error"]["details"] == {"reason": "no_church_access"}


def test_require_admin_403_has_no_reason(auth_client, make_user, make_church):
    church = make_church(name="Grace")
    add_membership(make_user(email="member@example.com"), church, "member")
    r = auth_client.patch("/rubric", json={"prefer_familiar": False},
                          headers={**_auth("member@example.com"), "X-Church-Id": str(church)})
    assert r.status_code == 403
    error = r.json()["error"]
    assert (error["code"], error["message"]) == ("forbidden", "Only church admins can do this.")
    assert "details" not in error


def test_other_http_errors_use_registered_codes():
    app = create_app()
    router = APIRouter()

    @router.get("/status/{status}")
    def fail_with(status: int):
        raise StarletteHTTPException(status_code=status, detail="upstream said: secret" if status >= 500 else None)

    app.include_router(router)
    client = TestClient(app)
    cases = [("GET", "/status/400", 400, "bad_request"), ("POST", "/health", 405, "method_not_allowed"),
             ("GET", "/status/418", 418, "bad_request"), ("GET", "/status/502", 502, "internal_error")]
    for method, path, status, code in cases:
        r = client.request(method, path)
        assert (r.status_code, r.json()["error"]["code"]) == (status, code), path
        assert code in ERROR_CODES
    assert client.get("/status/418").json()["error"]["message"] == "I'm a Teapot"
    server = client.get("/status/502")
    assert server.json()["error"]["message"] == "Something went wrong."
    assert "secret" not in server.text


def test_routes_document_the_error_body():
    schema = create_app().openapi()
    expected = {
        ("/me", "get"): {"401", "422", "503"},
        ("/church", "get"): {"401", "403", "422", "503"},
        ("/rubric", "get"): {"401", "403", "422", "503"},
        ("/rubric", "patch"): {"401", "403", "422", "503"},
        ("/churches", "post"): {"401", "422", "429", "503"},
        ("/invites/preview", "post"): {"400", "401", "422", "503"},
        ("/invites/accept", "post"): {"400", "401", "422", "503"},
        ("/translations", "get"): {"401", "422", "503"},
        ("/lectionary/readings", "get"): {"401", "422", "429", "502", "503", "504"},
        ("/scripture/passages", "post"): {"401", "422", "429", "503"},
        ("/hymnals", "get"): {"401", "403", "422", "503"},
        ("/hymns", "get"): {"401", "403", "422", "503"},
        ("/hymns/scripture-matches", "post"): {"401", "403", "422", "503"},
        ("/hymns/suggestions", "post"): {"401", "403", "422", "429", "502", "503", "504"},
        ("/liturgy/config", "get"): {"401", "422", "503"},
        ("/liturgy/generate", "post"): {"401", "403", "404", "422", "429", "503"},
        ("/liturgy/review", "post"): {"401", "403", "422", "503"},
        ("/liturgy/revise", "post"): {"401", "403", "422", "429", "502", "503", "504"},
    }
    for (path, method), statuses in expected.items():
        responses = schema["paths"][path][method]["responses"]
        assert set(responses) - {"200", "201"} == statuses, (path, method)   # minus the success status
        for status in statuses:
            assert responses[status]["content"]["application/json"]["schema"] == {
                "$ref": "#/components/schemas/ErrorBody"}
    schemas = schema["components"]["schemas"]
    assert "HTTPValidationError" not in schemas            # FastAPI's default 422 shape is not ours
    assert set(schemas["ErrorDetail"]["required"]) == {"code", "message", "request_id"}


def test_church_out_role_is_a_literal():
    with pytest.raises(ValidationError):
        ChurchOut(id=uuid.uuid4(), name="Grace", role="pastor")
    role = create_app().openapi()["components"]["schemas"]["ChurchOut"]["properties"]["role"]
    assert role["enum"] == ["owner", "admin", "member"]


def test_page_and_item_list_shapes():
    church = ChurchOut(id=uuid.UUID(int=1), name="Grace", role="owner")
    page = Page[ChurchOut](items=[church], total=3, limit=1, offset=0)
    assert page.model_dump(mode="json") == {
        "items": [{"id": "00000000-0000-0000-0000-000000000001", "name": "Grace", "role": "owner"}],
        "total": 3, "limit": 1, "offset": 0,
    }
    assert ItemList[str](items=["a", "b"]).model_dump() == {"items": ["a", "b"]}
    with pytest.raises(ValidationError):
        Page[ChurchOut](items=[], total=0, limit=50)        # offset is required


# --- Task 11: no create_all in the lifespan; revision and RLS startup checks ---
import logging
import uuid

import pytest
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import text

import db.schema_check
from db.schema_check import RevisionState, rls_disabled_tables, run_startup_checks

SCHEMA_HEAD = "0007_bulletin_images"
BEHIND_WARNING = f"schema revision None != head {SCHEMA_HEAD}"


@pytest.fixture
def fresh_sqlite(tmp_path, monkeypatch):
    """A development app on an empty SQLite file: no tables and no alembic_version."""
    from db import reset_engine_for_tests

    monkeypatch.setenv("APP_ENV", "development")
    settings_mod.get_settings.cache_clear()
    engine = reset_engine_for_tests(f"sqlite:///{tmp_path / 'fresh.db'}")
    yield engine
    engine.dispose()
    settings_mod.get_settings.cache_clear()


def _schema_check_records(caplog):
    return [(r.levelno, r.getMessage()) for r in caplog.records if r.name == "db.schema_check"]


def test_lifespan_creates_no_tables(fresh_sqlite):
    with TestClient(create_app()):
        pass
    assert sa_inspect(fresh_sqlite).get_table_names() == []


def test_startup_warns_on_a_revision_mismatch_without_errors(fresh_sqlite, caplog):
    """The WARNING names head 0004, so the check found the scripts; no ERROR means it did not fail."""
    app = create_app()
    with caplog.at_level(logging.INFO):
        with TestClient(app):
            pass
    assert _schema_check_records(caplog) == [(logging.WARNING, BEHIND_WARNING)]
    assert [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR] == []
    assert app.state.schema_state == RevisionState(None, SCHEMA_HEAD, "behind")


def test_rls_check_is_skipped_on_sqlite(fresh_sqlite, monkeypatch):
    calls = []
    monkeypatch.setattr(db.schema_check, "rls_disabled_tables", lambda conn: calls.append(conn) or [])
    with TestClient(create_app()):
        pass
    assert calls == []


def test_production_logs_behind_at_error(fresh_sqlite, caplog):
    """In production a behind schema is an ERROR (and /health/ready's gate turns it into a 503)."""
    with caplog.at_level(logging.INFO):
        state = run_startup_checks(fresh_sqlite, is_production=True)
    assert state == RevisionState(None, SCHEMA_HEAD, "behind")
    assert _schema_check_records(caplog) == [(logging.ERROR, BEHIND_WARNING)]


def test_a_failing_schema_check_logs_error_and_starts(fresh_sqlite, monkeypatch, caplog):
    def broken(_conn):
        raise RuntimeError("password=s3cret host=db.internal")

    monkeypatch.setattr(db.schema_check, "revision_state", broken)
    app = create_app()
    with caplog.at_level(logging.INFO):
        with TestClient(app) as client:
            assert client.get("/health").status_code == 200
    errors = [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]
    assert errors == ["Schema revision check failed: RuntimeError"]    # the class only
    assert "s3cret" not in caplog.text
    assert app.state.schema_state == RevisionState(None, None, "unknown")


@pytest.mark.postgres
def test_rls_check_names_tables_without_rls(pg_db, caplog):
    """After the CI alembic cycle 0003 has enabled RLS on every public table, so
    the test adds its own table without RLS and drops it again."""
    probe = f"wsb_rls_probe_{uuid.uuid4().hex[:8]}"
    with pg_db.begin() as conn:
        conn.execute(text(f"CREATE TABLE public.{probe} (id integer PRIMARY KEY)"))
    try:
        with pg_db.connect() as conn:
            assert rls_disabled_tables(conn) == [probe]
        with caplog.at_level(logging.INFO):
            state = run_startup_checks(pg_db, is_production=False)
        assert state == RevisionState(SCHEMA_HEAD, SCHEMA_HEAD, "current")
        assert _schema_check_records(caplog) == [
            (logging.WARNING, f"Row-level security is off on: {probe}")]
    finally:
        with pg_db.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS public.{probe}"))

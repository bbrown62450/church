import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter
from fastapi.testclient import TestClient

from api import settings as settings_mod
from api.main import create_app
from api.settings import _split_origins

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
    assert r.json() == {"error": {"code": "internal_error", "message": "Something went wrong."}}
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

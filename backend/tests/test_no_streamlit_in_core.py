"""The API imports auth and tenancy, and the API must run without Streamlit."""
import subprocess
import sys
from pathlib import Path

# The directory that holds tests/ — the repo root now, backend/ after the move.
CODE_DIR = Path(__file__).resolve().parents[1]


def test_auth_and_tenancy_do_not_import_streamlit():
    code = "import sys, auth, tenancy; sys.exit(1 if 'streamlit' in sys.modules else 0)"
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=CODE_DIR, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr or "streamlit was imported"


def test_usecases_package_imports_no_fastapi_or_streamlit():
    # usecases (including usecases.onboarding), domain_errors, db.ids,
    # timezones and slice 2's platform modules (cache, integrations.http) are
    # below the API layer (F §2.2).
    code = ("import sys, usecases, usecases.onboarding, usecases.church_profile, usecases.lectionary, usecases.passages, vanderbilt_lectionary, domain_errors, db.ids, timezones, "
            "cache, integrations.http, "
            "token_bucket, integrations.budget, scripture_refs, scripture_fetcher, integrations.openai_client, hymn_search, hymn_suggest, usecases.hymns, "
            "liturgy_config, prayer_library, liturgy_prompts, usecases.liturgy, review_checks; "
            "bad = sorted({m.split('.')[0] for m in sys.modules} & {'fastapi', 'starlette', 'streamlit'}); "
            "print(bad); sys.exit(1 if bad else 0)")
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=CODE_DIR, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr


# Imports every module in api/routes, builds the app, and fails if a routes
# module's router is not mounted (so "every router" stays true as slices add
# routers) or if anything on that path imported streamlit (F §2.2 item 6).
_EVERY_ROUTER = """
import importlib, pkgutil, sys
import api.main, api.routes
from fastapi.routing import iter_route_contexts
modules = [importlib.import_module(f"api.routes.{m.name}")
           for m in pkgutil.iter_modules(api.routes.__path__)]
served = {ctx.endpoint for ctx in iter_route_contexts(api.main.create_app().routes)}
unmounted = [m.__name__ for m in modules
             if not any(route.endpoint in served for route in m.router.routes)]
print("modules:", sorted(m.__name__ for m in modules))
print("unmounted:", unmounted)
print("streamlit imported:", "streamlit" in sys.modules)
sys.exit(1 if unmounted or "streamlit" in sys.modules or not modules else 0)
"""


def test_api_main_with_every_router_does_not_import_streamlit():
    result = subprocess.run(
        [sys.executable, "-c", _EVERY_ROUTER], cwd=CODE_DIR, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "unmounted: []" in result.stdout
    assert "'api.routes.me'" in result.stdout and "'api.routes.rubric'" in result.stdout
    assert "'api.routes.churches'" in result.stdout
    assert "'api.routes.invites'" in result.stdout
    assert "'api.routes.reference'" in result.stdout

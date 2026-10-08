"""Every API route declares who may call it (F §1.2 rule 4; S test_route_guards).

The walker lists every (method, path) the app serves with the full set of
dependencies FastAPI will run for it, and flags a route unless:
- it is in PUBLIC (the probes and FastAPI's built-in docs), or
- it is in USER_SCOPED and depends on get_current_user (and never on
  require_church: user-scoped routes ignore X-Church-Id), or
- require_church is somewhere in its dependency tree (require_admin depends
  on it, so admin routes pass too).

FastAPI 0.141 keeps included routers nested (app.routes holds
`_IncludedRouter`s with no path), so the walk goes through
fastapi.routing.iter_route_contexts, and reads `ctx.dependant`, which, unlike
`ctx.route.dependant`, includes the dependencies given to include_router(...)
(checked on 0.141.1; the fastapi==0.141.* pin keeps it stable).

ADMIN_ONLY pins the routes only owners and admins may call: each must have
require_admin in its tree, and every route that has it must be listed. A
usecase that re-reads the role under the church-row lock would still refuse
a member if a route's guard were weakened to require_church, so no request
test notices that; this does (6a-3a build review 4: PUT
/church/liturgy-prompts and PATCH /rubric).

Every slice that adds a user-scoped route adds it to USER_SCOPED in the same PR
(1b: POST /churches, POST /invites/preview, POST /invites/accept;
2a: GET /lectionary/readings, POST /scripture/passages, GET /translations;
4a: GET /liturgy/config; 5b-2: the four /gmail-connection routes).
"""
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, FastAPI
from fastapi.routing import iter_route_contexts

from api.deps import get_current_user, require_admin, require_church
from api.main import create_app

PUBLIC = {
    ("GET", "/health"),
    ("GET", "/health/ready"),
    ("GET", "/openapi.json"),
    ("GET", "/docs"),
    ("GET", "/docs/oauth2-redirect"),
    ("GET", "/redoc"),
}
USER_SCOPED = {
    ("GET", "/me"),
    ("POST", "/churches"),
    ("POST", "/invites/preview"),
    ("POST", "/invites/accept"),
    ("GET", "/translations"),
    ("GET", "/lectionary/readings"),
    ("POST", "/scripture/passages"),
    ("GET", "/liturgy/config"),
    ("GET", "/gmail-connection"),
    ("POST", "/gmail-connection/auth-url"),
    ("POST", "/gmail-connection"),
    ("DELETE", "/gmail-connection"),
}
ADMIN_ONLY = {
    ("PATCH", "/church"),
    ("PUT", "/church/bulletin-settings"),
    ("PUT", "/church/liturgy-prompts"),
    ("PATCH", "/rubric"),
    ("POST", "/contacts"),
    ("PATCH", "/contacts/{contact_id}"),
    ("DELETE", "/contacts/{contact_id}"),
    ("GET", "/hymnal-sources"),
    ("POST", "/hymnals"),
    ("DELETE", "/hymnals/{code}"),
    ("DELETE", "/hymns/{hymn_id}"),
}
CHURCH_SCOPED_TODAY = {("GET", "/church"), ("GET", "/rubric"), ("PATCH", "/rubric")}


def _calls(dependant: Any) -> set[Callable[..., Any]]:
    """Every callable in a dependency tree (sub-dependencies included)."""
    found: set[Callable[..., Any]] = set()
    stack = list(dependant.dependencies) if dependant is not None else []
    while stack:
        dep = stack.pop()
        if dep.call is not None:
            found.add(dep.call)
        stack.extend(dep.dependencies)
    return found


def route_dependencies(app: FastAPI) -> dict[tuple[str, str], set[Callable[..., Any]]]:
    """(method, path) -> every dependency FastAPI runs for it. HEAD is ignored
    (Starlette adds it to GET routes); a route with no methods (a mount) is "ANY"."""
    routes: dict[tuple[str, str], set[Callable[..., Any]]] = {}
    for ctx in iter_route_contexts(app.routes):
        calls = _calls(getattr(ctx, "dependant", None))   # None: a plain Starlette route
        for method in sorted(set(ctx.methods or {"ANY"}) - {"HEAD"}):
            routes.setdefault((method, ctx.path), set()).update(calls)
    return routes


def unguarded_routes(app: FastAPI) -> list[tuple[str, str]]:
    """The routes outside PUBLIC and USER_SCOPED with no require_church in their tree."""
    return sorted(
        route for route, calls in route_dependencies(app).items()
        if route not in PUBLIC and route not in USER_SCOPED and require_church not in calls
    )


def test_every_non_public_route_requires_a_church():
    routes = route_dependencies(create_app())
    assert CHURCH_SCOPED_TODAY <= routes.keys()   # the walker really sees the included routers
    assert unguarded_routes(create_app()) == []


def test_user_scoped_routes_require_a_user():
    routes = route_dependencies(create_app())
    for route in sorted(USER_SCOPED):
        assert get_current_user in routes[route], f"{route} does not depend on get_current_user"
        assert require_church not in routes[route], f"{route} is user-scoped but reads X-Church-Id"


def test_admin_routes_require_an_admin():
    routes = route_dependencies(create_app())
    for route in sorted(ADMIN_ONLY):
        assert require_admin in routes[route], f"{route} is admin-only but does not depend on require_admin"
    assert {route for route, calls in routes.items() if require_admin in calls} == ADMIN_ONLY


def test_allowlists_name_real_routes():
    """A renamed or removed route must leave the allowlists too, or they hide nothing."""
    served = set(route_dependencies(create_app()))
    assert PUBLIC - served == set()
    assert USER_SCOPED - served == set()
    assert ADMIN_ONLY - served == set()
    assert PUBLIC.isdisjoint(USER_SCOPED)
    assert ADMIN_ONLY.isdisjoint(PUBLIC | USER_SCOPED)


def _church_scoped_ok(church=Depends(require_church)) -> dict:
    return {}


def test_the_walker_flags_an_unguarded_route():
    app = create_app()

    @app.get("/unguarded")
    def unguarded() -> dict:
        return {}

    nested = APIRouter()

    @nested.post("/user-only")
    def user_only(user=Depends(get_current_user)) -> dict:
        return {}

    nested.add_api_route("/guarded", _church_scoped_ok, methods=["GET"])
    app.include_router(nested, prefix="/nested")

    assert unguarded_routes(app) == [("GET", "/unguarded"), ("POST", "/nested/user-only")]


def test_the_walker_sees_router_level_dependencies():
    app = create_app()
    on_include = APIRouter()
    on_include.add_api_route("/include-level", lambda: {}, methods=["DELETE"])
    app.include_router(on_include, dependencies=[Depends(require_church)])

    on_router = APIRouter(dependencies=[Depends(require_admin)])
    on_router.add_api_route("/router-level", lambda: {}, methods=["PUT"])
    app.include_router(on_router)

    routes = route_dependencies(app)
    assert require_church in routes[("DELETE", "/include-level")]
    assert require_church in routes[("PUT", "/router-level")]   # through require_admin
    assert unguarded_routes(app) == []

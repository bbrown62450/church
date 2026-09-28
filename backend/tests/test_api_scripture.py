"""POST /scripture/passages over HTTP (S API row 3, Status rules, Rate-limit
buckets `scripture`, Upstream budgets, Testing "test_api_scripture.py"; AC5, AC7, AC9).

Upstream calls are answered by httpx.MockTransport through
integrations.http.set_http_for_tests (the _no_network guard stays active).
Rate-limit tests take `limiter_clock` (a FakeClock) and never advance it
during a burst, so every wait is exact: one `scripture` token comes back
every 5 s.
"""
import httpx
import pytest

from api import settings as settings_mod
from integrations import http
from tests.api_helpers import auth_headers, make_api_client

EMAIL = "pastor@example.com"
ALLOWED_ORIGIN = "https://church.example.app"
PATH = "/scripture/passages"


def _ref(book: str, n: int) -> str:
    """'{book} 1:1; 1:2; …; 1:n': n parts, the book carried into each (split_parts)."""
    return "; ".join([f"{book} 1:1"] + [f"1:{verse}" for verse in range(2, n + 1)])


TWENTY_PARTS = [_ref("Genesis", 5), _ref("Exodus", 5), _ref("Leviticus", 5), _ref("Numbers", 5)]
TWENTY_ONE_PARTS = TWENTY_PARTS[:3] + [_ref("Numbers", 6)]


@pytest.fixture(autouse=True)
def _no_esv_key(monkeypatch):
    monkeypatch.delenv("ESV_API_KEY", raising=False)


@pytest.fixture
def calls():
    """Install a bible-api fake and return the decoded paths it was asked for.

    Nahum is not in the fake's Bible (404); chapter 99 is a server error (500);
    anything else is "Text of {path}."."""
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path[1:]
        seen.append(path)
        if "nahum" in path:
            return httpx.Response(404, json={"error": "not found"})
        if " 99:" in path:
            return httpx.Response(500)
        return httpx.Response(200, json={"text": f"Text of {path}."})

    http.set_http_for_tests(http.build_client(transport=httpx.MockTransport(handler)))
    return seen


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def cors_client(tmp_db, monkeypatch):
    """A client whose app allows exactly ALLOWED_ORIGIN (test_api_app's pattern)."""
    monkeypatch.setenv("CORS_ORIGINS", ALLOWED_ORIGIN)
    settings_mod.get_settings.cache_clear()
    yield make_api_client()
    settings_mod.get_settings.cache_clear()


def _post(client, refs, translation="web", email=EMAIL, **extra):
    return client.post(PATH, json={"refs": refs, "translation": translation, **extra},
                       headers=auth_headers(email))


def _invalid(response) -> dict:
    assert response.status_code == 422, response.text
    error = response.json()["error"]
    assert error["code"] == "invalid_request"
    return error


def _assert_rate_limited(response, seconds: int) -> None:
    assert response.status_code == 429, response.text
    error = response.json()["error"]
    assert (error["code"], error["message"]) == (
        "rate_limited", f"Too many requests. Try again in {seconds} seconds.")
    assert error["details"] == {"retry_after_seconds": seconds}
    assert response.headers["Retry-After"] == str(seconds)
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN


def test_requires_token_401(client, calls):
    r = client.post(PATH, json={"refs": ["John 3:16"], "translation": "web"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthenticated"
    assert calls == []


def test_200_statuses(client, calls):
    refs = ["  John 3:16  ", "Nahum 9:9", "Luke 1:1-4; 99:1 or Mark 1:1", "Isaiah 50:4-9a; Nahum 1:1"]
    r = _post(client, refs)
    assert r.status_code == 200, r.text
    assert r.json() == {
        "translation": "web",
        "translation_label": "World English Bible (WEB)",
        "passages": [
            {"reference": "John 3:16", "status": "ok",
             "sections": [{"reference": "John 3:16", "status": "ok", "text": "Text of john 3:16."}]},
            {"reference": "Nahum 9:9", "status": "not_found",
             "sections": [{"reference": "Nahum 9:9", "status": "not_found", "text": None}]},
            {"reference": "Luke 1:1-4; 99:1 or Mark 1:1", "status": "unavailable",
             "sections": [
                 {"reference": "Luke 1:1-4; 99:1", "status": "unavailable", "text": "Text of luke 1:1-4."},
                 {"reference": "Mark 1:1", "status": "ok", "text": "Text of mark 1:1."}]},
            {"reference": "Isaiah 50:4-9a; Nahum 1:1", "status": "not_found",
             "sections": [{"reference": "Isaiah 50:4-9a; Nahum 1:1", "status": "not_found",
                           "text": "Text of isaiah 50:4-9."}]},
        ],
    }
    assert sorted(calls) == sorted(["john 3:16", "nahum 9:9", "luke 1:1-4", "luke 99:1", "mark 1:1",
                                    "isaiah 50:4-9", "nahum 1:1"])


def test_422_five_refs(client, calls):
    error = _invalid(_post(client, ["John 3:16"] * 5))
    assert error["fields"] == {"refs": "Not a valid value."}


def test_422_ref_201_chars(client, calls):
    error = _invalid(_post(client, ["J" * 201]))
    assert error["fields"] == {"refs.0": "Too long (max 200 characters)."}
    assert _post(client, ["John 3:16"], translation="x" * 21).json()["error"]["fields"] == {
        "translation": "Too long (max 20 characters)."}


def test_422_empty_refs(client, calls):
    error = _invalid(_post(client, []))
    assert error["message"] == "Enter a scripture reference."
    assert error["fields"] == {"refs": "Enter a scripture reference."}


def test_422_blank_ref(client, calls):
    for refs in (["John 3:16", "   "], [";"], [" ; "]):
        error = _invalid(_post(client, refs))
        assert error["fields"] == {"refs": "Enter a scripture reference."}, refs
    assert calls == []


def test_422_twenty_one_parts(client, calls):
    error = _invalid(_post(client, TWENTY_ONE_PARTS))
    assert error["message"] == "Too many passages in one request."
    assert error["fields"] == {"refs": "Too many passages in one request."}
    assert calls == []


def test_422_unknown_translation(client, calls):
    for translation in ("klingon", "esv"):             # ESV without its key is unavailable
        error = _invalid(_post(client, ["John 3:16"], translation=translation))
        assert error["fields"] == {"translation": "Unknown or unavailable translation."}, translation


def test_422_extra_field(client, calls):
    error = _invalid(_post(client, ["John 3:16"], church_id="x"))
    assert error["fields"] == {"church_id": "Not a valid value."}
    missing = _invalid(client.post(PATH, json={"refs": ["John 3:16"]}, headers=auth_headers(EMAIL)))
    assert missing["fields"] == {"translation": "Required."}


def test_61st_one_part_call_429(cors_client, calls, limiter_clock):
    """60 parts per 5 minutes: the 61st one-part call waits 5 s for one token.
    Only the first call reaches bible-api (the rest are cache hits), and the
    429 fetches nothing."""
    headers = {**auth_headers(EMAIL), "Origin": ALLOWED_ORIGIN}
    body = {"refs": ["John 3:16"], "translation": "web"}
    for n in range(60):
        assert cors_client.post(PATH, json=body, headers=headers).status_code == 200, n
    # A part never fetched before, so a 429 that still loaded would show up in `calls`.
    _assert_rate_limited(cors_client.post(PATH, json={"refs": ["Mark 1:1"], "translation": "web"},
                                          headers=headers), 5)
    assert calls == ["john 3:16"]


def test_21st_three_part_call_429(cors_client, calls, limiter_clock):
    """Charged per part: after 20 three-part calls the 21st needs 3 tokens, 15 s."""
    headers = {**auth_headers(EMAIL), "Origin": ALLOWED_ORIGIN}
    body = {"refs": [_ref("Genesis", 3)], "translation": "web"}
    for n in range(20):
        assert cors_client.post(PATH, json=body, headers=headers).status_code == 200, n
    _assert_rate_limited(cors_client.post(PATH, json=body, headers=headers), 15)

    limiter_clock.advance(15)
    assert cors_client.post(PATH, json=body, headers=headers).status_code == 200


def test_budget_shared_across_users(client, calls, budget_clock):
    """The bible-api budget (15 per 30 s) is process-wide (S :892): user A's 15
    parts spend it, so user B's uncached part is `unavailable` with no upstream
    call, while a part A already loaded is still served from the cache."""
    a_refs = [_ref("Genesis", 4), _ref("Exodus", 4), _ref("Leviticus", 4), _ref("Numbers", 3)]
    a = _post(client, a_refs, email="a@example.com")
    assert a.status_code == 200, a.text
    assert [p["status"] for p in a.json()["passages"]] == ["ok"] * 4
    assert len(calls) == 15

    b = _post(client, ["Ruth 1:1", "Genesis 1:1"], email="b@example.com")
    assert b.status_code == 200, b.text
    ruth, genesis = b.json()["passages"]
    assert ruth == {"reference": "Ruth 1:1", "status": "unavailable",
                    "sections": [{"reference": "Ruth 1:1", "status": "unavailable", "text": None}]}
    assert genesis["status"] == "ok"
    assert genesis["sections"][0]["text"] == "Text of genesis 1:1."
    assert len(calls) == 15                              # nothing sent for B

    budget_clock.advance(2)                              # one bible-api token back (15 per 30 s)
    assert _post(client, ["Ruth 1:1"], email="b@example.com").json()["passages"][0]["status"] == "ok"
    assert calls[-1] == "ruth 1:1"


def test_422_charges_nothing(cors_client, calls, limiter_clock):
    """Validation runs before the charge: after one of each 422, the whole 60
    tokens are still there (three 20-part calls), and only then is a call 429."""
    headers = {**auth_headers(EMAIL), "Origin": ALLOWED_ORIGIN}
    invalid_bodies = [
        {"refs": ["John 3:16"] * 5, "translation": "web"},          # Pydantic: more than 4 refs
        {"refs": ["J" * 201], "translation": "web"},                # Pydantic: a ref over 200 characters
        {"refs": ["John 3:16"], "translation": "web", "extra": 1},  # Pydantic: extra="forbid"
        {"refs": [], "translation": "web"},                         # usecase: no refs
        {"refs": [";"], "translation": "web"},                      # usecase: a ref with no parts
        {"refs": ["John 3:16"], "translation": "klingon"},          # usecase: translation
        {"refs": TWENTY_ONE_PARTS, "translation": "web"},           # usecase: 21 parts
    ]
    for body in invalid_bodies:
        assert cors_client.post(PATH, json=body, headers=headers).status_code == 422, body
    assert calls == []

    for n in range(3):
        r = cors_client.post(PATH, json={"refs": TWENTY_PARTS, "translation": "web"}, headers=headers)
        assert r.status_code == 200, (n, r.text)
    _assert_rate_limited(
        cors_client.post(PATH, json={"refs": ["John 3:16"], "translation": "web"}, headers=headers), 5)

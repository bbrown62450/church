"""GET /voices over HTTP (Voices V1 spec "The API").

User-scoped reference data, like GET /translations: a token is required, X-Church-Id is ignored,
no AI and no database work beyond the sign-in. The answer is the shipped Catena (test_catena_data.py
pins it), so these tests read the real files.
"""
import pytest

from tests.api_helpers import auth_headers, make_api_client

EMAIL = "pastor@example.com"


@pytest.fixture
def client(tmp_db):
    return make_api_client()


def test_requires_a_token(client):
    r = client.get("/voices", params={"reference": "Matthew 22:15-22"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthenticated"


def test_the_fathers_on_matthew_22_15_22_as_printed(client):
    # X-Church-Id is ignored: a malformed one is neither checked nor a 403.
    r = client.get("/voices", params={"reference": "Matthew 22:15-22"},
                   headers={**auth_headers(EMAIL), "X-Church-Id": "not-a-uuid"})
    assert r.status_code == 200, r.text
    assert r.headers["cache-control"] == "private, max-age=3600"
    body = r.json()
    assert (body["reference"], body["gospel"], body["quotation_count"]) == ("Matthew 22:15-22", "Matthew", 19)
    assert body["credit"].startswith("From the Catena Aurea of Thomas Aquinas, vol. I, St. Matthew, "
                                     "translated by Mark Pattison, edited by John Henry Newman")
    (section,) = body["sections"]
    assert {k: v for k, v in section.items() if k != "comments"} == {
        "id": "matthew-22-15-22", "reference": "Matthew 22:15-22", "pages": "748-752",
        "volume": "Vol. I, St. Matthew, Part III (1842)", "status": "checked",
        "scan_url": "https://archive.org/details/catenaurecommpt301thomuoft/page/n19/mode/1up"}
    assert len(section["comments"]) == 19
    assert section["comments"][3] == {
        "label": "Chrys.", "father": "Chrysostom", "work": "Chrys. Hom. lxx.",
        "text": "They send their disciples and Herod's soldiers together, that whatever opinion He might give "
                "might be found fault with. Yet would they rather have had Him say somewhat against the "
                "Herodians; for being themselves afraid to lay hands on Him because of the populace, they "
                "sought to bring Him into danger through His liability to pay tribute.",
        "notes": [], "printed_label": None}


def test_the_catenas_own_linking_words_come_under_no_father_and_are_not_counted(client):
    r = client.get("/voices", params={"reference": "Matthew 22:34-46"}, headers=auth_headers(EMAIL))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["quotation_count"] == 36
    assert [len(s["comments"]) for s in body["sections"]] == [24, 13]
    assert body["sections"][0]["comments"][18] == {
        "label": None, "father": None, "work": None, "notes": [], "printed_label": None,
        "text": "It follows, *On these two commandments hang all the Law and the Prophets.*"}


def test_a_section_not_yet_checked_comes_without_text(client):
    r = client.get("/voices", params={"reference": "Matt 22:20-25"}, headers=auth_headers(EMAIL))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["quotation_count"] == 19
    assert [(s["id"], s["status"], len(s["comments"])) for s in body["sections"]] == [
        ("matthew-22-15-22", "checked", 19), ("matthew-22-23-33", "unchecked", 0)]
    assert body["sections"][1]["pages"] == "752-760"


def test_another_gospel_with_nothing_checked_yet(client):
    r = client.get("/voices", params={"reference": "John 20:19-31"}, headers=auth_headers(EMAIL))
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["gospel"], body["quotation_count"]) == ("John", 0)
    assert [s["reference"] for s in body["sections"]] == ["John 20:19-25", "John 20:26-31"]
    assert "translator not named in the volume" in body["credit"]


@pytest.mark.parametrize("params, field, message", [
    ({"reference": "Isaiah 45:1-7"}, "reference", "Choose a passage from Matthew, Mark, Luke or John."),
    ({"reference": "Psalm 96"}, "reference", "Choose a passage from Matthew, Mark, Luke or John."),
    ({"reference": "x" * 201}, "reference", "Too long (max 200 characters)."),
    ({}, "reference", "Required."),
])
def test_a_reference_that_is_not_a_gospel_passage_is_a_422(client, params, field, message):
    r = client.get("/voices", params=params, headers=auth_headers(EMAIL))
    assert r.status_code == 422, r.text
    assert r.json()["error"]["fields"] == {field: message}

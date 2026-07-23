import scripture_fetcher as sf


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_available_translations_excludes_esv_without_key(monkeypatch):
    monkeypatch.delenv("ESV_API_KEY", raising=False)
    ids = [tid for tid, _ in sf.available_translations()]
    assert "web" in ids and "kjv" in ids
    assert "esv" not in ids            # hidden until a key is configured


def test_available_translations_includes_esv_with_key(monkeypatch):
    monkeypatch.setenv("ESV_API_KEY", "test-key")
    ids = [tid for tid, _ in sf.available_translations()]
    assert "esv" in ids


def test_translation_label():
    assert "World English Bible" in sf.translation_label("web")
    assert "ESV" in sf.translation_label("esv")
    assert sf.translation_label(None) == sf.translation_label("web")
    assert sf.translation_label("unknown-id") == "unknown-id"


def test_esv_routing_uses_esv_endpoint(monkeypatch):
    monkeypatch.setenv("ESV_API_KEY", "test-key")
    seen = {}

    def fake_get(url, params=None, headers=None, timeout=None):
        seen["url"] = url
        seen["headers"] = headers or {}
        return _FakeResp({"passages": ["For God so loved the world. (ESV)"]})

    monkeypatch.setattr(sf.httpx, "get", fake_get)
    text = sf.get_passage_text("John 3:16", translation="esv")
    assert text == "For God so loved the world. (ESV)"
    assert seen["url"] == sf.ESV_API_BASE
    assert seen["headers"].get("Authorization") == "Token test-key"


def test_bible_api_routing_uses_bible_api(monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=None):
        assert url.startswith(sf.BIBLE_API_BASE)
        assert params.get("translation") == "kjv"
        return _FakeResp({"text": "In the beginning..."})

    monkeypatch.setattr(sf.httpx, "get", fake_get)
    text = sf.get_passage_text("Genesis 1:1", translation="kjv")
    assert text == "In the beginning..."

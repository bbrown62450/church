from hymn_utils import get_property_value


def test_get_property_value_nested_notion_shape():
    nested = {
        "properties": {
            "Hymn Title": {"type": "title", "title": [{"plain_text": "Be Thou My Vision"}]},
            "Hymn Number": {"type": "number", "number": 339},
            "Scripture References": {"type": "rich_text", "rich_text": [{"plain_text": "Prov 3:5"}]},
            "Theme": {"type": "multi_select", "multi_select": [{"name": "Trust"}, {"name": "Guidance"}]},
            "Hymnary.org Link": {"type": "url", "url": "https://hymnary.org/text/be_thou"},
        }
    }
    assert get_property_value(nested, "Hymn Title") == "Be Thou My Vision"
    assert get_property_value(nested, "Hymn Number") == 339
    assert get_property_value(nested, "Scripture References") == "Prov 3:5"
    assert get_property_value(nested, "Theme") == ["Trust", "Guidance"]
    assert get_property_value(nested, "Hymnary.org Link") == "https://hymnary.org/text/be_thou"
    assert get_property_value(nested, "Absent") is None


def test_get_property_value_flat_dict_shape():
    flat = {
        "id": "abc",
        "Hymn Title": "Be Thou My Vision",
        "Hymn Number": 339,
        "Scripture References": "Prov 3:5",
        "Theme": "Trust",
        "Hymnary.org Link": "https://hymnary.org/text/be_thou",
    }
    assert get_property_value(flat, "Hymn Title") == "Be Thou My Vision"
    assert get_property_value(flat, "Hymn Number") == 339
    assert get_property_value(flat, "Scripture References") == "Prov 3:5"
    assert get_property_value(flat, "Theme") == "Trust"
    assert get_property_value(flat, "Hymnary.org Link") == "https://hymnary.org/text/be_thou"
    assert get_property_value(flat, "Absent") is None

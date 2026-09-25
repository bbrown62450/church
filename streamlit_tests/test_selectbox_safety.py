import pytest
from ui_helpers import coerce_selectbox_value


def test_valid_value_is_kept():
    assert coerce_selectbox_value("holy", ["", "holy", "amazing"]) == "holy"


def test_stale_value_resets_to_empty():
    # The church-switch crash today: stored value not in the new church's options.
    assert coerce_selectbox_value("hymn_from_other_church", ["", "a", "b"]) == ""


def test_empty_stays_empty():
    assert coerce_selectbox_value("", ["", "a"]) == ""


def test_missing_none_resets_to_empty():
    assert coerce_selectbox_value(None, ["", "a"]) == ""
